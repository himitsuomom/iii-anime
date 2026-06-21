from __future__ import annotations

from pathlib import Path

import pytest

from anime_studio.config import ProviderConfig
from anime_studio.providers.hosted import audio as audio_mod
from anime_studio.providers.hosted.audio import HostedAudioProvider
from anime_studio.providers.types import GenSpec


async def test_hosted_success_downloads_bgm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_AUD_KEY", "secret")
    cfg = ProviderConfig(provider="hosted", endpoint="https://api.test/a", model="stable-audio",
                         api_key_env="TEST_AUD_KEY")

    def fake_submit(endpoint: str, payload: dict, key: str, **kw: object) -> dict:
        return {"output": "https://cdn.test/bgm.wav"}

    def fake_download(url: str, out_path: Path, **kw: object) -> Path:
        out_path.write_bytes(b"RIFFfake")
        return out_path

    monkeypatch.setattr(audio_mod, "submit_job", fake_submit)
    monkeypatch.setattr(audio_mod, "download", fake_download)

    out = tmp_path / "bgm.wav"
    art = await HostedAudioProvider(cfg).generate_bgm(GenSpec(kind="bgm", prompt="bed", out_path=str(out)))
    assert art.status == "rendered"
    assert out.exists()


async def test_hosted_audio_falls_back_to_ffmpeg_without_key(tmp_path: Path) -> None:
    # No key -> falls back to the procedural ffmpeg provider (or its mock degrade).
    cfg = ProviderConfig(provider="hosted", endpoint="https://api.test/a", api_key_env="MISSING")
    art = await HostedAudioProvider(cfg).generate_bgm(
        GenSpec(kind="bgm", prompt="bed", out_path=str(tmp_path / "bgm.wav"), params={"duration_s": 1.0})
    )
    # FfmpegAudioProvider yields "rendered" when ffmpeg is present, else "mock".
    assert art.status in ("rendered", "mock")
    assert art.provider == "ffmpeg-audio"
