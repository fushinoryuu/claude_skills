# CLAUDE.md

QA skills for AI coding agents, with a shared eval runner. The first skill is `qa-review` (`skills/qa-review/`). This file is for coding agents working in this repo.

## Where things are

- [README.md](README.md): expected tools, setup, commands.
- [docs/ROADMAP.md](docs/ROADMAP.md): the checklist for the whole project. Detail for each phase is in `docs/roadmap-phases/`.
- [docs/eval-format.md](docs/eval-format.md): how evals work. [docs/baseline-eval.md](docs/baseline-eval.md): the last full result.
- `skills/<name>/`: a skill (`SKILL.md`, `references/`, `assets/`, `scripts/`). Its eval kit is in `evals/<name>/`.
- `TODO.md`: the user's personal list. It is git-ignored and never part of a commit or PR.

## Commands

- `uv sync`, then `uv run poe check` runs lint and all tests. Do this before saying work is done.
- `npm run format:check-md` checks the Markdown with Prettier. `npm run format:write-md` fixes it. CI enforces it, and `poe check` does not include it, so run both. Node 24 or newer is needed.
- `uv run poe eval --skill <name> --dry-run` shows the eval prompts and costs nothing.

## How to work with me

**Pull requests**

- Keep them small, one topic each. A skill change comes with its eval result in the PR description.
- Fill in `.github/pull_request_template.md`. Every PR gets a "How it works" walkthrough for a reviewer who has not seen the code.
- Hand the PR body over in one four-backtick fenced block with no code fences inside it. Start that message with one short line, "Written for: …", naming the audience.
- I create branches, commit and push. Do not do those unless I ask. Give me the branch name (`QARS-<n>-short-name`) and the commit commands.
- Do not tick the PR checklist boxes. I tick them. Say which ones you checked.
- When a roadmap item is finished, tick it in its phase doc and in `docs/ROADMAP.md` in the same change. A PR with no roadmap item gets a ticked box that says "Not applicable" and why.

**Jira**

- There are three main projects: QARS, BEP, and ALP. Most of the work in this repo will be using the QARS project. Call `getAccessibleAtlassianResources` once for the `cloudId`. Deferred Atlassian tools are loaded with ToolSearch.
- Keep tickets few. Group related follow-ups into one ticket, with Context, Scope, Out of scope and Acceptance Criteria.
- Ask before creating or editing tickets. The one exception is the `qa-review` review comment, which the skill posts without asking, unless it derived the acceptance criteria. Then it shows a draft first and waits for a yes. Never change a ticket's status and never delete a ticket: I move tickets to Done by hand. QARS-8 is my scratchpad, so leave it alone.

**Evals and secrets**

- Evals call the Anthropic API and cost money. I run the full evals. Run one only when it is needed and say what it will cost. Do not edit files while an eval is running.
- Do not read `.env`, and never repeat a key.

**The `qa-review` skill**

- Dogfood it: review our own PRs with `/qa-review <initial|final> <KEY> <PR#>`.
- Before changing its behavior, read the ground rules in `skills/qa-review/SKILL.md` and `docs/roadmap-phases/phase-1-qa-review-skill.md`. If a change conflicts with them, ask.
- The skill never changes a ticket's status and never commits or pushes.

**Writing and reporting**

- Plain words and short sentences, in docs, PRs and replies.
- Report what happened, including failures, and say what was not run. Do not say it works when it was not checked.
- Use they/them for anyone whose pronouns are not stated.
