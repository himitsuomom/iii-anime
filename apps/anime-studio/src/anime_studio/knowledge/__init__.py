"""Embedded knowledge base of AI-anime production laws and principles."""

from .loader import (
    AnimationPrinciple,
    CameraMoveKB,
    EmotionMetaphor,
    Hook,
    KnowledgeBase,
    PlatformSpec,
    ScriptBeatsKB,
    default_knowledge_base,
)

__all__ = [
    "KnowledgeBase",
    "default_knowledge_base",
    "ScriptBeatsKB",
    "CameraMoveKB",
    "AnimationPrinciple",
    "PlatformSpec",
    "Hook",
    "EmotionMetaphor",
]
