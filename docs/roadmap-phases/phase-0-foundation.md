# Phase 0: Foundation

Everything the later phases depend on: repo structure, a shared eval runner, CI, and a README that sets expectations about tooling. Doing this once means every skill added afterward only has to supply content (SKILL.md, references, fixtures), not infrastructure.

## Goals

- One repo that holds several skills without them stepping on each other.
- One eval runner and one fixture format shared by every skill.
- Fast, deterministic checks in CI. Slow, model-driven evals run on demand.
- A clear statement of which MCP servers the skills expect and what to do without them.

## Deliverables

| Deliverable                          | Location                   |
| ------------------------------------ | -------------------------- |
| Repo skeleton                        | repo root                  |
| Shared eval runner                   | `evals/runner/`            |
| Fixture and case format spec         | `docs/eval-format.md`      |
| Structure tests                      | `tests/structure/`         |
| CI workflow                          | `.github/workflows/ci.yml` |
| README with "Expected tools" section | `README.md`                |

## Target repo layout

```
.
├── README.md
├── .env.example
├── .github/workflows/ci.yml
├── skills/
│   ├── pr-review/            # Phase 1
│   │   ├── SKILL.md
│   │   ├── references/
│   │   ├── scripts/
│   │   └── assets/
│   ├── failure-analysis/     # Phase 3
│   ├── defect-drafting/      # Phase 3
│   └── regression-selection/ # Phase 3
├── tests/
│   ├── unit/                 # script tests
│   └── structure/            # skill structure checks
├── evals/
│   ├── runner/
│   ├── pr-review/
│   │   ├── fixtures/
│   │   ├── cases/
│   │   └── triggers.yaml
│   └── ...                   # one folder per skill
└── docs/
```

Phase 2 items (#4, #1, #3) are extensions of `pr-review`, so they live inside that skill's `references/` and `scripts/` folders, not as separate skills.

## Tasks

### 1. Repo skeleton

- [x] Create the folder structure above with placeholder `.gitkeep` files where needed.
- [x] Add a `.gitignore` (Python cache, `.env`, eval output folders).
- [x] Add `.env.example` listing only what is still needed. With MCP servers handling Jira and GitHub access, this may be limited to the model API key used by the eval runner.
- [x] Choose the script language once (Python is the usual pick) and pin a version.

### 2. Eval format

Define the format before writing any fixtures. Suggested shape:

```
evals/<skill>/
├── fixtures/<fixture-name>/      # inputs the agent will see
│   ├── pr.diff
│   ├── ticket.md
│   └── ...
└── cases/<case-name>.yaml
```

A case file:

```yaml
id: pr-review-missing-tests-01
skill: pr-review
fixture: missing-tests
prompt: "Review this PR against the ticket."
expect:
  findings:
    - category: missing-unit-tests
      file: src/orders/service.py
  must_not_flag: []        # categories that must not appear
  max_findings: 8          # guard against noisy output
tags: [defect]
```

A clean case sets `findings: []` and a low `max_findings`, so it fails if the skill invents problems.

Decisions to record in `docs/eval-format.md`:

- [x] **Structured findings block.** Each skill ends its output with a machine-readable block (JSON) listing `category`, `file`, `severity`, and a one-line `summary`. This lets the runner score without a judge model.
- [x] **Category vocabulary.** Keep one shared list of category slugs per skill so cases and skills agree on names.
- [x] **Scoring.** Per case: recall of planted defects, count of unexpected findings, and pass/fail. Per run: aggregate recall and false-positive rate.
- [x] **Optional judge pass.** A second model call that grades quality (is the explanation correct and actionable). Off by default, since it costs money and adds variance.
- [x] **Fixture delivery.** Fixtures are pasted into the eval prompt (or mounted as files). They stand in for what the MCP servers would normally return, so no API mocks are needed.

### 3. Eval runner

- [x] CLI: `python -m evals.runner --skill pr-review [--case ID] [--runs N]`.
- [x] Load the skill's SKILL.md and references, assemble the prompt with the fixture, call the model, and capture output.
- [x] Parse the structured findings block and score against the case.
- [x] Support `--runs N` to repeat each case, since model output varies. Report pass rate across runs, not a single result.
- [x] Write results to `evals/results/<timestamp>.json` (git-ignored) and print a summary table.
- [x] Unit test the parser and scorer with canned model outputs (these tests run in CI and cost nothing).

### 4. Trigger tests

A skill that never triggers, or triggers on everything, is useless. Per skill, keep `triggers.yaml`:

```yaml
should_trigger:
  - "Review this PR against PROJ-123"
  - "Can you check my pull request for missing tests?"
should_not_trigger:
  - "Write a function that parses dates"
  - "Explain what a pull request is"
```

- [x] Runner mode that presents each prompt with the skill's name and description only, and records whether the model would select the skill.
- [ ] Aim for 8 to 10 prompts of each kind per skill, including near-misses.

### 5. Structure tests (run in CI)

Deterministic checks over every `skills/*/SKILL.md`:

- [x] Frontmatter parses and contains `name` and `description`.
- [x] `name` matches the folder name.
- [x] `description` is present, specific, and under a set length.
- [x] Every file referenced from SKILL.md exists.
- [x] No reference file is orphaned (exists but is never mentioned).
- [x] SKILL.md stays under a line budget (for example 500 lines), with detail pushed into `references/`.
- [x] Every skill has an `evals/<skill>/triggers.yaml` and at least one clean case.

### 6. CI

- [x] GitHub Actions workflow triggered on push and pull request.
- [x] Jobs: lint, unit tests, structure tests.
- [x] Evals are not part of CI. Add a manually triggered workflow (`workflow_dispatch`) for them later if wanted, using a repository secret for the API key.
- [x] Add a status badge to the README.

### 7. README tooling section

- [x] List expected tooling: GitHub CLI (PRs, issues) and Atlassian MCP (Jira).
- [x] State the fallback: if no Jira access, paste the ticket text.
- [x] Explain that the skills never store credentials; auth lives in the MCP configuration.

## Acceptance criteria

- `pytest tests/` passes locally and in CI on a fresh clone.
- The eval runner executes one dummy case end to end and prints a score.
- Adding a new skill requires only: a skill folder, an eval folder, and passing structure tests.

## Risks and notes

- **Eval variance.** The same case can pass or fail between runs. Use `--runs` and judge by pass rate.
- **Over-building the runner.** Keep it small. A few hundred lines is enough. Resist adding a dashboard.
- **Category drift.** If skills and cases disagree on category names, scores become meaningless. Keep the vocabulary in one file per skill and test that cases only use listed slugs.
