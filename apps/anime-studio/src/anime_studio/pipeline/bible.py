"""Render the human-readable production bible (master deliverable)."""

from __future__ import annotations

from typing import Any

from ..models.brief import ProjectBrief
from ..models.character import CharacterSheet
from ..models.distribution import DistributionPlan
from ..models.edit import EditPlan
from ..models.prompts import CutPromptSet
from ..models.qa import QAReport
from ..models.script import CreativeBrief, ScriptArtifact
from ..models.storyboard import Storyboard


def render_bible(brief: ProjectBrief, artifacts: dict[str, Any]) -> str:
    lines: list[str] = []
    w = lines.append

    w(f"# 制作バイブル — {brief.title_idea}")
    w("")
    w(f"- **Project ID**: `{brief.project_id}`")
    w(f"- **Logline**: {brief.logline}")
    w(f"- **Platforms**: {', '.join(brief.target_platforms)}")
    w(f"- **Duration**: {brief.target_duration_s}s / **Tone**: {brief.tone} / **Genre**: {brief.genre}")
    w("")

    planning = artifacts.get("planning")
    if isinstance(planning, CreativeBrief):
        w("## 1. 企画 (Concept / STEPPS)")
        w(f"- **Concept**: {planning.concept}")
        w(f"- **Primary platform**: {planning.primary_platform}")
        w(f"- **Hook archetype**: {planning.hook_archetype}")
        w(f"- **STEPPS levers**: {', '.join(planning.stepps_levers)}")
        w(f"- **Share trigger**: {planning.share_trigger}")
        w("")

    script = artifacts.get("script")
    if isinstance(script, ScriptArtifact):
        w("## 2. 脚本 (Script — 5-beat Shorts structure)")
        w(f"*Framework: {script.framework} / Theme: {script.theme}*")
        w("")
        w("| # | Beat | Time | Emotion | Visual metaphor | Narrative |")
        w("|---|------|------|---------|-----------------|-----------|")
        for i, b in enumerate(script.beats, 1):
            w(f"| {i} | {b.label} | {b.start_s}-{b.end_s}s | {b.emotion} | {b.visual_metaphor} | {b.narrative} |")
        w("")
        for note in script.silent_storytelling_notes:
            w(f"- {note}")
        w("")

    character = artifacts.get("character")
    if isinstance(character, CharacterSheet):
        w("## 3. キャラクターシート (Character Sheets)")
        for c in character.characters:
            w(f"### {c.name} ({c.role})")
            w(f"- {c.visual_description}")
            w(f"- **Palette**: {', '.join(c.palette)}")
            w(f"- **Consistency**: {c.consistency_notes}")
        w("")

    storyboard = artifacts.get("storyboard")
    if isinstance(storyboard, Storyboard):
        w("## 4. 絵コンテ (Storyboard)")
        w("| Cut | Beat | Dur | Shot | Composition | Camera | Color | Light |")
        w("|-----|------|-----|------|-------------|--------|-------|-------|")
        for cut in storyboard.cuts:
            w(
                f"| {cut.index} | {cut.beat_id} | {cut.duration_s}s | {cut.composition.shot_size} "
                f"| {cut.composition.rule} | {cut.camera.move_id} | {cut.color_mood} | {cut.lighting} |"
            )
        w("")

    production = artifacts.get("production")
    if isinstance(production, CutPromptSet):
        w("## 5. 生成プロンプト (Generation Prompts)")
        for p in production.prompts:
            w(f"### Cut {p.cut_index} — tool: {p.recommended_tool}")
            w(f"- **Principles**: {', '.join(p.animation_principles)}")
            w(f"- **Positive**: {p.positive}")
            w(f"- **Negative**: {p.negative}")
        w("")

    editing = artifacts.get("editing")
    if isinstance(editing, EditPlan):
        w("## 6. 編集・音響 (Edit & Sound Plan)")
        w(f"- **BPM**: {editing.bpm} (beat-matched cuts)")
        w(f"- **Leitmotif**: {editing.leitmotif}")
        w(f"- **Loop**: {editing.loop_strategy}")
        w(f"- **Segments**: {len(editing.segments)} / **Audio cues**: {len(editing.audio_cues)}")
        w("")

    qa = artifacts.get("qa")
    if isinstance(qa, QAReport):
        w("## 7. QAレポート (Quality Gates)")
        w(f"**Overall: {'PASS' if qa.passed else 'NEEDS WORK'}**")
        w("")
        w("| Gate | Result | Score | Feedback |")
        w("|------|--------|-------|----------|")
        for g in qa.gates:
            w(f"| {g.gate} | {'✅' if g.passed else '❌'} | {g.score} | {g.feedback} |")
        w("")

    distribution = artifacts.get("distribution")
    if isinstance(distribution, DistributionPlan):
        w("## 8. 配信プラン (Distribution)")
        w("| Platform | Duration | Aspect | Audio | Hashtags |")
        w("|----------|----------|--------|-------|----------|")
        for v in distribution.variants:
            w(f"| {v.platform} | {v.duration_s}s | {v.aspect_ratio} | {v.audio_strategy} | {' '.join(v.hashtags)} |")
        w("")
        w(f"**Thumbnail**: {distribution.thumbnail.concept} (overlay: {distribution.thumbnail.text_overlay})")
        w("")
        w("**Title candidates**:")
        for t in distribution.titles:
            w(f"- _{t.hook_archetype}_: {t.text}")
        w("")

    return "\n".join(lines) + "\n"
