"""Shared HTTP helpers for hosted-API provider adapters.

A minimal submit -> poll -> download flow over the standard library (so we add
no runtime dependency). Blocking I/O is pushed onto a worker thread by callers
via ``asyncio.to_thread``. The shape is deliberately generic (Replicate /
fal.ai-style async prediction APIs); concrete adapters map their request/response
fields onto these primitives.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


class HostedAPIError(RuntimeError):
    """Raised on any non-recoverable hosted-API failure (triggers fallback)."""


def _request(url: str, *, method: str, headers: dict[str, str], data: bytes | None, timeout: float) -> Any:
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:  # network / timeout
        raise HostedAPIError(f"request to {url} failed: {exc}") from exc
    if not body:
        return {}
    try:
        return json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HostedAPIError(f"invalid JSON from {url}") from exc


def submit_job(endpoint: str, payload: dict[str, Any], api_key: str, *, timeout: float = 120.0) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    result: dict[str, Any] = _request(
        endpoint, method="POST", headers=headers, data=json.dumps(payload).encode("utf-8"), timeout=timeout
    )
    return result


def poll(status_url: str, api_key: str, *, timeout: float = 120.0, interval: float = 2.0) -> dict[str, Any]:
    """Poll a status URL until it reports a terminal state. Returns the final body."""
    headers = {"Authorization": f"Bearer {api_key}"}
    deadline = time.monotonic() + timeout
    while True:
        body: dict[str, Any] = _request(status_url, method="GET", headers=headers, data=None, timeout=timeout)
        status = str(body.get("status", "")).lower()
        if status in ("succeeded", "completed", "complete", "done", ""):
            return body
        if status in ("failed", "error", "canceled", "cancelled"):
            raise HostedAPIError(f"hosted job ended with status '{status}'")
        if time.monotonic() > deadline:
            raise HostedAPIError("hosted job timed out")
        time.sleep(interval)


def download(url: str, out_path: Path, *, timeout: float = 120.0) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            out_path.write_bytes(resp.read())
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise HostedAPIError(f"download from {url} failed: {exc}") from exc
    return out_path


def status_url(body: dict[str, Any], endpoint: str) -> str | None:
    urls = body.get("urls")
    if isinstance(urls, dict) and urls.get("get"):
        return str(urls["get"])
    if body.get("status_url"):
        return str(body["status_url"])
    if body.get("id") and endpoint:
        return f"{endpoint.rstrip('/')}/{body['id']}"
    return None


def await_terminal(
    body: dict[str, Any], endpoint: str, key: str, *, timeout: float = 120.0, interval: float = 2.0
) -> dict[str, Any]:
    """Return ``body`` if already terminal, else poll its status URL until it is."""
    if body.get("output") or body.get("url"):
        return body
    url = status_url(body, endpoint)
    if url is None:
        return body
    return poll(url, key, timeout=timeout, interval=interval)


def first_output_url(body: dict[str, Any]) -> str:
    """Extract an asset URL from common response shapes (output/url/urls)."""
    output = body.get("output", body.get("url") or body.get("urls"))
    if isinstance(output, str):
        return output
    if isinstance(output, list) and output:
        return str(output[0])
    if isinstance(output, dict):
        for key in ("url", "video", "image", "audio"):
            if key in output:
                return str(output[key])
    raise HostedAPIError("no output URL in hosted response")
