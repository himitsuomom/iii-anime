---
name: spy
description: >-
  Enforces strict coding conventions with comprehensive testing guidelines, multiple code
  compilation options, and backend-specific test decorators for targeted filtering. (CLAUDE.md
  File, via awesome-claude-code).
---

# SPy

- **Author:** [spylang](https://github.com/spylang)
- **License:** MIT
- **Source:** https://github.com/spylang/spy/blob/main/CLAUDE.md
- **Imported from:** [awesome-claude-code](https://github.com/anthropics/awesome-claude-code)
- **Category:** CLAUDE.md File

## SPy Language - Dev Reference

## General behavior of claude code
- NEVER run tests automatically unless explicitly asked
- when asked to write a test, write just the test without trying to fix it
- avoid writing useless comments: if you need to write a comment, explain WHY
  the code does something instead of WHAT it does



## Common Commands
- When running tests, always use the venv: e.g. `./venv/bin/pytest'
- Run all tests: `pytest`
- Run single test: `pytest spy/tests/path/to/test_file.py::TestClass::test_function`
- Run backend-specific tests: `pytest -m interp` or `-m C` or `-m doppler`
- Type checking: `mypy`
- Test shortcut: `source pytest-shortcut.sh` (enables `p` as pytest alias with tab completion)

## Compile SPy Code
```bash
spy your_file.spy                 # Execute (default)
spy -C your_file.spy              # Generate C code
spy -c your_file.spy              # Compile to executable
spy -O 1 -g your_file.spy         # With optimization and debug symbols
```

## Code Style Guidelines
- Use strict typing (mypy enforced)
- Classes: PascalCase (`CompilerTest`)
- Functions/methods: snake_case (`compile_module()`)
- Constants: SCREAMING_SNAKE_CASE (`ALL_BACKENDS`)
- Organize imports by standard Python conventions
- Prefer specific imports: `from spy.errors import SPyError`
- Tests inherit from `CompilerTest` base class
- Use backend-specific decorators for test filtering (`@only_interp`, `@skip_backends`)

## GH PR Guidelines
- When creating a PR, describe what you did, but don't include the "test plan" section.

