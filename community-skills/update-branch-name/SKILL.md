---
name: update-branch-name
description: >-
  Updates branch names with proper prefixes and formats, enforcing naming conventions, supporting
  semantic prefixes, and managing remote branch updates. (Slash Command, via awesome-claude-code).
---

# /update-branch-name

- **Author:** [giselles-ai](https://github.com/giselles-ai)
- **License:** Apache-2.0
- **Source:** https://github.com/giselles-ai/giselle/blob/main/.claude/commands/update-branch-name.md
- **Imported from:** [awesome-claude-code](https://github.com/anthropics/awesome-claude-code)
- **Category:** Slash Command

## Update Branch Name

Follow these steps to update the current branch name:

1. Check differences between current branch and main branch HEAD using `git diff main...HEAD`
2. Analyze the changed files to understand what work is being done
3. Determine an appropriate descriptive branch name based on the changes
4. Update the current branch name using `git branch -m [new-branch-name]`
5. Verify the branch name was updated with `git branch`

