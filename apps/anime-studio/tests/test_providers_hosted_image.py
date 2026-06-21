from __future__ import annotations

from pathlib import Path

import pytest

from anime_studio.config import ProviderConfig
from anime_studio.providers.hosted import image as image_mod
from anime_studio.providers.hosted.image import HostedImageProvider
from anime_studio.providers.types import GenSpec


async def test_falls_back_to_mock_without_key() -> None:
    cfg = ProviderConfig(provider="hosted", endpoint="https://api.test/predict", api_key_env="MISSING_KEY")
    provider = HostedImageProvider(cfg)
    art = await provider.generate(GenSpec(kind="image", prompt="a sheep"))
    assert art.status == "mock"
    assert art.uri is None


async def test_hosted_success_downloads_asset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_IMG_KEY", "secret")
    cfg = ProviderConfig(
        provider="hosted", endpoint="https://api.test/predict", model="sd", api_key_env="TEST_IMG_KEY"
    )

    captured: dict[str, object] = {}

    def fake_submit(endpoint: str, payload: dict, key: str, **kw: object) -> dict:
        captured["payload"] = payload
        captured["key"] = key
        return {"output": "https://cdn.test/out.png"}

    def fake_download(url: str, out_path: Path, **kw: object) -> Path:
        out_path.write_bytes(b"\x89PNG\r\n\x1a\n fake")
        return out_path

    monkeypatch.setattr(image_mod, "submit_job", fake_submit)
    monkeypatch.setattr(image_mod, "download", fake_download)

    out = tmp_path / "hero.png"
    provider = HostedImageProvider(cfg)
    art = await provider.generate(GenSpec(kind="image", prompt="a brave sheep", out_path=str(out)))

    assert art.status == "rendered"
    assert art.uri == str(out)
    assert out.exists()
    assert captured["key"] == "secret"
    assert captured["payload"]["input"]["prompt"] == "a brave sheep"  # type: ignore[index]


async def test_hosted_falls_back_on_api_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_IMG_KEY", "secret")
    cfg = ProviderConfig(provider="hosted", endpoint="https://api.test/predict", api_key_env="TEST_IMG_KEY")

    def boom(*_: object, **__: object) -> dict:
        from anime_studio.providers.hosted._http import HostedAPIError

        raise HostedAPIError("network down")

    monkeypatch.setattr(image_mod, "submit_job", boom)
    provider = HostedImageProvider(cfg)
    art = await provider.generate(GenSpec(kind="image", prompt="x", out_path=str(tmp_path / "x.png")))
    assert art.status == "mock"
