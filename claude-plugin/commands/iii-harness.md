---
description: Run the iii plan → work → review harness on a task, looping until review passes.
argument-hint: <task description>
---

Run the full iii coding harness on: **$ARGUMENTS**

Drive the plan → work → review loop. Do not write code yourself in the planning step.

1. **Plan** — delegate to the `iii-planner` agent. Get an approved plan grounded in the iii
   worker/function/trigger model with explicit acceptance checks. If anything material is ambiguous,
   ask the user before proceeding.
2. **Work** — delegate to the `iii-implementer` agent to execute the plan step by step, keeping the
   build green. If the implementer reports the plan is wrong or blocked, return to step 1.
3. **Review** — delegate to the `iii-reviewer` agent to adversarially verify the diff and re-run the
   acceptance checks.
4. **Iterate** — if review returns FAIL, send the findings back to the implementer and repeat from
   step 2. Stop after the review PASSes, or after 3 failed review rounds — then report where it is
   stuck.
5. **Compound** — apply any reusable lesson the reviewer surfaced as a concrete edit to a `skills/`
   file so the next run starts smarter.

Report the final verdict, the files changed, and the checks that passed.
