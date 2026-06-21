from __future__ import annotations

from pathlib import Path

import pytest

from anime_studio.config import ProviderConfig
from anime_studio.providers.hosted import video as video_mod
from anime_studio.providers.hosted.video import HostedVideoProvider
from anime_studio.providers.types import GenSpec


async def test_falls_back_to_mock_without_key() -> None:
    cfg = ProviderConfig(provider="hosted", endpoint="https://api.test/v", api_key_env="MISSING")
    art = await HostedVideoProvider(cfg).generate(GenSpec(kind="video", prompt="a sheep runs"))
    assert art.status == "stub"  # MockVideoProvider
    assert art.uri is None


async def test_hosted_success_downloads_clip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_VID_KEY", "secret")
    cfg = ProviderConfig(provider="hosted", endpoint="https://api.test/v", model="wan", api_key_env="TEST_VID_KEY")

    captured: dict[str, object] = {}

    def fake_submit(endpoint: str, payload: dict, key: str, **kw: object) -> dict:
        captured["payload"] = payload
        return {"output": ["https://cdn.test/clip.mp4"]}

    def fake_download(url: str, out_path: Path, **kw: object) -> Path:
        out_path.write_bytes(b"\x00\x00\x00\x18ftypmp42")
        return out_path

    monkeypatch.setattr(video_mod, "submit_job", fake_submit)
    monkeypatch.setattr(video_mod, "download", fake_download)

    out = tmp_path / "cut_01.mp4"
    spec = GenSpec(
        kind="video", prompt="a sheep runs", init_image="/tmp/ref.png",
        out_path=str(out), params={"duration_s": 3.0, "aspect": "9:16"},
    )
    art = await HostedVideoProvider(cfg).generate(spec)

    assert art.status == "rendered"
    assert art.uri == str(out)
    assert out.exists()
    assert captured["payload"]["input"]["image"] == "/tmp/ref.png"  # type: ignore[index]
