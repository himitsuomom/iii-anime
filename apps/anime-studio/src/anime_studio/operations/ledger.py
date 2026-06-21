"""Production ledger: the company's persistent record of every video made."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models.operations import LedgerEntry


class Ledger:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> list[LedgerEntry]:
        if not self._path.exists():
            return []
        data = json.loads(self._path.read_text(encoding="utf-8"))
        return [LedgerEntry.model_validate(row) for row in data]

    def append(self, entry: LedgerEntry) -> None:
        entries = self.load()
        # Replace any prior row for the same project (idempotent re-runs).
        entries = [e for e in entries if e.project_id != entry.project_id]
        entries.append(entry)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps([e.model_dump(mode="json") for e in entries], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def summary(self) -> dict[str, Any]:
        entries = self.load()
        completed = [e for e in entries if e.status == "completed"]
        passed = [e for e in completed if e.qa_passed]
        scores = [e.qa_score for e in completed if e.qa_score is not None]
        return {
            "total": len(entries),
            "completed": len(completed),
            "failed": len(entries) - len(completed),
            "qa_pass_rate": round(len(passed) / len(completed), 2) if completed else 0.0,
            "avg_qa_score": round(sum(scores) / len(scores), 1) if scores else None,
        }
