# Phase 1: PR-Review Skill (the base)

The generic PR-review skill is the foundation the Phase 2 extensions build on. It should work across frontend, backend, and infra projects, pull its context through MCP servers, and use scripts only for deterministic checks.

## Goals

- Review a pull request against the requirements in its linked ticket (Jira or GitHub Issue).
- Check acceptance criteria coverage, unit-test coverage, and whether API specs need updating.
- Adapt its checks to the project type (frontend, backend, infra) without bloating SKILL.md.
- Produce findings in a consistent human-readable format plus a machine-readable block for evals.

## Deliverables

| Deliverable | Location |
|---|---|
| Skill definition | `skills/pr-review/SKILL.md` |
| Project-type references | `skills/pr-review/references/{frontend,backend,infra}.md` |
| Output format reference | `skills/pr-review/references/output-format.md` |
| Deterministic scripts | `skills/pr-review/scripts/` |
| Script unit tests | `tests/unit/pr_review/` |
| Fixtures and cases | `evals/pr-review/` |

## Design decisions

### No API adapters

Ticket and PR data come from MCP servers (GitHub, Atlassian). The skill describes what it needs ("the PR diff, the PR description, the linked ticket and its acceptance criteria") and lets the agent fetch it. Scripts are reserved for work that is not an API call. SKILL.md includes an "Expected tools" section with the `gh` CLI and paste-the-ticket fallbacks.

### Two modes

Carried over from the work version of the skill:

- **Initial review.** Check acceptance criteria, unit-test coverage, and API spec needs. Report findings and, if configured, comment on the ticket or PR.
- **Final review.** Run the same checks, address lingering gaps, and update a living document of recurring review issues.

Decide how the mode is selected (explicit user phrase, or inferred from PR state) and document it in SKILL.md.

### Progressive disclosure

SKILL.md holds the workflow and decision points. Project-type details live in `references/` and are loaded only when relevant. This keeps the always-loaded text small.

## Tasks

### 1. Write SKILL.md

- [ ] Frontmatter: `name: pr-review` and a `description` that states what it does and when to use it (reviewing a PR against a ticket, checking test coverage, checking API spec changes). Include trigger phrases a user would naturally say.
- [ ] **Expected tools** section: GitHub MCP (PR, diff, files, comments), Atlassian MCP (issue, acceptance criteria), with fallbacks.
- [ ] **Workflow** section, in order:
  1. Identify the PR and the linked ticket.
  2. Detect project type from changed files (see below).
  3. Extract acceptance criteria from the ticket.
  4. Map each criterion to code and tests in the diff.
  5. Run the deterministic scripts.
  6. Apply the project-type reference.
  7. Produce the report.
- [ ] **Modes** section describing initial and final behavior.
- [ ] **What to skip** section (style nitpicks a linter owns, generated files, lockfiles) to keep reviews focused.
- [ ] **Uncertainty rule:** when the ticket has no acceptance criteria, say so and flag it, do not invent criteria.

### 2. Project-type detection

- [ ] Define simple heuristics in SKILL.md: frontend (component files, CSS, `package.json` with a UI framework), backend (route handlers, services, migrations), infra (Terraform, Dockerfiles, CI config, Kubernetes manifests).
- [ ] Allow mixed PRs: apply every relevant reference.
- [ ] Allow the user to override detection.

### 3. Write the references

Each reference is a checklist the agent applies, with the reasoning behind each item so the agent can judge edge cases.

- [ ] `frontend.md`: component tests, accessibility basics, state handling, loading and error states, no hardcoded strings where i18n exists.
- [ ] `backend.md`: input validation, error handling, auth checks, migration safety, idempotency, logging of sensitive data, API spec updates.
- [ ] `infra.md`: least-privilege permissions, secrets handling, rollback path, blast radius, drift from existing patterns, plan output reviewed.
- [ ] `output-format.md`: report template and the structured findings block (see Phase 0).

### 4. Scripts (deterministic only)

| Script | Purpose |
|---|---|
| `changed_endpoints.py` | Parse a diff and list added, removed, or modified HTTP routes |
| `missing_tests.py` | Given changed source files, report which have no matching test file changes |
| `openapi_changed.py` | Report whether an OpenAPI/Swagger file changed, and whether route changes lack a matching spec change |

For each script:

- [ ] Reads a diff from a file or stdin, prints JSON.
- [ ] Handles several common frameworks for route detection, and says clearly when it cannot tell.
- [ ] Has a `--help` and a documented output schema.
- [ ] Has unit tests with small hand-written diffs, including empty diffs and malformed input.
- [ ] SKILL.md tells the agent to run the script and treat its output as a signal, not a verdict.

### 5. Report format

- [ ] Summary line with overall assessment.
- [ ] Acceptance criteria table: criterion, status (covered, partial, missing, unclear), evidence.
- [ ] Findings grouped by severity, each with file, line when known, explanation, and suggested fix.
- [ ] Structured findings block at the end for evals.
- [ ] Keep it short enough that a reviewer reads all of it.

### 6. Fixtures and cases

Each fixture is a small PR (diff, description, ticket). Planted defects:

| Fixture | Planted defect | Expected category |
|---|---|---|
| `missing-tests` | New service function with no test changes | `missing-unit-tests` |
| `criterion-not-implemented` | Ticket lists 4 criteria, diff implements 3 | `unmet-acceptance-criterion` |
| `route-without-spec` | New endpoint, OpenAPI file untouched | `missing-spec-update` |
| `no-validation` | Backend handler trusts request body | `missing-input-validation` |
| `infra-wildcard-perms` | IAM policy with `*` actions | `excessive-permissions` |
| `frontend-no-error-state` | Component fetches data, no failure path | `missing-error-handling` |
| `clean` | Well-formed PR with tests and spec update | none |

- [ ] Write each fixture to be realistic but minimal.
- [ ] Write one case per fixture, plus a mixed fixture with two defects.
- [ ] Write 8 to 10 trigger prompts of each kind.

## Acceptance criteria

- Structure and unit tests pass in CI.
- On the eval set, the skill finds each planted defect in a majority of runs and produces no more than the allowed findings on the clean PR.
- SKILL.md is under the line budget, with detail in references.
- A reader can follow the README to run the skill with only the GitHub MCP server connected.

## Risks and notes

- **Noisy reviews.** The most common failure is too many low-value findings. The clean-PR case and `max_findings` guard against it.
- **Ticket quality.** Real tickets are messy. Add at least one fixture with vague acceptance criteria to check the uncertainty rule.
- **Diff size.** Large diffs exceed what the agent can reason over carefully. Add guidance in SKILL.md for prioritizing files (source over generated, tests next to source).
