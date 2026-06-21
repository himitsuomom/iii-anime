from __future__ import annotations

from pathlib import Path

from anime_studio.cli import main

_FIXTURES = Path(__file__).parent / "fixtures"


def test_cli_run_writes_bible(tmp_path: Path) -> None:
    rc = main(
        [
            "run",
            "--brief",
            str(_FIXTURES / "sample_brief.yaml"),
            "--output-dir",
            str(tmp_path),
            "--provider",
            "mock",
        ]
    )
    assert rc == 0
    assert (tmp_path / "demo-sheep" / "production_bible.md").exists()


def test_cli_validate() -> None:
    assert main(["validate"]) == 0


def test_cli_info(capsys) -> None:
    assert main(["info"]) == 0
    out = capsys.readouterr().out
    assert "script" in out and "distribution" in out
