# QA Skills Roadmap

Build order for the PR-review skill and its related QA skills. Every skill gets the same eval kit: planted-defect fixtures, a clean case that should produce no findings, and trigger prompts.

## Phase 0: Foundation

- [ ] Repo skeleton: `skills/`, `tests/`, `evals/`, `docs/`, CI workflow
- [ ] Shared eval runner and fixture format, written once
- [ ] CI runs unit and structure tests; evals run manually
- [ ] README lists the expected MCP servers (GitHub, Atlassian) with a `gh` CLI fallback

## Phase 1: PR-review skill (the base)

- [ ] SKILL.md with an "Expected tools" section
- [ ] References for frontend, backend, and infra
- [ ] Scripts only for deterministic work (changed endpoints, missing test files)
- [ ] Fixtures: PRs with planted defects, plus one clean PR

## Phase 2: Extensions to PR review

- [ ] **#4 Automation Code Review**
  - [ ] Add a test-code reference covering hardcoded data, weak assertions, unstable locators, fixed waits, and duplicate code
  - [ ] Fixtures with each planted defect type
- [ ] **#1 Requirement Review**
  - [ ] Flag missing acceptance criteria, edge cases, and unclear requirements
  - [ ] Works from Jira and GitHub Issues via MCP
  - [ ] Fixtures: vague stories, plus one well-written story
- [ ] **#3 API Contract**
  - [ ] Spec-diff script for OpenAPI changes
  - [ ] Request validation suggestions, negative test cases, and schema checks
  - [ ] Fixtures: specs with planted gaps, plus one clean spec

## Phase 3: Standalone skills

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
