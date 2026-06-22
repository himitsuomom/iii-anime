---
name: claude-code-github-actions
description: >-
  Official GitHub Actions integration for Claude Code with examples and documentation for
  automating AI-powered workflows in CI/CD pipelines. (Official Documentation, via
  awesome-claude-code).
---

# Claude Code GitHub Actions

- **Author:** [Anthropic](https://github.com/anthropics)
- **License:** MIT
- **Source:** https://github.com/anthropics/claude-code-action/tree/main/examples
- **Imported from:** [awesome-claude-code](https://github.com/anthropics/awesome-claude-code)
- **Category:** Official Documentation

name: Auto Fix CI Failures

on:
  workflow_run:
    workflows: ["CI"]
    types:
      - completed

permissions:
  contents: write
  pull-requests: write
  actions: read
  issues: write
  id-token: write # Required for OIDC token exchange

jobs:
  auto-fix:
    if: |
      github.event.workflow_run.conclusion == 'failure' &&
      github.event.workflow_run.pull_requests[0] &&
      !startsWith(github.event.workflow_run.head_branch, 'claude-auto-fix-ci-')
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          ref: ${{ github.event.workflow_run.head_branch }}
          fetch-depth: 0
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Setup git identity
        run: |
          git config --global user.email "claude[bot]@users.noreply.github.com"
          git config --global user.name "claude[bot]"

      - name: Create fix branch
        id: branch
        run: |
          BRANCH_NAME="claude-auto-fix-ci-${{ github.event.workflow_run.head_branch }}-${{ github.run_id }}"
          git checkout -b "$BRANCH_NAME"
          echo "branch_name=$BRANCH_NAME" >> $GITHUB_OUTPUT

      - name: Get CI failure details
        id: failure_details
        uses: actions/github-script@v7
        with:
          script: |
            const run = await github.rest.actions.getWorkflowRun({
              owner: context.repo.owner,
              repo: context.repo.repo,
              run_id: ${{ github.event.workflow_run.id }}
            });

            const jobs = await github.rest.actions.listJobsForWorkflowRun({
              owner: context.repo.owner,
              repo: context.repo.repo,
              run_id: ${{ github.event.workflow_run.id }}
            });

            const failedJobs = jobs.data.jobs.filter(job => job.conclusion === 'failure');

            let errorLogs = [];
            for (const job of failedJobs) {
              const logs = await github.rest.actions.downloadJobLogsForWorkflowRun({
                owner: context.repo.owner,
                repo: context.repo.repo,
                job_id: job.id
              });
              errorLogs.push({
                jobName: job.name,
                logs: logs.data
              });
            }

            return {
              runUrl: run.data.html_url,
              failedJobs: failedJobs.map(j => j.name),
              errorLogs: errorLogs
            };

      - name: Fix CI failures with Claude
        id: claude
        uses: anthropics/claude-code-action@v1
        with:
          prompt: |
            /fix-ci 
            Failed CI Run: ${{ fromJSON(steps.failure_details.outputs.result).runUrl }}
            Failed Jobs: ${{ join(fromJSON(steps.failure_details.outputs.result).failedJobs, ', ') }}
            PR Number: ${{ github.event.workflow_run.pull_requests[0].number }}
            Branch Name: ${{ steps.branch.outputs.branch_name }}
            Base Branch: ${{ github.event.workflow_run.head_branch }}
            Repository: ${{ github.repository }}

            Error logs:
            ${{ toJSON(fromJSON(steps.failure_details.outputs.result).errorLogs) }}
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          claude_args: "--allowedTools 'Edit,MultiEdit,Write,Read,Glob,Grep,LS,Bash(git:*),Bash(bun:*),Bash(npm:*),Bash(npx:*),Bash(gh:*)'"

## Additional Files

- [`claude.yml`](./claude.yml)
- [`issue-deduplication.yml`](./issue-deduplication.yml)
- [`issue-triage.yml`](./issue-triage.yml)
- [`manual-code-analysis.yml`](./manual-code-analysis.yml)
- [`pr-review-comprehensive.yml`](./pr-review-comprehensive.yml)
- [`pr-review-filtered-authors.yml`](./pr-review-filtered-authors.yml)
- [`pr-review-filtered-paths.yml`](./pr-review-filtered-paths.yml)

