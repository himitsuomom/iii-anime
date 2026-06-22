---
name: initref
description: >-
  Initializes reference documentation structure with standard doc templates, API reference setup,
  documentation conventions, and placeholder content generation. (Slash Command, via
  awesome-claude-code).
---

# /initref

- **Author:** [okuvshynov](https://github.com/okuvshynov)
- **License:** MIT
- **Source:** https://github.com/okuvshynov/cubestat/blob/main/.claude/commands/initref.md
- **Imported from:** [awesome-claude-code](https://github.com/anthropics/awesome-claude-code)
- **Category:** Slash Command

Build a reference for the implementation details of this project. Use provided summarize tool to get summary of the files. Avoid reading the content of many files yourself, as we might hit usage limits. Do read the content of important files though. Use the returned summaries to create reference files in /ref directory. Use markdown format for writing the documentation files.

Update CLAUDE.md file with the pointers to important documentation files.

