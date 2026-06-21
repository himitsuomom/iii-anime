from __future__ import annotations

import json

from anime_studio.pipeline.orchestrator import run_pipeline


async def test_full_pipeline_writes_bible_and_artifacts(sample_brief, config) -> None:
    output = await run_pipeline(sample_brief, config)

    # All stage artifacts present.
    for stage in ("planning", "script", "character", "storyboard", "production", "editing", "qa", "distribution"):
        assert stage in output.artifacts

    # Core files written.
    project_dir = output.output_dir
    assert (project_dir / "brief.json").exists()
    assert (project_dir / "script.json").exists()
    assert (project_dir / "storyboard.json").exists()
    assert (project_dir / "distribution" / "youtube_shorts.json").exists()
    assert list((project_dir / "cuts").glob("cut_*.json"))

    # Bible has every section header.
    bible = output.bible_path.read_text(encoding="utf-8")
    headers = ("企画", "脚本", "キャラクターシート", "絵コンテ", "生成プロンプト", "編集", "QAレポート", "配信プラン")
    for header in headers:
        assert header in bible

    # Artifacts round-trip through JSON.
    script = json.loads((project_dir / "script.json").read_text(encoding="utf-8"))
    assert len(script["beats"]) == 5


async def test_pipeline_is_deterministic_with_mock(sample_brief, config) -> None:
    out1 = await run_pipeline(sample_brief, config)
    text1 = out1.bible_path.read_text(encoding="utf-8")
    out2 = await run_pipeline(sample_brief, config)
    text2 = out2.bible_path.read_text(encoding="utf-8")
    assert text1 == text2
