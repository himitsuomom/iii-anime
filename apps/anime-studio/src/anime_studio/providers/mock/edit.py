"""Mock edit provider: describes the final assembly without rendering."""

from __future__ import annotations

from ...models.artifacts import ArtifactDescriptor
from ...models.edit import EditPlan


class MockEditProvider:
    name = "mock-edit"
    supports_render = False

    async def assemble(self, edit_plan: EditPlan, clips: list[ArtifactDescriptor]) -> ArtifactDescriptor:
        return ArtifactDescriptor(
            kind="final_video",
            status="stub",
            uri=None,
            prompt=f"assemble {len(clips)} clips at {edit_plan.bpm} BPM",
            provider=self.name,
            metadata={"segments": len(edit_plan.segments), "bpm": edit_plan.bpm},
        )
