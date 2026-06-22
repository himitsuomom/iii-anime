---
name: testing_plan_integration
description: >-
  Creates inline Rust-style tests, suggests refactoring for testability, analyzes code challenges,
  and creates comprehensive test coverage for robust code. (Slash Command, via
  awesome-claude-code).
---

# /testing_plan_integration

- **Author:** [buster-so](https://github.com/buster-so)
- **License:** NOASSERTION
- **Source:** https://github.com/buster-so/buster/blob/main/api/.claude/commands/testing_plan_integration.md
- **Imported from:** [awesome-claude-code](https://github.com/anthropics/awesome-claude-code)
- **Category:** Slash Command

I need you to create an integration testing plan for $ARGUMENTS

These are integration tests and I want them to be inline in rust fashion.

If the code is difficult to test, you should suggest refactoring to make it easier to test.

Think really hard about the code, the tests, and the refactoring (if applicable).

Will you come up with test cases and let me review before you write the tests?

Feel free to ask clarifying questions.

