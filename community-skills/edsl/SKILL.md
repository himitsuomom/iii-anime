---
name: edsl
description: >-
  Offers detailed build and test commands with strict code style enforcement, comprehensive
  testing requirements, and standardized development workflow using Black and mypy. (CLAUDE.md
  File, via awesome-claude-code).
---

# EDSL

- **Author:** [expectedparrot](https://github.com/expectedparrot)
- **License:** MIT
- **Source:** https://github.com/hesreallyhim/awesome-claude-code/blob/main/resources/claude.md-files/EDSL/CLAUDE.md
- **Imported from:** [awesome-claude-code](https://github.com/anthropics/awesome-claude-code)
- **Category:** CLAUDE.md File

## EDSL Codebase Reference

## Build & Test Commands
- Install: `make install`
- Run all tests: `make test`
- Run single test: `pytest -xv tests/path/to/test.py`
- Run with coverage: `make test-coverage`
- Run integration tests: `make test-integration`
- Type checking: `make lint` (runs mypy)
- Format code: `make format` (runs black-jupyter)
- Generate docs: `make docs`
- View docs: `make docs-view`

## Code Style Guidelines
- **Formatting**: Use Black for consistent code formatting
- **Imports**: Group by stdlib, third-party, internal modules
- **Type hints**: Required throughout, verified by mypy
- **Naming**: 
  - Classes: PascalCase
  - Methods/functions/variables: snake_case
  - Constants: UPPER_SNAKE_CASE
  - Private items: _prefixed_with_underscore
- **Error handling**: Use custom exception hierarchy with BaseException parent
- **Documentation**: Docstrings for all public functions/classes
- **Testing**: Every feature needs associated tests

## Permissions Guidelines
- **Allowed without asking**: Running tests, linting, code formatting, viewing files
- **Ask before**: Modifying tests, making destructive operations, installing packages
- **Never allowed**: Pushing directly to main branch, changing API keys/secrets

