"""Vault への成果物保存と、過去ドキュメントの簡易検索。

保存パス規約: ``{VAULT}/prompts/YYYY/MM/{phase}-{slug}.md``
frontmatter に phase / title / project / created を付与する。
``VAULT_PATH`` 環境変数でルートを指定（未設定なら ``./vault``）。
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

_SLUG_STRIP = re.compile(r"[^\w]+", re.UNICODE)


def vault_root() -> Path:
    """Vault のルートディレクトリ。``VAULT_PATH`` 未設定なら ``./vault``。"""
    return Path(os.environ.get("VAULT_PATH", "vault")).expanduser()


def slugify(title: str) -> str:
    """タイトルをファイル名向けの slug に変換する（日本語はそのまま残す）。"""
    slug = _SLUG_STRIP.sub("-", title.strip().lower()).strip("-")
    return slug or "untitled"


def _frontmatter(phase: int, title: str, project: str, created: str) -> str:
    return (
        "---\n"
        f"phase: {phase}\n"
        f'title: "{title}"\n'
        f'project: "{project}"\n'
        f"created: {created}\n"
        "---\n"
    )


@dataclass(frozen=True)
class SaveResult:
    path: str
    relative: str


def save_artifact(
    phase: int,
    title: str,
    content: str,
    project: str = "",
    now: datetime | None = None,
) -> SaveResult:
    """成果物を Vault に保存し、保存先パスを返す。

    `now` を渡せると決定的にテストできる（未指定なら現在時刻）。
    """
    stamp = now or datetime.now()
    rel = Path("prompts") / f"{stamp:%Y}" / f"{stamp:%m}" / f"{phase}-{slugify(title)}.md"
    dest = vault_root() / rel
    dest.parent.mkdir(parents=True, exist_ok=True)

    document = (
        _frontmatter(phase, title, project, stamp.strftime("%Y-%m-%dT%H:%M:%S"))
        + "\n"
        + content.rstrip()
        + "\n"
    )
    dest.write_text(document, encoding="utf-8")
    return SaveResult(path=str(dest), relative=str(rel))


def retrieve_context(query: str, limit: int = 5) -> list[dict[str, str]]:
    """Vault 内の Markdown を素朴な部分一致で検索し、上位 `limit` 件を返す。

    クエリ語をスペース分割し、本文に含まれる語数が多い順にスコアリングする。
    """
    root = vault_root()
    if not root.exists():
        return []

    terms = [t for t in query.lower().split() if t]
    scored: list[tuple[int, str, str]] = []
    for md in root.rglob("*.md"):
        try:
            text = md.read_text(encoding="utf-8")
        except OSError:
            continue
        low = text.lower()
        score = sum(1 for t in terms if t in low) if terms else 0
        # クエリ語が空でも、検索対象として最低限ヒットさせる
        if score > 0 or not terms:
            excerpt = text.strip().splitlines()
            preview = " ".join(line for line in excerpt[:8] if not line.startswith("---"))
            scored.append((score, str(md.relative_to(root)), preview[:280]))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {"path": path, "score": str(score), "preview": preview}
        for score, path, preview in scored[: max(0, limit)]
    ]
