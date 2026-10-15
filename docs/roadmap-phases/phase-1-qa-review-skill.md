# Phase 1: QA-Review Skill (the base)

The generic `qa-review` skill is the foundation the Phase 2 extensions build on. It must work on **any project where a QA engineer would be asked to review code or a feature**, whatever the stack, domain, or type of project. It pulls its context through the `gh` CLI (GitHub) and the Atlassian MCP server (Jira), and uses scripts only for deterministic checks.

## Scope principle: project-agnostic by design

The skill is a QA review, not a frontend, backend, or infra review. Frontend, backend, and infra are only examples of where it might be used, and none of them gets special treatment in the core design. The same skill should be just as usable on a mobile app, a CLI tool, a data pipeline, a library or SDK, a game, an ML service, an embedded project, or a docs-only change.

What this means in practice:

- **The core review is universal.** It asks the questions a QA engineer asks on every change: does it meet the requirements, how is it tested, what could break, what is untested or unclear. None of these depends on the stack.
- **No project-type label.** The skill never needs to classify the project (frontend, backend, infra, and so on) before it can review it. It reads the ticket, the change, and the surrounding repo, and works from there. Choosing a lens is a separate step based on what the change touches (see "Lens selection"), and "core only" is always a valid result.
- **Stack knowledge is optional and additive.** Stack-specific guidance, if wanted, is a small optional "lens" file that adds checks on top of the core. A project with no matching lens gets the full core review, not a degraded one.
- **No stack assumptions in the wording.** SKILL.md and the core reference say "the change", "the feature", "the interface", and "the tests", not "the component", "the endpoint", or "the service", unless a lens is the one speaking.
- **Fixtures prove it.** The eval set deliberately spans different kinds of projects, so a skill that only works for web apps fails the evals.

## Goals

- Review a pull request or feature against the requirements in its linked ticket (Jira or GitHub Issue), on any kind of project.
- Check acceptance criteria coverage, test coverage, and whether any interface or contract documentation needs updating (for example an API spec, a CLI help text, a schema, or a README).
- Apply a universal QA checklist, and layer on optional stack-specific lenses when they exist, without bloating SKILL.md.
- Produce findings in a consistent human-readable format plus a machine-readable block for evals.

## Deliverables

| Deliverable                           | Location                                       |
| ------------------------------------- | ---------------------------------------------- |
| Skill definition                      | `skills/qa-review/SKILL.md`                    |
| Core QA review checklist (universal)  | `skills/qa-review/references/qa-core.md`       |
| Optional stack lenses (examples only) | `skills/qa-review/references/lenses/`          |
| Output format reference               | `skills/qa-review/references/output-format.md` |
| Deterministic scripts                 | `skills/qa-review/scripts/`                    |
| Script unit tests                     | `tests/unit/qa_review/`                        |
| Fixtures and cases                    | `evals/qa-review/`                             |

## Design decisions

### No API adapters

PR data comes from the `gh` CLI and ticket data from the Atlassian MCP server. The skill describes what it needs ("the PR diff, the PR description, the linked ticket and its acceptance criteria") and lets the agent fetch it. Scripts are reserved for work that is not an API call. SKILL.md includes an "Expected tools" section with the paste-the-ticket fallback for Jira.

### Token-conscious fetching

Token spend matters, both for this repo's evals and for a team running the skill daily. That is the main reason GitHub goes through the CLI instead of an MCP server:

- An MCP server puts every tool definition into context, whether or not the tools are used, and its tools tend to return full JSON objects.
- With `gh`, the agent chooses exactly which fields to request (`--json`), can filter with `--jq`, `head`, or `grep`, and pays only for what it reads.
- Jira has no equivalent CLI, so it stays on MCP. The skill fetches the ticket once and works from the extracted acceptance criteria afterwards.

SKILL.md carries these rules (see Task 1): list the changed files first, request only the fields needed, read diffs only for files that matter, and never silently truncate. The effect is easy to measure: `/context` in Claude Code shows what an MCP server's tool definitions cost.

### Two modes

Carried over from the work version of the skill:

- **Initial review.** Check acceptance criteria, unit-test coverage, and API spec needs. Report findings and, if configured, comment on the ticket or PR.
- **Final review.** Run the same checks, address lingering gaps, and update a living document of recurring review issues.

Decide how the mode is selected (explicit user phrase, or inferred from PR state) and document it in SKILL.md.

### Progressive disclosure

SKILL.md holds the workflow and decision points. The universal checklist lives in `references/qa-core.md`, and optional stack lenses live in `references/lenses/`, loaded only when relevant. This keeps the always-loaded text small.

### Core plus optional lenses

- **Core (`qa-core.md`)** is always applied and is written without reference to any stack.
- **Lenses** are optional, short, and additive. They exist for convenience when a team wants extra stack-specific checks, never because the skill needs them to function.
- Lenses are chosen from what the change actually touches, not from a project label. If nothing matches, the core review stands on its own.
- Adding a lens must never require editing SKILL.md beyond a one-line mention, so a user can add one for their own stack (game, mobile, data, embedded, anything).

### Lens selection (instead of project-type detection)

Deciding which lens to load is real work, and it is done from evidence about the change, not from a project label. A label forces one answer onto mixed or unusual repos, fails silently when wrong, and is the wrong unit anyway: a frontend repo can ship a PR that only edits a deployment file.

- **Declared signals.** Each lens opens with an `applies_when` block: `paths` (file globs, used by the script) and `touches` (one plain-language line, used by the agent's judgment). Proposed format:

  ```yaml
  ---
  name: web-ui
  description: One line on what this lens adds beyond the core.
  applies_when:
    paths: ["**/*.tsx", "**/*.vue", "**/*.css"]
    touches: "user-facing screens, components, or styles"
  ---
  ```

- **Deterministic hint.** `suggest_lenses.py` matches the changed-file list against every lens's `paths` and prints the candidate lenses with the files that matched. Like the other scripts, its output is a signal, not a verdict.
- **Judgment and transparency.** The agent decides: it may apply several lenses, one, or none. The report names each lens applied and why, or says "core only".
- **Lazy loading.** Only the lenses that matched are read, so unmatched lenses cost no tokens.
- **Overrides.** The user can name a lens, or say "core only".
- **Never required.** No match, no `lenses/` folder, or an unreadable lens file means the core review runs unchanged.

## Tasks

### 1. Write SKILL.md

- [ ] Frontmatter: `name: qa-review` and a `description` that states what it does and when to use it (a QA review of a PR or feature against its ticket, checking test coverage, checking whether interface or contract docs need updating). Include trigger phrases a user would naturally say, and keep the description free of stack-specific words so it triggers on any kind of project.
- [ ] State near the top of SKILL.md that the skill is project-agnostic and applies to any code or feature a QA engineer would review.
- [ ] **Expected tools** section: the `gh` CLI (PR, diff, files, comments, GitHub Issues), the Atlassian MCP server (Jira issue, acceptance criteria), and the paste-the-ticket fallback when Jira is not available.
- [ ] **Fetching** section, to keep token use down:
  - List the changed files first (`gh pr diff <n> --name-only`, or `gh pr view <n> --json files`) and apply "What to skip" before reading any diff.
  - Request only the fields needed (`gh pr view <n> --json title,body,files`), not the full object.
  - Read diffs only for the files that matter, filtering by path with shell tools or `gh api` with `--jq`. Never fetch lockfile or generated-file diffs.
  - Fetch the ticket and the PR once per review and work from the extracted criteria and file list, not repeated fetches.
  - When the diff is too large to review carefully, review the highest-risk files first and say which files were skipped. Do not silently truncate.
- [ ] **Workflow** section, in order:
  1. Identify the PR (or feature) and the linked ticket.
  2. Read the change and its surroundings to understand what it touches (see "Understanding the change" below).
  3. Extract acceptance criteria from the ticket.
  4. Map each criterion to code and tests in the diff.
  5. Run the deterministic scripts, including the lens hint.
  6. Select lenses (see "Lens selection"), then apply the core QA checklist plus any selected lens.
  7. Produce the report.
- [ ] **Modes** section describing initial and final behavior.
- [ ] **What to skip** section (style nitpicks a linter owns, generated files, lockfiles) to keep reviews focused.
- [ ] **Uncertainty rule:** when the ticket has no acceptance criteria, say so and flag it, do not invent criteria.

### 2. Understanding the change and selecting lenses (replaces project-type detection)

The skill does not classify the project as frontend, backend, or infra before reviewing. It builds a plain-language picture of the change, and picks lenses from what the change touches.

- [ ] Add a short step in SKILL.md: before reviewing, state what the change does, what it touches (user-facing behavior, data, interfaces, configuration, build or deploy, tests, docs), and how it is exercised or tested in this repo.
- [ ] Infer the test approach from the repo itself (existing test folders, naming patterns, CI config) instead of assuming a framework.
- [ ] Treat unfamiliar stacks as normal. If the stack is unfamiliar, the skill says so and applies the core checklist rather than guessing at stack conventions.
- [ ] Allow mixed or unusual changes (code plus config plus docs, or a repo that fits no common category) without special handling.
- [ ] Allow the user to name a lens explicitly, or to say "core only".
- [ ] Add a short "Lens selection" step in SKILL.md: run `suggest_lenses.py` on the changed files, read only the lenses it names (plus any the user asked for), apply judgment, and state which lenses were applied and why, or "core only". Any number of lenses, including none, is valid.

### 3. Write the references

Each reference is a checklist the agent applies, with the reasoning behind each item so the agent can judge edge cases.

- [ ] `qa-core.md` (universal, always applied), written with no stack assumptions. Suggested sections:
  - **Requirements:** every acceptance criterion is implemented and testable; behavior beyond the ticket is called out; unclear requirements are flagged, not assumed.
  - **Test coverage:** new and changed behavior has tests at an appropriate level; tests assert real outcomes; failure paths are tested, not only the happy path.
  - **Edge cases and inputs:** empty, maximum, invalid, duplicate, and concurrent inputs or states, as relevant to the change.
  - **Error handling and failure behavior:** what happens when a dependency, input, or step fails, and whether the failure is visible and recoverable.
  - **Regression risk:** what existing behavior could be affected, and whether existing tests cover it.
  - **Interfaces and contracts:** any externally visible interface (API, CLI flags, file format, schema, config option, event) that changed, and whether its documentation and consumers are updated.
  - **Data and state:** migrations, persisted data, backward compatibility, and rollback or recovery.
  - **Security and privacy basics:** secrets, permissions, sensitive data in logs or output, untrusted input.
  - **Observability and supportability:** logging, error messages, and enough information to diagnose a failure.
  - **Documentation and release notes:** user-facing or operator-facing changes are documented.
  - **Testability:** whether the change can be tested in this repo's environment, and what a QA engineer needs (test data, flags, environments) to verify it manually.
- [ ] Mark each core item as "apply when relevant to the change" so the agent skips items that do not apply instead of forcing findings.
- [ ] `lenses/` (optional, additive): add at most a few short examples to show the pattern, and label them clearly as examples, not requirements. Candidates: a web UI lens (accessibility, loading and error states), a service lens (validation, auth, idempotency), an infrastructure-as-code lens (least privilege, rollback, blast radius). A user can add a lens for any other stack (mobile, game, data pipeline, embedded, ML) by dropping in one file.
- [ ] Each lens opens with the `applies_when` block (`paths` and `touches`, see "Lens selection"), adds only checks the core does not already cover, and never repeats core items.
- [ ] `lenses/README.md`: how to add a lens (the file format, the `applies_when` fields, and the rule that a lens only adds to the core). SKILL.md mentions it in one line.
- [ ] `output-format.md`: report template and the structured findings block (see Phase 0).

### 4. Scripts (deterministic only)

| Script | Purpose |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `changed_interfaces.py` | Best-effort listing of externally visible interfaces touched by a diff (for example HTTP routes, CLI flags, config keys, schema files). Reports "could not tell" instead of guessing                                                  |
| `missing_tests.py`      | Given changed source files, report which have no matching test file changes. Test file patterns are configurable, with sensible defaults across common languages                                                                      |
| `openapi_changed.py`    | Optional. Runs only when the repo contains an OpenAPI/Swagger spec, and reports whether interface changes lack a matching spec change                                                                                                 |
| `suggest_lenses.py`     | Matches the changed-file list against each lens's `applies_when.paths` and prints candidate lenses with the files that matched. Prints an empty list when nothing matches or there is no `lenses/` folder, and never fails the review |

Scripts must degrade gracefully on any project. A script that does not apply to the repo (no spec file, no recognizable test layout) reports "not applicable" and exits cleanly, and SKILL.md tells the agent to continue with the core review.

For each script:

- [ ] Reads a diff from a file or stdin, prints JSON.
- [ ] Handles several common languages and frameworks, and says clearly when it cannot tell or when the repo does not fit its assumptions.
- [ ] Has a `--help` and a documented output schema.
- [ ] Has unit tests with small hand-written diffs, including empty diffs and malformed input.
- [ ] SKILL.md tells the agent to run the script and treat its output as a signal, not a verdict.

### 5. Report format

- [ ] Summary line with overall assessment.
- [ ] Acceptance criteria table: criterion, status (covered, partial, missing, unclear), evidence.
- [ ] Findings grouped by severity, each with file, line when known, explanation, and suggested fix.
- [ ] A "Lenses applied" line naming each lens and why, or "core only".
- [ ] Structured findings block at the end for evals. It also carries a `lenses_applied` list (an extra top-level key, which the current scoring ignores).
- [ ] Keep it short enough that a reviewer reads all of it.

### 6. Fixtures and cases

Each fixture is a small PR (diff, description, ticket). Planted defects are described by QA category, not by stack, and the fixtures are deliberately spread across different kinds of projects so the eval set proves the skill is not tied to any one of them.

| Fixture | Project kind | Planted defect | Expected category |
| --------------------------- | ---------------------- | ------------------------------------------------------------------------- | ------------------------------ |
| `missing-tests`             | Library                | New public function with no test changes                                  | `missing-tests`                |
| `criterion-not-implemented` | Any (ticket-driven)    | Ticket lists 4 criteria, diff implements 3                                | `unmet-acceptance-criterion`   |
| `interface-without-docs`    | CLI tool               | New command flag, help text and README untouched                          | `missing-interface-doc-update` |
| `no-input-validation`       | Web service            | Handler trusts request body                                               | `missing-input-validation`     |
| `unhandled-failure-path`    | Mobile or web app      | Network call with no failure or empty state                               | `missing-error-handling`       |
| `unsafe-data-change`        | Data pipeline          | Schema change with no backfill or rollback path                           | `unsafe-data-change`           |
| `excessive-permissions`     | Infrastructure as code | Policy grants wildcard access                                             | `excessive-permissions`        |
| `untested-edge-case`        | Game or desktop app    | Behavior on empty or maximum input is unhandled and untested              | `missing-edge-case-coverage`   |
| `docs-only`                 | Any                    | Docs-only change, expecting a short review with no invented code findings | none                           |
| `clean`                     | Any                    | Well-formed change with tests and doc updates                             | none                           |

- [ ] Write each fixture to be realistic but minimal.
- [ ] Write one case per fixture, plus a mixed fixture with two defects.
- [ ] Include at least one fixture on an unfamiliar or unusual stack, expecting a core-only review that states the stack was unfamiliar instead of inventing stack conventions.
- [ ] Include at least one case run with an optional lens enabled and the same case run core-only, to confirm the core finds the defect either way.
- [ ] Cover lens selection in the fixtures: a mixed change (for example code plus an infrastructure file) that should select more than one lens, and the docs-only change, which should select none and say "core only". Fixtures supply the output of `suggest_lenses.py` as a file, since scripts are not run in evals.
- [ ] Write 8 to 10 trigger prompts of each kind, including prompts that name different stacks and prompts that name none.

### 7. Runner and structure support for lenses

Lenses need two small changes outside the skill itself.

- [ ] **Per-case lens control in the eval runner.** The runner currently pastes every file under `references/`, lenses included, and the model cannot read files during an eval. Add a per-case option (for example a `lenses:` list naming the lens files to include, with `[]` meaning core only), so the same fixture can run with and without a lens. Update `evals/runner/loader.py` and `prompt.py`, add unit tests, and document the option in `docs/eval-format.md`.
- [ ] **Decide whether cases can assert lens selection.** For example `expect.lenses`, compared with the reported `lenses_applied`. This is the only eval signal for the agent's selection judgment, since the script's own behavior is covered by its unit tests.
- [ ] **Structure tests for lenses**, in `evals/structure.py`:
  - Every file in `references/lenses/` has valid `applies_when` frontmatter (`paths` as a list of globs, and `touches`), and lens names are unique.
  - The orphan-reference rule exempts lens files. They are discovered by `suggest_lenses.py`, not named in SKILL.md, so today's rule would flag every one of them.
  - SKILL.md and `qa-core.md` link to no specific lens file, so removing the `lenses/` folder cannot break them.
  - The stack-term scan (see Risks) skips lens files.

## Acceptance criteria

- Structure and unit tests pass in CI.
- On the eval set, the skill finds each planted defect in a majority of runs and produces no more than the allowed findings on the clean PR.
- SKILL.md is under the line budget, with detail in references.
- A reader can follow the README to run the skill with only the `gh` CLI authenticated, pasting the ticket text in place of Jira access.
- The skill works on every fixture project kind with no lens installed, and SKILL.md and `qa-core.md` contain no stack-specific wording outside example lenses.
- Removing the `lenses/` folder entirely leaves the skill fully functional.
- Every report states which lenses were applied and why, or "core only".

## Risks and notes

- **Drifting back to stack-specific.** It is easy for stack assumptions to creep into SKILL.md or the core checklist. Add a structure test that scans them for stack-specific terms (for example "component", "endpoint", "controller", "Terraform") and fails unless the term appears inside a lens.
- **Lens signals that match everything or nothing.** A lens whose `paths` are too broad loads on every change, and one that is too narrow never loads. Keep globs specific, and check in the fixtures that a lens is not selected for unrelated changes.
- **Generic means shallow.** A project-agnostic checklist can produce vague findings. Each core item should include what evidence to look for in the diff, and the eval set should check that findings point to specific files or lines.
- **Noisy reviews.** The most common failure is too many low-value findings. The clean-PR case and `max_findings` guard against it.
- **Ticket quality.** Real tickets are messy. Add at least one fixture with vague acceptance criteria to check the uncertainty rule.
- **Diff size.** Large diffs exceed what the agent can reason over carefully. Add guidance in SKILL.md for prioritizing files (source over generated, tests next to source).
