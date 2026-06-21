"""Typed production artifacts passed between studio departments."""

from .artifacts import ArtifactDescriptor
from .brief import ProjectBrief
from .character import CharacterDesign, CharacterSheet
from .distribution import DistributionPlan, PlatformVariant, ThumbnailSpec, TitleCandidate
from .edit import AudioCue, EditPlan, EditSegment
from .job import PipelineJob, ProgressEvent, StageStatus
from .prompts import CutPromptSet, GenerationPrompt
from .qa import QAGateResult, QAReport
from .script import Beat, CreativeBrief, ScriptArtifact
from .storyboard import CameraMove, Composition, Cut, Storyboard

__all__ = [
    "ArtifactDescriptor",
    "ProjectBrief",
    "CreativeBrief",
    "Beat",
    "ScriptArtifact",
    "CharacterDesign",
    "CharacterSheet",
    "Composition",
    "CameraMove",
    "Cut",
    "Storyboard",
    "GenerationPrompt",
    "CutPromptSet",
    "EditSegment",
    "AudioCue",
    "EditPlan",
    "QAGateResult",
    "QAReport",
    "TitleCandidate",
    "ThumbnailSpec",
    "PlatformVariant",
    "DistributionPlan",
    "StageStatus",
    "ProgressEvent",
    "PipelineJob",
]
