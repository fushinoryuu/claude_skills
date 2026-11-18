# QA Skills Roadmap

Build order for the qa-review skill and its related QA skills. Every skill gets the same eval kit: planted-defect fixtures, a clean case that should produce no findings, and trigger prompts.

## Phase 0: Foundation

- [x] Repo skeleton: `skills/`, `tests/`, `evals/`, `docs/`, CI workflow
- [x] Shared eval runner and fixture format, written once
- [x] CI runs unit and structure tests; evals run manually
- [x] README lists the expected tooling: Atlassian MCP server and GitHub CLI
- [x] Short task commands for lint, tests, and evals (`uv run poe <task>`), documented in the README

## Phase 1: QA-review skill (the base)

- [x] SKILL.md with an "Expected tools" section
- [x] Project-agnostic core QA checklist (works on any kind of project), plus optional stack lenses (chosen from what the change touches) as examples
- [x] Scripts only for deterministic work (changed endpoints, missing test files)
- [x] Fixtures: PRs with planted defects, plus one clean PR

## Phase 2: Extensions to QA review

- [ ] **Carried over from Phase 1**
  - [ ] Run `qa-review` in VS Code Copilot (QARS-22)
  - [x] Backend lenses, written from real misses (QARS-23)
  - [ ] Review several Jira tickets for one or more PRs, one comment per ticket (QARS-24)
  - [ ] Check that a project lens in the repo's `.claude` folder loads and replaces a bundled lens of the same name (QARS-26)
- [x] **Groom the Phase 2 plan** (QARS-34)
- [ ] **#4 Automation Code Review** (a `test-code` lens)
  - [ ] Add the lens: hardcoded data, weak assertions, unstable locators, fixed waits, duplicate code, test independence and cleanup, with categories (QARS-35)
  - [ ] Fixtures with each planted defect type, cases and eval baseline (QARS-36)
- [ ] **#3 API Contract** (grow the `api-spec` lens)
  - [ ] Spec-diff script for OpenAPI changes, `openapi_diff.py` (QARS-39)
  - [ ] Grow the lens: request validation suggestions, negative test cases and schema checks, and run the script in Step 7 (QARS-40)
  - [ ] Fixtures: specs with planted gaps, plus one clean spec, cases and eval baseline (QARS-41)
- [x] **Security review (QARS-29)**
  - [x] Design notes and work breakdown (QARS-29)
  - [x] Core security upgrade (QARS-30)
  - [x] `security` lens and its categories (QARS-31)
  - [x] Security fixtures, cases and eval baseline (QARS-32)
- [ ] **Phase 2 exit check** (QARS-42)

## Phase 3: Standalone skills

- [ ] **#1 Requirement Review** (its own skill, moved from Phase 2)
  - [ ] Add the `requirement-review` skill: missing acceptance criteria, edge cases and unclear requirements, from Jira (Atlassian MCP) and GitHub Issues (`gh`) (QARS-37)
  - [ ] Fixtures: vague stories, plus one well-written story, cases and eval baseline (QARS-38)
- [ ] **#5 Failure Analysis**
  - [ ] Classify failures as application defect, automation issue, test data problem, or environment failure
  - [ ] Fixture logs and stack traces for each class
  - [ ] One ambiguous case to check that it admits uncertainty
- [ ] **#7 Defect Drafting**
  - [ ] Turn #5 output, logs, screenshots, and API responses into structured bug reports
  - [ ] Fixtures where repro steps must be inferred
- [ ] **#8 Regression Test Selection**
  - [ ] Script to map code diffs to modules
  - [ ] Fixture repo with a known test-to-module map
  - [ ] Use historical defects as a ranking signal
  - [ ] Eval scored on precision and recall

## Phase 4: Polish

- [ ] Docs for each skill, with an example input and output
- [ ] Short demo (GIF or transcript) in the README
- [ ] Resume bullet tying the project together
