# Security review for qa-review: design notes

How `qa-review` gets a real security review. This is the plan, not the work. It is written for QARS-29, which only plans. The work is split into follow-up tickets (see "Work breakdown"). Nothing in `skills/` changes in the PR that adds this file.

## The problem

`qa-review` is good at finding unmet acceptance criteria. Its security coverage is thin:

- The core checklist (`skills/qa-review/references/qa-core.md`) has one bullet, "Security and privacy basics".
- The `service` lens checks input validation and authorization, nothing deeper.
- The eval set plants two security defects: `missing-input-validation` and `excessive-permissions`.

The person running the skill has started reviewing a backend project and does not have a security background. They cannot tell what the skill missed, so the skill has to carry more of this knowledge.

## Options considered

| Option                                    | What it is                                                              | Decision                                 |
| ----------------------------------------- | ----------------------------------------------------------------------- | ---------------------------------------- |
| 1. A security step in `SKILL.md`          | A 13th step in the workflow                                             | Rejected                                 |
| 2. A `security` lens, plus a core upgrade | Stack-free checks in the core, backend depth in a lens                  | **Chosen**                               |
| 3. A standalone whole-repo security skill | A skill with no ticket or PR as input, which reads the repo and reports | Later, as its own ticket (Phase 3 style) |

Why not option 1:

- The Phase 1 ground rules say the 12 steps are a stable backbone, and new items go in as sub-items only.
- A new step reaches into the progress list, both Jira templates, the memory format, the report and the evals.
- Security is not a separate activity. It is a way of reading the code in Steps 4 to 7: new inputs, who may call this, what gets logged, what the change depends on.

Why not option 3 now:

- It has a different input (no ticket, no PR) and a different output (no Jira comment).
- `qa-review` skips code the PR did not touch on purpose. A whole-repo review is another job.
- Claude Code already has a built-in `/security-review` for the pending changes on a branch. Try it next to the lens, so we know what we are adding.

## Why a lens and a core upgrade, and not only a lens

A lens is optional. The agent can decide not to load it, and the path match for security is fuzzy because security does not live in one folder. So:

- The **core upgrade** makes sure security is considered on every review, on any kind of project. It stays stack-free.
- The **lens** adds the depth that only makes sense for a server-side project: injection, token handling, tenant scoping, CORS, and so on.

## Core upgrade (spec)

The one bullet in Step 4 becomes a short section, "Security and privacy". Each item says when it applies and what evidence to look for, like the other core items. The wording must not use the stack words that `evals/structure.py` bans outside the lenses folder (`endpoint`, `controller`, `sql`, `docker`, `html`, `openapi`, `backend`, and the others in `STACK_TERMS`). The structure tests check this.

| Item                                 | What to check                                                                                                                            | Evidence to look for                                                                                                                                                            |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Untrusted input                      | Data from outside the code (people, files, other systems, settings) is checked, and is never joined into a command, query, path or page. | A new input that reaches a command, query, file path or output with no check or encoding.                                                                                       |
| Who is calling, and may they do this | A new or changed operation checks the caller's identity and that they may act on this specific item, not only that they are signed in.   | A new operation with no permission check. An item fetched by id with no owner check. A check done only on the client side.                                                      |
| Secrets and credentials              | No secret in code, committed settings, fixtures or logs. New ones come from the project's secret store.                                  | A literal key, token, password or connection string in the diff. A committed settings file with real values. The report names the file and symbol and never repeats the secret. |
| Sensitive data                       | Personal, financial and sign-in data is not logged, returned beyond need, or stored and sent unprotected.                                | A new log line, error message or response field that carries it.                                                                                                                |
| Least privilege and exposure         | Permissions, roles, network access and defaults grant only what the change needs. Nothing new is public by default.                      | Wildcard permissions, public access, checks switched off, debug settings left on.                                                                                               |
| Dependencies and build               | New, upgraded or removed dependencies and build or pipeline steps are needed, from a known source, and pinned.                           | A manifest change (not the lockfile, see decision D3) that adds an unpinned or unknown package, or a pipeline step that runs downloaded code.                                   |
| Failing open                         | When a security check itself fails, the result is "deny". Error messages do not leak internals.                                          | A catch-all that carries on after a failed permission or validation check.                                                                                                      |

Two more small changes in the core:

- **Step 5 (test coverage):** one new bullet. Security-relevant behavior has tests for the denied path: a caller who is not allowed, hostile or malformed input, a missing or expired credential. _Evidence:_ the happy-path test exists and no test shows a refusal.
- **Severity guide** in `references/output-format.md`: one added line. A gap that lets someone read or change what they should not is `high`. Today `high` covers "access is too wide", which is close but not enough.

## The `security` lens (spec)

File: `skills/qa-review/references/lenses/security.md`. It adds checks on top of the core and never repeats a core item.

Proposed frontmatter:

```yaml
---
name: security
description: Extra security checks for server-side code, authentication, dependencies and build or pipeline files.
applies_when:
  paths:
    - "**/auth/**"
    - "**/authn/**"
    - "**/authz/**"
    - "**/security/**"
    - "**/middleware/**"
    - "**/routes/**"
    - "**/handlers/**"
    - "**/controllers/**"
    - "**/iam/**"
    - "**/.github/workflows/**"
    - "**/Dockerfile*"
    - "**/*.tf"
    - "**/package.json"
    - "**/pyproject.toml"
    - "**/requirements*.txt"
    - "**/go.mod"
    - "**/pom.xml"
  touches: "who may do what, handling of untrusted input or secrets, dependencies, or the permissions of a service or pipeline"
---
```

The path list is a first pass. `suggest_lenses.py` treats it as a signal, and the agent judges from `touches` when no path matches. The follow-up ticket checks the globs against the script's own rules (`*` stays in one folder, `**` crosses folders).

Checks, under the same step names `SKILL.md` uses:

**Step 4: Requirements and implementation**

- **Injection and unsafe interpretation.** A query, command, template or file path is built by joining input. Look for parameterized queries and allow-lists. Also deserialization of untrusted data, a server fetching a URL a caller supplied, a redirect to a caller-supplied address, and path traversal in file upload or download.
- **Authentication details.** Tokens are checked for signature, expiry and audience. Passwords use a slow, salted hash. No home-made cryptography. Random values for tokens come from a secure generator. Tokens and passwords never appear in logs.
- **Authorization depth.** Access to one item is checked per item (a caller cannot read another caller's record by changing an id). Admin operations are checked per operation. In a multi-tenant service, every data access is scoped to the tenant. A request body is not bound whole onto a record that has privileged fields.
- **Web exposure.** Cross-origin settings are not wildcard when credentials are sent. Cookies carry the protective flags. State-changing requests that use cookie sign-in have forgery protection. Sign-in and other costly operations have a rate limit. Stack traces and debug pages are off outside local use.
- **Pipeline and infrastructure files.** A workflow has the least permissions it needs, does not run code from an untrusted branch with write access or secrets, and does not print secrets. Third-party actions are pinned. A container does not run as root without a reason.
- **Dependencies.** A new package has a clear reason, a pinned version and a known maintainer. Ask for the project's own audit result when it has one. A dependency pulled from a git URL or `latest` is a gap.
- **Files and data.** Uploads have a size limit and a type check. Personal data has a retention rule or a note that there is none.

**Step 5: Test coverage**

- A test where the caller is not allowed. A test where an item belongs to someone else. A test with hostile input. A test with an expired or missing token. The test asserts that the response does not leak details.

**Step 6: Higher-level tests (`final` mode only)**

- The permission matrix (each role against each operation) is covered at the project's higher test level. Users and tokens a test creates are removed afterwards.

**Step 7: Interfaces and documentation**

- The documentation states how each new or changed route is protected (the spec's security scheme, or the README). The 401 and 403 responses are documented. A new setting or variable that holds a secret says how to supply it. A change that makes sign-in stricter is called out as breaking.

### How the lens avoids repeating anything

- Nothing in the core table above is restated. The lens says "deeper" and gives the concrete failure.
- `service` has two items that duplicate the core upgrade: "Input validation" and "Authorization". See decision D1.
- The existing eval pair `no-input-validation-01` (with the `service` lens) and `-02` (core only) both expect the same finding. That already shows the core catches it, so the lens does not need to carry it.
- Both lenses can match one change (`routes/`, `handlers/`). That is allowed. If both raise the same gap, the existing rule "merge related gaps" applies.

### Project conventions come first

The skill must discover how the project does things (Step 3). The lens says: before flagging a missing check, look for the project's own middleware, validation library or policy layer. A check done there is not a gap.

## Eval plan

Rules from `docs/eval-format.md` apply: synthetic data only, one planted defect per fixture, scored by category and file, at least one clean case.

### New categories

Added to `evals/qa-review/categories.yaml` and to the table in `references/output-format.md`. The structure tests fail if the two lists differ.

| Slug                          | Use it when                                                                         |
| ----------------------------- | ----------------------------------------------------------------------------------- |
| `missing-authorization-check` | A caller can do or read something they may not, or the check covers only part of it |
| `weak-authentication`         | Tokens, sessions or passwords are checked or stored in a weak way                   |
| `injection-risk`              | Input is joined into a query, command, path or template                             |
| `hardcoded-secret`            | A key, token, password or connection string is in the code or committed settings    |
| `sensitive-data-exposure`     | Personal or sign-in data is logged, returned or stored without need or protection   |
| `insecure-configuration`      | A setting weakens security: wildcard cross-origin access, checks off, debug on      |
| `risky-dependency-change`     | A dependency or build step is unpinned, unknown or runs unreviewed code             |

`excessive-permissions` and `missing-input-validation` stay as they are. A pipeline workflow with too many permissions is `excessive-permissions`.

### Fixtures and cases

Each fixture is a small PR (`pr.diff`, `pr-description.md`, `ticket.md`, plus `suggest_lenses.json` where lens choice matters).

| Fixture                          | Planted defect                                                   | Cases                                      |
| -------------------------------- | ---------------------------------------------------------------- | ------------------------------------------ |
| `security-missing-authorization` | A record is returned to any signed-in user, with no owner check  | core only, and with the lens               |
| `security-injection-risk`        | A search query is built from a request parameter                 | core only, and with the lens               |
| `security-hardcoded-secret`      | An API key literal in a settings module                          | core only                                  |
| `security-sensitive-data`        | The full request body, with a password, is logged                | core only                                  |
| `security-weak-authentication`   | A token is accepted without checking its signature               | with the lens                              |
| `security-insecure-config`       | Wildcard cross-origin access with credentials, and debug left on | with the lens                              |
| `security-risky-dependency`      | A package added unpinned, from a git URL                         | with the lens                              |
| `security-clean`                 | The safe version of the same kinds of change                     | core only, and with the lens (tag `clean`) |
| `security-tricky`                | Looks risky, is safe (see below)                                 | with the lens (tag `tricky`)               |

That is 9 fixtures and 12 cases. The tricky fixture builds a query with an f-string, but only from a hard-coded allow-list of table names, and a test file holds a fake password. It uses `must_not_flag: [injection-risk, hardcoded-secret]`.

Whether the core alone catches the lens-only defects is a question for the eval, not a rule. The cases for them run with the lens, and the core-only runs of the first four show how much the core upgrade already covers.

Expected values: `max_findings` 3 or 4 for defect cases, 0 or 1 for clean, 1 for tricky. `expect.lenses` is `[security]` or `[security, service]` where the case sets it, tagged `lenses`. Word limits follow the template (750 for `initial`).

### The risk in adding a lens

Only one existing case sets `lenses:`. The other 14 load every lens by default, so a new `security` lens changes their prompt. The clean cases are the canary: they allow 0 to 2 findings, and a lens that reports too much will fail them. Plan for it:

- Do not pin the 14 cases to the old lenses. A full re-run is the regression check the Phase 2 exit checklist already asks for.
- If clean cases get noisy, tighten the lens text. Do not raise the limits.
- The core upgrade also makes the always-loaded prompt a little longer. Keep each item to one or two lines.

Unit tests do not depend on the exact set of lenses (`test_suggest_lenses.py` checks that `service` and `api-spec` are present, not that they are the only ones).

### Cases that require an exact lens list

`expect.lenses` is scored as an exact match: a run passes only if the reported lenses equal the list. Three older cases are affected, because the proposed `security` globs match files their fixtures change (`**/handlers/**` and `**/routes/**`):

| Case                     | Expects today         | Fixture file the globs match          | Expects after the lens exists   |
| ------------------------ | --------------------- | ------------------------------------- | ------------------------------- |
| `no-input-validation-01` | `[service]`           | `src/orders/handlers/create_order.py` | `[service, security]`           |
| `mixed-lens-change-01`   | `[service, api-spec]` | `src/shop/routes/orders.py`           | `[service, api-spec, security]` |
| `docs-only-01`           | `[]`                  | none (docs only)                      | `[]`, unchanged                 |

Each of the three fixtures also holds a `suggest_lenses.json`, the saved output of `suggest_lenses.py`. It was made before `security` existed, so it no longer matches what the real script prints. `docs/eval-format.md` says this file must be the script's real output on the fixture's inputs. The fix:

- Regenerate `suggest_lenses.json` for `no-input-validation`, `mixed-lens-change` and `docs-only` by running the script, once the `security` lens file exists. Do not edit them by hand.
- Change the two expectations in the table. Leave `docs-only-01` at `[]`, since no `security` path matches a docs-only change. Its regenerated file only gains `security` in the unmatched list.
- Do not pin these cases to the old lenses with `lenses:`. That would hide the change in lens choice that the cases exist to check.
- The expectations depend on the final path globs. QARS-31 settles the globs (decision D4), so this work happens in QARS-32 after it. If QARS-31 narrows the globs so that `handlers/` and `routes/` no longer match, the two expectations stay as they are today, and only the regenerated files need review.
- "No regression on the 15 older cases" in QARS-32 means the findings, the false-positive rate and the comment length. The three lens lists above are an intended change, and the PR description names them.
- The older cases can also fail on findings, because `security` is now loaded for them. The full re-run shows that, and the lens text is tightened if it does.

### Fixture values and the secret scanner

A TruffleHog scan runs on every push (`.github/workflows/secret-scanner.yaml`). The fake secret in `security-hardcoded-secret` and the fake password in `security-tricky` must not look like a real key format from a known provider. Use plain made-up strings. Push the fixtures once on a branch and read the scanner result before the PR is opened. The PR checklist item "no secrets" stays unticked until then.

### Cost

Token counts come from the 2026-11-13 baseline in `docs/baseline-eval.md` (45 runs per model). Prices come from the Claude API skill's cached table (dated 2026-11-03): Sonnet 5.5 $2 in and $10 out per million tokens with cache reads at $0.10, Haiku 5.5 $0.10 and $0.50, Opus 5.5 $4 and $20 with cache reads at $0.20. Cache writes are assumed at 1.25 times the input price. Check the live prices before a run. These are estimates, not quotes.

| Run                                             | Runs | Sonnet 5.5 | Haiku 5.5  | Opus 5.5   |
| ----------------------------------------------- | ---- | ---------- | ---------- | ---------- |
| Baseline today (15 cases, 3 runs each)          | 45   | about $2.5 | about $0.2 | about $4.9 |
| New security cases only (12 cases, 3 runs each) | 36   | about $2.0 | about $0.1 | about $3.9 |
| Full set after the work (27 cases, 3 runs each) | 81   | about $4.4 | about $0.3 | about $8.8 |

Output tokens are about 85% of the Sonnet cost, so a longer lens costs little. A three-model refresh of the baseline would be about $13.5.

Order of runs, cheapest first: `uv run poe eval --skill qa-review --dry-run` (free), then the security cases on Sonnet only (about $2), then the full set on Sonnet (about $4.4). The three-model refresh is the user's call.

## Limits

- A model review reads the diff and applies patterns. It can miss things, and "no security findings" does not mean "secure".
- It sees only the changed lines and the files it fetches. Whole-repo problems are not covered (that is option 3).
- It does not run the code, probe the service or scan dependencies for known vulnerabilities.
- It does not replace these, which should run in CI and catch what a reader cannot:
  - a dependency audit (and Dependabot, QARS-27),
  - a secret scanner (this repo already runs TruffleHog),
  - a static analyzer such as Semgrep,
  - a penetration test or a security review by a person for anything sensitive.
- A finding in a Jira comment is visible to everyone who can see the ticket. A secret is never quoted in the comment or the report.
- The first reviews will show false alarms and misses. The lens is expected to change after real reviews, as the backend lenses will (QARS-23).

## Ground rules check

The plan keeps the rules in `SKILL.md` and `docs/roadmap-phases/phase-1-qa-review-skill.md`:

- **Project-agnostic core.** The core upgrade uses no stack words, and each item says to skip it when the project has no such surface. The structure tests enforce the banned words.
- **Stack words only in lenses.** Injection, token and cross-origin detail live in `lenses/security.md`.
- **Twelve steps unchanged.** `SKILL.md` is not edited, so it stays at 305 of 500 lines. The skill's checks sit in the core and lens files.
- **Find first, fix later.** The lens only records gaps. `final` mode still edits only tests and documentation.
- **No production code, no commits, no ticket status changes.** Unchanged.
- **A lens is never required.** The core upgrade means the review still covers security when the lens is skipped.

## Work breakdown

Three tickets, filed on 2026-11-17 as tasks that relate to QARS-29. The Phase 2 doc and `docs/ROADMAP.md` name them.

| Ticket  | Title                                 | Work                                                                                                                                                                                                                                                                                                                                                         | Size   |
| ------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------ |
| QARS-30 | Core security upgrade                 | Rewrite the core security section and add the Step 5 bullet and the severity line. Move the duplicated `service` items (decision D1). Dry-run, then run the validation and permission cases and the clean cases.                                                                                                                                             | Small  |
| QARS-31 | `security` lens and categories        | Write `lenses/security.md`. Add the seven categories to `categories.yaml` and `output-format.md`. Check the path globs with `suggest_lenses.py` and add a unit test for them.                                                                                                                                                                                | Medium |
| QARS-32 | Security fixtures, cases and baseline | Nine fixtures and twelve cases. Scan them for secrets. Regenerate the `suggest_lenses.json` of three older fixtures and update two lens expectations (see "Cases that require an exact lens list"), after QARS-31 settles the globs. Run Sonnet on the new cases, then the full set. Record the result in `docs/baseline-eval.md` or a short note beside it. | Medium |

Order: QARS-30, then QARS-31, then QARS-32. QARS-30 can ship alone. The other two need its wording, and QARS-32 also needs the final path globs from QARS-31. Because QARS-32 is where the evals cost money, the person who owns the budget runs the full eval.

Later, as its own ticket and not part of QARS-29: the standalone whole-repo security skill.

## Decisions

All four were agreed on 2026-11-17, with the recommendations below. They are tracked in the follow-up tickets.

1. **D1: the `service` lens.** Agreed: move "Input validation" and "Authorization" out of `service`, since the core upgrade now covers them and the eval pair shows the core already catches validation. `service` keeps idempotency and migrations. The alternative is to leave `service` alone and accept some double reporting.
2. **D2: category count.** Agreed: the seven above, so a case can say exactly what it expects. The alternative is fewer, coarser categories (for example one for authentication and authorization), which is simpler but scores less precisely.
3. **D3: dependency checks and lockfiles.** `SKILL.md` tells the agent to skip lockfile diffs. Agreed: check the manifest only (the file that names the dependency) and keep that rule as it is. The alternative is a one-line exception in "What to skip", which is a `SKILL.md` edit.
4. **D4: path globs.** The list above is broad on purpose. If it matches too often, the lens loads on changes with no security surface. Agreed: measure it in QARS-31 and narrow the list if needed.

## Not in this plan

- Writing the core upgrade, the lens, the fixtures or the cases.
- Running any eval.
- The standalone whole-repo security skill.
- Installing or configuring scanners.
