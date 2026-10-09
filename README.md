# claude_skills

[![CI](https://github.com/fushinoryuu/claude_skills/actions/workflows/ci.yml/badge.svg)](https://github.com/fushinoryuu/claude_skills/actions/workflows/ci.yml)

## Expected tools

The skills describe what they need (the PR diff, the linked ticket and its acceptance criteria) and let the agent fetch it with whatever is connected. They expect two tools:

| Need                                                         | Expected                                                                                | Fallback                            |
| ------------------------------------------------------------ | --------------------------------------------------------------------------------------- | ----------------------------------- |
| Pull requests, diffs, changed files, comments, GitHub Issues | The [GitHub CLI](https://cli.github.com/) (`gh pr view`, `gh pr diff`, `gh issue view`) | None                                |
| Jira issues, acceptance criteria, comments                   | The [Atlassian Rovo MCP server](https://developer.atlassian.com/cloud/rovo-mcp/)        | Paste the ticket text into the chat |

Without Jira access, a skill still works if you paste the ticket text.

### Credentials

The skills never store, read, or ask for credentials. Authentication lives outside them: `gh auth login` for the GitHub CLI, and your MCP server configuration for Atlassian (see its documentation).

The one secret this repo uses is `ANTHROPIC_API_KEY`, and only for running the evals. Copy `.env.example` to `.env` and fill it in. `.env` is git-ignored.

## Common commands

Set up with [uv](https://docs.astral.sh/uv/): `uv sync` installs the pinned Python version (from `.python-version`) and the dependencies. Then run tasks with `uv run poe <task>`; they are defined in `pyproject.toml`.

| Command                                     | What it does                                                                                                                        |
| ------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `uv run poe lint`                           | Lint with ruff                                                                                                                      |
| `uv run poe unit`                           | Unit tests (`tests/unit`)                                                                                                           |
| `uv run poe structure`                      | Structure tests for every skill (`tests/structure`)                                                                                 |
| `uv run poe test`                           | All tests                                                                                                                           |
| `uv run poe check`                          | Lint, then all tests. Same coverage as CI.                                                                                          |
| `uv run poe eval --skill <name> [--runs N]` | Run a skill's eval cases against the model. Add `--triggers` for the trigger tests, or `--dry-run` to preview the prompts for free. |
| `uv run poe eval-sample`                    | Run the eval cases of the sample skill used to test the runner                                                                      |
| `uv run poe triggers-sample`                | Run the trigger tests of the sample skill                                                                                           |

The eval commands call the Anthropic API, so they need `ANTHROPIC_API_KEY` and cost a small amount per run. Lint and tests do not. See [docs/eval-format.md](docs/eval-format.md) for how evals work.
