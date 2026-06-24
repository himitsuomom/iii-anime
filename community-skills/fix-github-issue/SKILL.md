---
name: fix-github-issue
description: >-
  Analyzes and fixes GitHub issues using a structured approach with GitHub CLI for issue details,
  implementing necessary code changes, running tests, and creating proper commit messages. (Slash
  Command, via awesome-claude-code).
---

# /fix-github-issue

- **Author:** [jeremymailen](https://github.com/jeremymailen)
- **License:** Apache-2.0
- **Source:** https://github.com/jeremymailen/kotlinter-gradle/blob/master/.claude/commands/fix-github-issue.md
- **Imported from:** [awesome-claude-code](https://github.com/anthropics/awesome-claude-code)
- **Category:** Slash Command

Please analyze and fix the GitHub issue: $ARGUMENTS.

Follow these steps:

1. Use `gh issue view` to get the issue details
2. Understand the problem described in the issue
3. Search the codebase for relevant files
4. Implement the necessary changes to fix the issue
5. Write and run tests to verify the fix
6. Ensure code passes linting and type checking
7. Create a descriptive commit message

Remember to use the GitHub CLI (`gh`) for all GitHub-related tasks.

