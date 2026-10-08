# claude_skills

[![CI](https://github.com/fushinoryuu/claude_skills/actions/workflows/ci.yml/badge.svg)](https://github.com/fushinoryuu/claude_skills/actions/workflows/ci.yml)

## Expected tools

The skills describe what they need (the PR diff, the linked ticket and its acceptance criteria) and let the agent fetch it with whatever is connected. They expect two tools:

| Need | Expected | Fallback |
|---|---|---|
| Pull requests, diffs, changed files, comments, GitHub Issues | The [GitHub CLI](https://cli.github.com/) (`gh pr view`, `gh pr diff`, `gh issue view`) | None |
| Jira issues, acceptance criteria, comments | The [Atlassian Rovo MCP server](https://developer.atlassian.com/cloud/rovo-mcp/) | Paste the ticket text into the chat |

Without Jira access, a skill still works if you paste the ticket text.

### Credentials

The skills never store, read, or ask for credentials. Authentication lives outside them: `gh auth login` for the GitHub CLI, and your MCP server configuration for Atlassian (see its documentation).

The one secret this repo uses is `ANTHROPIC_API_KEY`, and only for running the evals. Copy `.env.example` to `.env` and fill it in. `.env` is git-ignored.
