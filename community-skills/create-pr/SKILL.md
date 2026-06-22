---
name: create-pr
description: >-
  Streamlines pull request creation by handling the entire workflow: creating a new branch,
  committing changes, formatting modified files with Biome, and submitting the PR. (Slash Command,
  via awesome-claude-code).
---

# /create-pr

- **Author:** [toyamarinyon](https://github.com/toyamarinyon)
- **License:** Apache-2.0
- **Source:** https://github.com/toyamarinyon/giselle/blob/main/.claude/commands/create-pr.md
- **Imported from:** [awesome-claude-code](https://github.com/anthropics/awesome-claude-code)
- **Category:** Slash Command

## Create Pull Request Command

Create a new branch, commit changes, and submit a pull request.

## Behavior
- Creates a new branch based on current changes
- Formats modified files using Biome
- Analyzes changes and automatically splits into logical commits when appropriate
- Each commit focuses on a single logical change or feature
- Creates descriptive commit messages for each logical unit
- Pushes branch to remote
- Creates pull request with proper summary and test plan

## Guidelines for Automatic Commit Splitting
- Split commits by feature, component, or concern
- Keep related file changes together in the same commit
- Separate refactoring from feature additions
- Ensure each commit can be understood independently
- Multiple unrelated changes should be split into separate commits

