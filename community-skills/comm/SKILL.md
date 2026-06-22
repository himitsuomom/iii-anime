---
name: comm
description: >-
  Serves as a development reference for E2E-encrypted messaging applications with code
  organization architecture, security implementation details, and testing procedures. (CLAUDE.md
  File, via awesome-claude-code).
---

# Comm

- **Author:** [CommE2E](https://github.com/CommE2E)
- **License:** BSD-3-Clause
- **Source:** https://github.com/CommE2E/comm/blob/master/AGENTS.md
- **Imported from:** [awesome-claude-code](https://github.com/anthropics/awesome-claude-code)
- **Category:** CLAUDE.md File

## Comm Project Development Guide

## Build & Test Commands

- Run tests: `yarn workspace [lib|web|keyserver|native] test`
- Test all packages: `yarn jest:all`
- Run lint: `yarn eslint:all`
- Fix lint issues: `yarn eslint:fix`
- Check Flow types: `yarn flow:all` or `yarn workspace [workspace] flow`
- Run dev server: `yarn workspace [workspace] dev`
- Clean install: `yarn cleaninstall`

## Code Style

### Types

- Use Flow for static typing with strict mode enabled
- Always include `// @flow` annotation at the top of JS files
- Export types with explicit naming: `export type MyType = {...}`

### Formatting

- Prettier with 80-char line limit
- Single quotes, trailing commas
- Arrow function parentheses avoided when possible
- React component files named \*.react.js

### Naming

- kebab-case for filenames (enforced by unicorn/filename-case)
- Descriptive variable names

### Imports

- Group imports with newlines between builtin/external and internal
- Alphabetize imports within groups
- No relative imports between workspaces - use workspace references

### React

- Use functional components with hooks
- Follow exhaustive deps rule for useEffect/useCallback
- Component props should use explicit Flow types

### Error Handling

- Use consistent returns in functions
- Handle all promise rejections

