---
description: Capture a lesson from the current session into the iii skills catalog (compound engineering).
argument-hint: [lesson or leave blank to infer from the session]
---

Compound engineering step: turn what was just learned into reusable context so future agent runs
start smarter.

Lesson (optional): **$ARGUMENTS**

1. Identify the lesson — a pattern that worked, a gotcha that cost time, a missing example, or an
   API misuse that the harness corrected. If `$ARGUMENTS` is empty, infer it from the current
   session's diff and review findings.
2. Find the right home for it in `skills/` — extend the most relevant existing `SKILL.md`
   (`iii-core-primitives`, `iii-architecture-patterns`, `iii-error-handling`, or one of the
   agent-infrastructure skills) rather than creating a new file unless the topic is genuinely new.
3. Write it as a concrete, copy-pasteable rule or example in the terse iii voice — not a vague tip.
4. Keep the catalog honest: if you add a skill, update `skills/SKILLS.md` and `skills/README.md`.

Report the exact edit you made and why it will help the next run.
