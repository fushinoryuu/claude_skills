# Phase 3: Standalone Skills

Three skills that need their own inputs, fixtures, and workflows, so they live in their own folders under `skills/`. They share the Phase 0 eval runner and fixture format.

- **#5 Failure Analysis:** classify why a test failed.
- **#7 Defect Drafting:** turn evidence into a structured bug report.
- **#8 Regression Test Selection:** pick which tests to run for a change.

Build in that order. #7 consumes the output of #5, and #8 is the hardest, so it goes last.

---

## #5 Failure Analysis

**Location:** `skills/failure-analysis/`

### Goal

Analyze test reports, logs, and stack traces and classify each failure as one of:

| Class                 | Meaning                                                |
| --------------------- | ------------------------------------------------------ |
| `application-defect`  | The product behaves incorrectly                        |
| `automation-issue`    | The test code is wrong, brittle, or outdated           |
| `test-data-problem`   | Data was missing, stale, conflicting, or malformed     |
| `environment-failure` | Infrastructure, network, deploy, or dependency problem |
| `unknown`             | Evidence is insufficient to decide                     |

### Design decisions

- **`unknown` is a first-class answer.** The skill must say what evidence is missing instead of guessing.
- **Evidence first.** Each classification cites the specific log line, status code, or stack frame that supports it.
- **Confidence.** Each result carries a confidence level (high, medium, low) tied to the evidence.
- **Input flexibility.** Accept pasted logs, JUnit-style XML, pytest output, Playwright or Selenium traces, and CI log text. Use scripts only to normalize formats.

### Tasks

- [ ] Write `SKILL.md` with the workflow: parse input, group related failures, classify, cite evidence, summarize, suggest next action.
- [ ] Write `references/classification-guide.md` with signals per class:
  - Application defect: assertion on business value fails, 5xx from the app with a stack trace, wrong data returned.
  - Automation issue: element not found after a UI change, timeout on a fixed wait, stale element reference, assertion on outdated text.
  - Test data problem: unique constraint violation, record not found for a seeded ID, expired token or date-dependent data.
  - Environment failure: connection refused, DNS failure, 502 or 503 from infrastructure, out-of-memory in the runner, dependency outage.
- [ ] Add the "grouping" rule: many failures with one root cause are reported once with a count.
- [ ] Optional script `scripts/normalize_report.py`: converts JUnit XML or similar into a compact JSON list of failures (test name, message, first stack frames). Unit test it with real-looking samples and malformed input.
- [ ] Define the structured findings block: `test`, `class`, `confidence`, `evidence`, `next_action`.

### Fixtures

- [ ] At least two fixtures per class, with different surface symptoms.
- [ ] A grouped case: 10 failures, one root cause.
- [ ] An ambiguous case (for example, a timeout that could be a slow environment or a missing wait) where the expected answer is `unknown` or low confidence with the missing evidence named.
- [ ] A mixed report with failures from three different classes.

### Acceptance criteria

- Classification accuracy is high on unambiguous fixtures across repeated runs.
- The ambiguous case does not receive a high-confidence guess.
- Every classification includes quoted or referenced evidence.

---

## #7 Defect Drafting

**Location:** `skills/defect-drafting/`

### Goal

Convert logs, screenshots, and API responses into a structured bug report with clear reproduction steps, ready to paste into Jira or GitHub Issues.

### Report structure

- Title: short, specific, symptom-first.
- Environment: app version, browser or client, OS, backend environment.
- Preconditions.
- Steps to reproduce, numbered, each a single action.
- Expected result.
- Actual result, with the relevant log excerpt or response body.
- Severity and priority suggestion, with a one-line reason.
- Attachments to include.
- Open questions where evidence was thin.

### Design decisions

- **Never invent steps.** If reproduction steps are inferred from a test script or logs, label them as inferred and list what to verify manually.
- **Mark unknowns.** Missing environment or version details appear under open questions, not filled with guesses.
- **Chain from #5.** Accept the structured output of Failure Analysis as an input, and only draft reports for failures classified as application defects (or on explicit request).
- **Output targets.** Provide Jira-flavored and GitHub-flavored markdown variants via a template choice. Creating the ticket is done through the MCP server only if the user asks.

### Tasks

- [ ] Write `SKILL.md` with the workflow: gather evidence, extract the minimal reproduction, draft, mark inferences, propose severity, offer to file.
- [ ] Write `references/report-template.md` with both formats and a quality checklist.
- [ ] Write `references/severity-guide.md` with a simple, adjustable rubric (data loss, security, outage, workaround available, user impact).
- [ ] Handle screenshots: describe only what is visible, and note when text in an image is unreadable.
- [ ] Add a duplicate check step: search existing issues through MCP before drafting, and mention likely duplicates.
- [ ] Define the structured findings block: `title`, `severity`, `steps_inferred` (true or false), `open_questions` count.

### Fixtures

- [ ] A failing UI test log plus a screenshot description, where steps must be inferred from the test script.
- [ ] A failing API call with request and response, where reproduction is a single request.
- [ ] A case with missing environment details, expecting open questions instead of invented values.
- [ ] A case where evidence points to an environment failure, expecting the skill to push back instead of drafting a defect.

### Acceptance criteria

- Reports contain every required section.
- Inferred steps are labeled. Missing details are listed, not invented.
- The environment-failure fixture does not produce a bug report for the product.

---

## #8 Regression Test Selection

**Location:** `skills/regression-selection/`

### Goal

Given a code change, recommend which regression tests to run, using the changed files, the modules they affect, and historical defect data.

### Inputs

- The diff or list of changed files.
- A test-to-module map (a file in the repo, such as `test-map.yaml`).
- Optional defect history (a list of past defects with the modules they touched).
- Optional test metadata: runtime, flakiness, tags.

### Output

- A ranked list of tests with a reason for each (direct module match, dependency, historical defect hotspot).
- A "must run", "should run", and "optional" split.
- Estimated total runtime when metadata is available.
- A statement of what the selection does not cover (modules with no mapped tests).

### Design decisions

- **Deterministic core.** The mapping from changed files to affected modules to candidate tests is a script. The agent adds judgment for ranking and for gaps the map cannot see.
- **Be explicit about coverage gaps.** Unmapped changed files are reported, never silently skipped.
- **Safe defaults.** When confidence is low (large change, shared library touched, config change), recommend widening the selection and say why.
- **Map format first.** Keep the test map format simple and documented so users can generate it from their own repo.

### Tasks

- [ ] Define `test-map.yaml` format and document it in `references/test-map-format.md`:

  ```yaml
  modules:
    orders:
      paths: ["src/orders/**"]
      depends_on: ["payments", "inventory"]
      tests: ["tests/orders/**", "tests/e2e/checkout.spec.ts"]
  ```

- [ ] Write `scripts/map_changes.py`:
  - [ ] Input: changed file list (or diff) and the test map.
  - [ ] Output: affected modules, direct and transitive, with candidate tests and the reason for each.
  - [ ] Report unmapped files.
  - [ ] Handle glob patterns, renames, and deleted files.
- [ ] Write `scripts/rank_tests.py` (optional): combine module distance, defect-history weight, and flakiness into a score. Keep the formula simple and documented.
- [ ] Unit test both scripts with small map and diff pairs, including cyclic dependencies, empty diffs, and overlapping paths.
- [ ] Write `SKILL.md` with the workflow: run the mapping script, review gaps, rank, apply risk adjustments, produce the report.
- [ ] Write `references/risk-signals.md`: shared libraries, config and schema changes, dependency upgrades, and auth-related code widen the selection.
- [ ] Define the structured findings block: ordered list of `{test, tier, reason}` plus `unmapped_files`.

### Fixtures

Build one small fixture repo (a handful of modules, a test map, a defect history) and several changes against it:

- [ ] A change confined to one leaf module.
- [ ] A change to a module with dependents, expecting transitive selection.
- [ ] A change to a shared utility, expecting widened selection.
- [ ] A change with an unmapped file, expecting a reported gap.
- [ ] A docs-only change, expecting an empty or minimal selection.

### Evaluation

Score with precision and recall against a hand-labeled "correct set" per change:

- **Recall** (did we include everything we needed) matters most. Treat a missed required test as a failure.
- **Precision** (did we avoid running everything) is secondary but tracked, since a selection that runs the full suite is useless.
- Report both per case and in aggregate. Set thresholds, for example recall of 1.0 on must-run tests and precision above 0.6.

### Acceptance criteria

- The mapping script is correct on all unit tests, including transitive dependencies and unmapped files.
- Evals meet the recall and precision thresholds in a majority of runs.
- Unmapped files and low-confidence situations are always called out.

---

## Phase 3 exit checklist

- [ ] Each skill has SKILL.md, references, fixtures, cases, trigger prompts, and passing structure tests.
- [ ] Trigger prompts across all four skills in the repo are checked for overlap, so "analyze this failing test" picks Failure Analysis and not PR Review.
- [ ] The #5 to #7 handoff works end to end on a shared fixture.
- [ ] Unit tests for every script run in CI.
