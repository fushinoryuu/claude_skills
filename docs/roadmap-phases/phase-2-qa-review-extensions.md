# Phase 2: Extensions to QA Review

Two capabilities that extend the Phase 1 skill instead of becoming separate skills. Each one is a lens: it loads when a changed path matches the lens's `applies_when.paths`, so it needs no new workflow step and no loading rule. They share the skill's adapters/tooling (`gh` and the Atlassian MCP server), its eval runner, and its output format.

- **#4 Automation Code Review:** review test code itself. A new `test-code` lens (QARS-35, QARS-36).
- **#3 API Contract:** go deeper on API specs and their tests. The existing `api-spec` lens grows, and a new script compares two spec versions (QARS-39, QARS-40, QARS-41).

Build in that order. #4 is nearly free. #3 adds `openapi_diff.py`, which compares two versions of a spec, and the lens work that uses it.

**#1 Requirement Review moved to Phase 3.** It reviews a ticket before any PR exists, so it does not fit the PR workflow that `qa-review` has become. It is now its own skill: see [Phase 3](phase-3-standalone-skills.md#1-requirement-review) (QARS-37, QARS-38).

## Plan

- [x] Groom the Phase 2 plan: update the roadmap and phase docs, and file the tickets below (QARS-34)

## Carried over from Phase 1

Four follow-ups moved here from Phase 1 (see [Moved to Phase 2](phase-1-qa-review-skill.md#moved-to-phase-2)). They improve the Phase 1 skill and can be built in any order, alongside the two capabilities above.

- [ ] **Copilot (QARS-22).** Run `qa-review` in VS Code Copilot and fix the differences: `${CLAUDE_SKILL_DIR}`, the `mcp__atlassian__*` tool names, `$ARGUMENTS` and `/compact`. The eval runner only calls Anthropic models, so this is checked by hand, once, and the result goes in the skill's README.
- [x] **Backend lenses (QARS-23).** Decided from real reviews of a backend project: `service` fit where it fired, and the core checks alone found real gaps on infrastructure, CI workflow and event contract changes. No lens was written. The `api-spec` paths already match the spec source files, so `**/specs/**` was not added. Reviews show what was found, not what was missed, so write a lens only when a real miss shows up, as a project lens first.
- [ ] **Several tickets per review (QARS-24).** Let `qa-review` take several Jira tickets for one or more PRs, and post one comment per ticket.
- [ ] **Project lenses (QARS-26).** Check, once, that a lens in the reviewed repo's `.claude/qa-review/lenses/` folder is loaded, and that a project lens with the same name as a bundled lens is the one that is used. The `suggest_lenses.py` unit tests cover this for the script, but it has not been checked in a real review.

## Security review (QARS-29)

A deeper security review for `qa-review`: a stack-free upgrade of the core security checks, plus an optional `security` lens for server-side code. It is not a new step, so the 12-step workflow stays as it is. The plan, the options, the eval plan and the limits are in [the design notes](../security-lens/design-notes.md). A standalone whole-repo security skill is a later, separate ticket.

- [x] Design notes and work breakdown (QARS-29)
- [x] Core security upgrade (QARS-30)
- [x] `security` lens and its categories (QARS-31)
- [x] Security fixtures, cases and eval baseline (QARS-32)

---

## #4 Automation Code Review

### Goal

When a PR contains automation or test code, review it for the problems that make suites brittle and untrustworthy.

### How it loads

As a lens, `skills/qa-review/references/lenses/test-code.md`. Its `applies_when.paths` match test and automation files (test folders, `*.test.*`, `*.spec.*`, `test_*.py`, `*_test.py`, `*_test.go`), so it loads from what the change contains, not from a project type. The checks sit under the workflow steps they belong to, mostly Step 5. Stack words (Playwright, Selenium, pytest) are allowed in a lens.

Because most test changes match, the lens also matches most older fixtures. Their stored lens lists and some case expectations change in QARS-36, and the PR names each change.

### What it checks

| Check             | What to look for                                                                                           |
| ----------------- | ---------------------------------------------------------------------------------------------------------- |
| Hardcoded data    | Literal IDs, emails, URLs, or environment-specific values in tests                                         |
| Weak assertions   | Tests that assert only that something exists, no exception was thrown, or status is 200 with no body check |
| Unstable locators | Positional XPath, auto-generated class names, text-dependent selectors where a test id exists              |
| Fixed waits       | `sleep`, `Thread.sleep`, or hardcoded timeouts instead of explicit waits on a condition                    |
| Duplicate code    | Repeated setup or step sequences that belong in a helper, fixture, or page object                          |
| Test independence | Tests that depend on order or on state left by another test                                                |
| Cleanup           | Created data never removed                                                                                 |

### Tasks

- [ ] Add the `test-code` lens (QARS-35) with the checklist above, including why each item matters, the evidence to look for, and when it is acceptable (for example, a fixed wait inside a retry utility).
- [ ] Make it framework-neutral, with short examples for the stacks you actually use (Playwright, Selenium, pytest, REST client tests). Keep examples to a few lines each (QARS-35).
- [ ] Add finding categories: `hardcoded-test-data`, `weak-assertion`, `unstable-locator`, `fixed-wait`, `duplicate-code`, `test-dependency`, `missing-cleanup` (QARS-35).
- [ ] Unit test that `suggest_lenses.py` matches the lens for test paths in several stacks and not for a docs-only change (QARS-35).
- [ ] Not ticketed: an optional script `scripts/scan_test_smells.py` (regex-based detection of obvious fixed waits and hardcoded URLs, a hint generator for the agent, not a verdict). Build it only if the eval shows the model missing those.

### Fixtures

- [ ] One fixture per smell, each a small test file diff with exactly one planted problem (QARS-36).
- [ ] A clean test diff that uses explicit waits, test ids, and meaningful assertions, expecting no findings (QARS-36).
- [ ] A tricky fixture: a fixed wait inside a documented retry helper, which should not be flagged (QARS-36).
- [ ] Regenerate `suggest_lenses.json` of the older fixtures that change a test file, and update the cases that pin a lens list (QARS-36).

### Acceptance criteria

- Each planted smell is found in a majority of runs.
- The clean and tricky fixtures produce no false positives in a majority of runs.
- The full set shows no regression on the older cases. The only intended changes are their lens lists.

---

## #3 API Contract

### Goal

Analyze an API specification (usually OpenAPI) and its changes, then suggest request validations, negative test cases, and schema checks.

### How it loads

The existing `api-spec` lens grows. It already loads on the same files (spec files, routes, controllers) and covers Step 7 for them, so a separate `api-contract.md` would duplicate it. Spec-level checks go in Step 7, and suggested negative tests go in Step 5. A script, `openapi_diff.py`, compares two spec versions. It sits next to `openapi_changed.py`, which only checks that a changed route has a matching spec change.

### What it produces

- Spec-level issues: missing required fields, loose types, undocumented error responses, inconsistent naming, breaking changes.
- Suggested negative tests per endpoint (missing required field, wrong type, boundary values, invalid enum, oversized payload, unauthorized access).
- Suggested schema assertions for response validation.
- A breaking-change report when two spec versions are compared.

### Tasks

- [ ] Write `scripts/openapi_diff.py` that compares two OpenAPI documents and outputs JSON (QARS-39):
  - [ ] Added, removed, and changed paths and methods.
  - [ ] Parameter changes (added required parameter, type change, removed parameter).
  - [ ] Request and response schema changes.
  - [ ] A `breaking: true/false` flag per change with a reason.
- [ ] Support OpenAPI 3.x in JSON and YAML (QARS-39). Swagger 2.0 is unsupported, and the script says so with a clear status. The standard library has no YAML reader, so PyYAML is a documented requirement for YAML specs. Both READMEs name it and warn that without it the review compares the specs by hand, which costs more tokens.
- [ ] Unit test the diff script with pairs of small specs covering every change type, plus identical specs, invalid input, JSON, YAML and Swagger 2.0 (QARS-39).
- [ ] Grow the `api-spec` lens with the checklist and a test-suggestion matrix (field type to negative cases) (QARS-40).
- [ ] Update SKILL.md Step 7 so the agent runs the diff script when both spec versions are available (from the base and head of the PR) and uses its output to drive the review (QARS-40).
- [ ] Add categories: `breaking-change`, `missing-error-response`, `loose-schema`, `missing-negative-tests` (QARS-40). A parameter the code uses but the spec lacks is `missing-interface-doc-update`, so there is no `undocumented-parameter` category. Add a tie-break line for it and one for `missing-negative-tests`.

### Fixtures

- [ ] Spec pair with a removed required response field (breaking) (QARS-41).
- [ ] Spec pair with a new required request parameter (breaking) (QARS-41).
- [ ] Spec pair with only an added optional field (not breaking, must not be flagged as breaking) (QARS-41).
- [ ] Single spec with an endpoint lacking 4xx responses (QARS-41).
- [ ] A new response schema that is only `type: object` with no properties (`loose-schema`) (QARS-41).
- [ ] A new endpoint whose spec has required fields and an enum, with tests that cover only the happy path (`missing-negative-tests`) (QARS-41).
- [ ] Clean spec pair expecting no findings (QARS-41).
- [ ] Add `openapi_diff.json` to the older fixtures whose diff changes a spec file (QARS-41).

### Acceptance criteria

- The diff script classifies breaking and non-breaking changes correctly across all unit test cases.
- Evals find each planted problem and do not label the non-breaking change as breaking.
- The full set shows no regression on the older cases.

---

## Phase 2 exit checklist

- [ ] Both extensions have their lens, fixtures and cases (QARS-35, QARS-36, QARS-39, QARS-40, QARS-41).
- [ ] The carried-over tickets are done or dropped (QARS-22, QARS-24, QARS-26).
- [ ] Lens choice still works: the `suggest_lenses.py` tests and the `expect.lenses` cases cover plain reviews, test code and API contract changes (QARS-42). `qa-review` is slash-only (`disable-model-invocation: true`), so it has no trigger prompts to test.
- [ ] SKILL.md remains under the line budget. If it does not, move workflow detail into references (QARS-42).
- [ ] One full run of the Phase 1 eval set covers the final state, so nothing regressed (QARS-42).
