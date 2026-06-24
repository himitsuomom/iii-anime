# Community Skills

Claude Code resources curated by
[awesome-claude-code](https://github.com/anthropics/awesome-claude-code), repackaged as
iii-installable skills. Each folder is a standalone skill with a `SKILL.md`; the original
resource files are preserved alongside it.

## Install

```bash
# everything
npx skills add iii-hq/iii/community-skills

# a single skill
npx skills add iii-hq/iii/community-skills --skill commit
```

## Provenance

These resources are contributed by their original authors and retain their original
licenses (see each skill's `SKILL.md`). Only open-source-licensed resources are hosted
here, mirroring awesome-claude-code's hosting policy.

## Catalog

### Slash Commands

- [`act`](./act/SKILL.md) — Generates React components with proper accessibility, creating ARIA-compliant components with keyboard navigation that follow React best practices and include comprehensive accessibility testing.
- [`add-to-changelog`](./add-to-changelog/SKILL.md) — Adds new entries to changelog files while maintaining format consistency, properly documenting changes, and following established project standards for version tracking.
- [`clean`](./clean/SKILL.md) — Addresses code formatting and quality issues by fixing black formatting problems, organizing imports with isort, resolving flake8 linting issues, and correcting mypy type errors.
- [`commit`](./commit/SKILL.md) — Creates git commits using conventional commit format with appropriate emojis, following project standards and creating descriptive messages that explain the purpose of changes.
- [`context-prime`](./context-prime/SKILL.md) — Primes Claude with comprehensive project understanding by loading repository structure, setting development context, establishing project goals, and defining collaboration parameters.
- [`create-hook`](./create-hook/SKILL.md) — Slash command for hook creation - intelligently prompts you through the creation process with smart suggestions based on your project setup
- [`create-jtbd`](./create-jtbd/SKILL.md) — You are an experienced Product Manager. Your task is to create a Jobs to be Done
- [`create-pr`](./create-pr/SKILL.md) — Streamlines pull request creation by handling the entire workflow: creating a new branch, committing changes, formatting modified files with Biome, and submitting the PR.
- [`create-prd`](./create-prd/SKILL.md) — You are an experienced Product Manager. Your task is to create a Product Requirements Document
- [`create-prp`](./create-prp/SKILL.md) — Creates product requirement plans by reading PRP methodology, following template structure, creating comprehensive requirements, and structuring product definitions for development.
- [`create-pull-request`](./create-pull-request/SKILL.md) — Provides comprehensive PR creation guidance with GitHub CLI, enforcing title conventions, following template structure, and offering concrete command examples with best practices.
- [`create-worktrees`](./create-worktrees/SKILL.md) — Creates git worktrees for all open PRs or specific branches, handling branches with slashes, cleaning up stale worktrees, and supporting custom branch creation for development.
- [`fix-github-issue`](./fix-github-issue/SKILL.md) — Analyzes and fixes GitHub issues using a structured approach with GitHub CLI for issue details, implementing necessary code changes, running tests, and creating proper commit messages.
- [`husky`](./husky/SKILL.md) — Sets up and manages Husky Git hooks by configuring pre-commit hooks, establishing commit message standards, integrating with linting tools, and ensuring code quality on commits.
- [`initref`](./initref/SKILL.md) — Initializes reference documentation structure with standard doc templates, API reference setup, documentation conventions, and placeholder content generation.
- [`load-llms-txt`](./load-llms-txt/SKILL.md) — Loads LLM configuration files to context, importing specific terminology, model configurations, and establishing baseline terminology for AI discussions.
- [`optimize`](./optimize/SKILL.md) — Analyzes code performance to identify bottlenecks, proposing concrete optimizations with implementation guidance for improved application performance.
- [`pr-review`](./pr-review/SKILL.md) — Reviews pull request changes to provide feedback, check for issues, and suggest improvements before merging into the main codebase.
- [`release`](./release/SKILL.md) — Manages software releases by updating changelogs, reviewing README changes, evaluating version increments, and documenting release changes for better version tracking.
- [`testing_plan_integration`](./testing_plan_integration/SKILL.md) — Creates inline Rust-style tests, suggests refactoring for testability, analyzes code challenges, and creates comprehensive test coverage for robust code.
- [`todo`](./todo/SKILL.md) — A convenient command to quickly manage project todo items without leaving the Claude Code interface, featuring due dates, sorting, task prioritization, and comprehensive todo list management.
- [`update-branch-name`](./update-branch-name/SKILL.md) — Updates branch names with proper prefixes and formats, enforcing naming conventions, supporting semantic prefixes, and managing remote branch updates.
- [`update-docs`](./update-docs/SKILL.md) — Reviews current documentation status, updates implementation progress, reviews phase documents, and maintains documentation consistency across the project.

### CLAUDE.md Files

- [`ai-intellij-plugin`](./ai-intellij-plugin/SKILL.md) — Provides comprehensive Gradle commands for IntelliJ plugin development with platform-specific coding patterns, detailed package structure guidelines, and clear internationalization standards.
- [`avs-vibe-developer-guide`](./avs-vibe-developer-guide/SKILL.md) — Structures AI-assisted EigenLayer AVS development workflow with consistent naming conventions for prompt files and established terminology standards for blockchain concepts.
- [`aws-mcp-server`](./aws-mcp-server/SKILL.md) — Features multiple Python environment setup options with detailed code style guidelines, comprehensive error handling recommendations, and security considerations for AWS CLI interactions.
- [`basic-memory`](./basic-memory/SKILL.md) — Presents an innovative AI-human collaboration framework with Model Context Protocol for bidirectional LLM-markdown communication and flexible knowledge structure for complex projects.
- [`claude-code-mcp-enhanced`](./claude-code-mcp-enhanced/SKILL.md) — Provides detailed and emphatic instructions for Claude to follow as a coding agent, with testing guidance, code examples, and compliance checks.
- [`comm`](./comm/SKILL.md) — Serves as a development reference for E2E-encrypted messaging applications with code organization architecture, security implementation details, and testing procedures.
- [`course-builder`](./course-builder/SKILL.md) — Enables real-time multiplayer capabilities for collaborative course creation with diverse tech stack integration and monorepo architecture using Turborepo.
- [`cursor-tools`](./cursor-tools/SKILL.md) — Creates a versatile AI command interface supporting multiple providers and models with flexible command options and browser automation through "Stagehand" feature.
- [`droidconkotlin`](./droidconkotlin/SKILL.md) — Delivers comprehensive Gradle commands for cross-platform Kotlin Multiplatform development with clear module structure and practical guidance for dependency injection.
- [`edsl`](./edsl/SKILL.md) — Offers detailed build and test commands with strict code style enforcement, comprehensive testing requirements, and standardized development workflow using Black and mypy.
- [`giselle`](./giselle/SKILL.md) — Provides detailed build and test commands using pnpm and Vitest with strict code formatting requirements and comprehensive naming conventions for code consistency.
- [`guitar`](./guitar/SKILL.md) — Serves as development guide for Guitar Git GUI Client with build commands for various platforms, code style guidelines for contributing, and project structure explanation.
- [`jsbeeb`](./jsbeeb/SKILL.md) — Provides development guide for JavaScript BBC Micro emulator with build and testing instructions, architecture documentation, and debugging workflows.
- [`lamoom-python`](./lamoom-python/SKILL.md) — Serves as reference for production prompt engineering library with load balancing of AI Models, API documentation, and usage patterns with examples.
- [`langgraphjs`](./langgraphjs/SKILL.md) — Offers comprehensive build and test commands with detailed TypeScript style guidelines, layered library architecture, and monorepo structure using yarn workspaces.
- [`network-chronicles`](./network-chronicles/SKILL.md) — Presents detailed implementation plan for AI-driven game characters with technical specifications for LLM integration, character guidelines, and service discovery mechanics.
- [`note-companion`](./note-companion/SKILL.md) — Provides detailed styling isolation techniques for Obsidian plugins using Tailwind with custom prefix to prevent style conflicts and practical troubleshooting steps.
- [`pareto-mac`](./pareto-mac/SKILL.md) — Serves as development guide for Mac security audit tool with build instructions, contribution guidelines, testing procedures, and workflow documentation.
- [`perplexity-mcp`](./perplexity-mcp/SKILL.md) — Offers clear step-by-step installation instructions with multiple configuration options, detailed troubleshooting guidance, and concise architecture overview of the MCP protocol.
- [`sg-cars-trends-backend`](./sg-cars-trends-backend/SKILL.md) — Provides comprehensive structure for TypeScript monorepo projects with detailed commands for development, testing, deployment, and AWS/Cloudflare integration.
- [`spy`](./spy/SKILL.md) — Enforces strict coding conventions with comprehensive testing guidelines, multiple code compilation options, and backend-specific test decorators for targeted filtering.
- [`tpl`](./tpl/SKILL.md) — Details Go project conventions with comprehensive error handling recommendations, table-driven testing approach guidelines, and modernization suggestions for latest Go features.

### Workflows & Knowledge Guides

- [`blogging-platform-instructions`](./blogging-platform-instructions/SKILL.md) — Provides a well-structured set of commands for publishing and maintaining a blogging platform, including commands for creating posts, managing categories, and handling media files.
- [`design-review-workflow`](./design-review-workflow/SKILL.md) — A tailored workflow for enabling automated UI/UX design review, including specialized sub agents, slash commands, `CLAUDE.md` excerpts, and more. Covers a broad range of criteria from responsive design to accessibility.

### Official Documentation

- [`anthropic-quickstarts`](./anthropic-quickstarts/SKILL.md) — Offers comprehensive development guides for three distinct AI-powered demo projects with standardized workflows, strict code style guidelines, and containerization instructions.
- [`claude-code-github-actions`](./claude-code-github-actions/SKILL.md) — Official GitHub Actions integration for Claude Code with examples and documentation for automating AI-powered workflows in CI/CD pipelines.

