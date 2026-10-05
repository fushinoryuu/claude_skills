# Phase 2: Extensions to PR Review

Three capabilities that extend the Phase 1 skill instead of becoming separate skills. They share its adapters (MCP), its eval runner, and its output format.

- **#4 Automation Code Review:** review test code itself.
- **#1 Requirement Review:** review the ticket before code is written.
- **#3 API Contract:** go deeper on API specs and their tests.

Build in that order. #4 is nearly free, #1 reuses acceptance-criteria logic, and #3 introduces the first script that does real work.

---

## #4 Automation Code Review

### Goal

When a PR contains automation or test code, review it for the problems that make suites brittle and untrustworthy.

### What it checks

| Check | What to look for |
|---|---|
| Hardcoded data | Literal IDs, emails, URLs, or environment-specific values in tests |
| Weak assertions | Tests that assert only that something exists, no exception was thrown, or status is 200 with no body check |
| Unstable locators | Positional XPath, auto-generated class names, text-dependent selectors where a test id exists |
| Fixed waits | `sleep`, `Thread.sleep`, or hardcoded timeouts instead of explicit waits on a condition |
| Duplicate code | Repeated setup or step sequences that belong in a helper, fixture, or page object |
| Test independence | Tests that depend on order or on state left by another test |
| Cleanup | Created data never removed |

### Tasks

- [ ] Add `skills/pr-review/references/test-code.md` with the checklist above, including why each item matters and when it is acceptable (for example, a fixed wait inside a retry utility).
- [ ] Add a project-type detection rule: changed files under test directories, or matching test naming patterns, load this reference.
- [ ] Make the reference framework-neutral, with short examples for common stacks you actually use (for example Playwright, Selenium, pytest, REST client tests). Keep examples to a few lines each.
- [ ] Optional script `scripts/scan_test_smells.py`: regex-based detection of obvious fixed waits and hardcoded URLs. It is a hint generator for the agent, not a verdict. Unit test it.
- [ ] Add finding categories: `hardcoded-test-data`, `weak-assertion`, `unstable-locator`, `fixed-wait`, `duplicate-code`, `test-dependency`, `missing-cleanup`.

### Fixtures

- [ ] One fixture per smell, each a small test file diff with exactly one planted problem.
- [ ] A clean test diff that uses explicit waits, test ids, and meaningful assertions, expecting no findings.
- [ ] A tricky fixture: a fixed wait inside a documented retry helper, which should not be flagged.

### Acceptance criteria

- Each planted smell is found in a majority of runs.
- The clean and tricky fixtures produce no false positives in a majority of runs.

---

## #1 Requirement Review

### Goal

Review a ticket or user story before implementation and identify missing acceptance criteria, unhandled edge cases, and unclear requirements. This is the same logic the PR review uses to extract criteria, run earlier in the lifecycle.

### What it produces

- A list of missing or weak acceptance criteria.
- Edge cases the story does not address (empty states, limits, concurrency, permissions, failure modes).
- Ambiguous wording, each with a clarifying question.
- A readiness verdict: ready, needs clarification, or not ready.

### Tasks

- [ ] Add `skills/pr-review/references/requirement-review.md` covering a story-quality checklist: clear actor and goal, testable criteria, defined error behavior, non-functional needs, dependencies, out-of-scope statement.
- [ ] Add a "Requirement review" entry point in SKILL.md, triggered when the user asks to review a ticket or story with no PR attached.
- [ ] Share the criterion-extraction step with the PR workflow so there is one definition of "acceptance criterion".
- [ ] Define how clarifying questions are phrased: specific, answerable, grouped by theme, with a suggested default when one is reasonable.
- [ ] Source support: Jira issues and GitHub Issues via MCP, with paste-in text as a fallback.
- [ ] Add categories: `missing-acceptance-criteria`, `untestable-criterion`, `unhandled-edge-case`, `ambiguous-requirement`, `missing-nonfunctional`.

### Fixtures

- [ ] A story with no acceptance criteria.
- [ ] A story with vague criteria ("should be fast", "user-friendly").
- [ ] A story with a contradiction between two criteria.
- [ ] A story missing error behavior.
- [ ] A well-written story with testable criteria, expecting a "ready" verdict and few or no findings.

### Acceptance criteria

- Each planted gap is found in a majority of runs.
- The well-written story is not rejected.
- Clarifying questions are specific enough to answer in one sentence.

---

## #3 API Contract

### Goal

Analyze an API specification (usually OpenAPI) and its changes, then suggest request validations, negative test cases, and schema checks.

### What it produces

- Spec-level issues: missing required fields, loose types, undocumented error responses, inconsistent naming, breaking changes.
- Suggested negative tests per endpoint (missing required field, wrong type, boundary values, invalid enum, oversized payload, unauthorized access).
- Suggested schema assertions for response validation.
- A breaking-change report when two spec versions are compared.

### Tasks

- [ ] Add `skills/pr-review/references/api-contract.md` with the checklist and a test-suggestion matrix (field type to negative cases).
- [ ] Write `scripts/openapi_diff.py` that compares two OpenAPI documents and outputs JSON:
  - [ ] Added, removed, and changed paths and methods.
  - [ ] Parameter changes (added required parameter, type change, removed parameter).
  - [ ] Response schema changes.
  - [ ] A `breaking: true/false` flag per change with a reason.
- [ ] Support OpenAPI 3.x in JSON and YAML. State clearly that Swagger 2.0 is unsupported or handled, whichever you choose.
- [ ] Unit test the diff script with pairs of small specs covering every change type, plus identical specs and invalid input.
- [ ] Update SKILL.md so the agent runs the diff script when both spec versions are available (from the base and head of the PR) and uses its output to drive the review.
- [ ] Add categories: `breaking-change`, `missing-error-response`, `loose-schema`, `missing-negative-tests`, `undocumented-parameter`.

### Fixtures

- [ ] Spec pair with a removed required response field (breaking).
- [ ] Spec pair with a new required request parameter (breaking).
- [ ] Spec pair with only an added optional field (not breaking, must not be flagged as breaking).
- [ ] Single spec with an endpoint lacking 4xx responses.
- [ ] Clean spec pair expecting no findings.

### Acceptance criteria

- The diff script classifies breaking and non-breaking changes correctly across all unit test cases.
- Evals find each planted problem and do not label the non-breaking change as breaking.

---

## Phase 2 exit checklist

- [ ] All three extensions have references, fixtures, cases, and trigger prompts.
- [ ] Trigger tests confirm the skill still activates for plain PR review and does not misfire on unrelated requests.
- [ ] SKILL.md remains under the line budget. If it does not, move workflow detail into references.
- [ ] Re-run the full Phase 1 eval set to confirm nothing regressed.
