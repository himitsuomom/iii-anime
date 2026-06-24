"""`PhaseSpec` と入力コンテキストから system/user プロンプトを組み立てる。

テンプレート `templates/phase-{n}.md` が存在すればそれを system プロンプトの本体に使い、
無ければフェーズ仕様からフォールバックの system プロンプトを生成する。いずれの場合も
先頭にフェーズ名（`name_ja`）と適用思想を含むヘッダを付与する。
"""

from __future__ import annotations

from importlib import resources
from typing import Any

from sdlc_prompt_gen.phases import PhaseSpec

_TEMPLATE_PACKAGE = "sdlc_prompt_gen.templates"


def _load_template(number: int) -> str | None:
    """`templates/phase-{n}.md` を読む。無ければ None。"""
    name = f"phase-{number}.md"
    try:
        resource = resources.files(_TEMPLATE_PACKAGE).joinpath(name)
        if not resource.is_file():
            return None
        return resource.read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError):
        return None


def _system_header(spec: PhaseSpec) -> str:
    return (
        f"# SDLC Phase {spec.number}: {spec.name_ja}（{spec.name_en}）\n"
        f"適用思想: {spec.philosophy}\n"
    )


def _fallback_body(spec: PhaseSpec) -> str:
    return (
        f"あなたは SDLC Phase {spec.number}「{spec.name_ja}」を担当する熟練エンジニアです。\n"
        f"「{spec.philosophy}」の考え方に沿って、与えられたコンテキストから"
        f"このフェーズの成果物を、抜け漏れなく具体的に作成してください。\n"
        f"成果物は {spec.output_dir} 配下に置く想定で記述します。\n"
    )


def build_prompt(
    spec: PhaseSpec,
    project_context: str,
    response_format: str = "detailed",
    prior_artifacts: list[str] | None = None,
) -> dict[str, Any]:
    """system/user プロンプトと付帯メタデータを返す。

    返り値: ``{"system_prompt", "user_prompt", "phase_meta"}``
    """
    template = _load_template(spec.number)
    template_loaded = template is not None
    body = template if template_loaded else _fallback_body(spec)

    system_prompt = f"{_system_header(spec)}\n{body}".rstrip() + "\n"

    detail_hint = (
        "可能な限り詳細に、章立てと根拠を添えて出力してください。"
        if response_format == "detailed"
        else "要点を簡潔に箇条書きで出力してください。"
    )

    user_lines = [
        "## project_context",
        project_context,
        "",
        "## response_format",
        f"{response_format} — {detail_hint}",
    ]
    if prior_artifacts:
        user_lines += [
            "",
            "## prior_artifacts",
            "以下の既存成果物を踏まえて、重複を避けつつ整合させること:",
            *[f"- {path}" for path in prior_artifacts],
        ]
    user_prompt = "\n".join(user_lines) + "\n"

    return {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "phase_meta": {
            "number": spec.number,
            "name_ja": spec.name_ja,
            "name_en": spec.name_en,
            "philosophy": spec.philosophy,
            "model": spec.model,
            "template_loaded": template_loaded,
            "response_format": response_format,
        },
    }
