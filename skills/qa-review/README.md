# QA Review Skill

Runs a structured QA review session for a Jira ticket + one or more PRs. This could serve as the formal QA verification step for a given team/project: when all gaps are resolved and you are satisfied, mark the ticket Done.

The skill is project-agnostic. It applies to any code or feature a QA engineer would review, whatever the stack. A universal core checklist always applies, and optional lenses add stack-specific checks on top.

## Initial setup

This skill assumes that you have the following tools already set up and fully authenticated:

- Atlassian MCP with write access to post comments
- GitHub CLI (`gh`)
- Set effort level to `high` before running skill

## Review modes

There are two modes, used at different points in the ticket lifecycle:

| Mode      | When to use                              | Functional/Integration tests | On gaps found                                                     |
| --------- | ---------------------------------------- | ---------------------------- | ----------------------------------------------------------------- |
| `initial` | First time the ticket reaches QA         | Skipped                      | Report all gaps, send back to dev                                 |
| `final`   | After dev has addressed initial feedback | Evaluated and implemented    | Fix what can be fixed in session without touching production code |

## Usage

```
/qa-review <MODE> <JIRA-TICKET> <PR#> [PR#2 PR#3 ...]
```

**Examples:**

```
/qa-review initial ABC-123 456
/qa-review final ABC-123 456
/qa-review final ABC-123 456 789
```

## What each mode does

**`initial` review:**

1. Load any prior review memory for this ticket if it exists
2. Fetch the Jira ticket, its linked tickets, and the PR diffs
3. Understand the change and select lenses
4. Check acceptance criteria coverage and the implementation
5. Identify test coverage gaps (reports only - does not fix)
6. _(Functional/Integration tests skipped)_
7. Check interfaces and documentation (reports only - does not fix)
8. Sanity-check each gap against the current main branch
9. Post an initial review comment to the Jira ticket and stop

**`final` review:**

1. Load any prior review memory for this ticket if it exists - cross-references gaps from the initial review
2. Fetch the Jira ticket, its linked tickets, and the PR diffs
3. Understand the change and select lenses
4. Check acceptance criteria coverage and the implementation; verify initial review gaps are closed and identify any new gaps
5. Check test coverage
6. Evaluate and implement functional/integration tests
7. Check interfaces and documentation; fix if needed
8. Sanity-check each gap against the current main branch
9. Fix test and documentation gaps in session where possible
10. Post a final review comment to the Jira ticket. If gaps remain for dev, the comment is posted as another initial-style review instead.

## What it checks

### The core checklist

[references/qa-core.md](references/qa-core.md) applies to every review. Each item is applied only when it is relevant to the change.

**Requirements and implementation**

- Every acceptance criterion is implemented, and unclear requirements are flagged instead of assumed.
- Fixes and new rules are applied consistently across similar places.
- Failure behavior, regression risk, data and state, security basics, observability and testability.

**Test coverage**

- New and changed behavior has tests at an appropriate level, including failure paths and edge cases.
- Tests assert real outcomes.

**Higher-level tests** _(final mode only)_

- Behavior the acceptance criteria describe, which lower-level tests cannot fully verify, is covered in the project's designated test location.
- If for some reason a functional/integration test can't be created at this moment, a `.todo` stub is added to keep track of missing tests in source control.
- Test data created by a test is cleaned up afterwards.

**Interfaces and documentation**

- A changed externally visible interface (an API, command-line flags, a file format, a schema, a config option) has its documentation updated.
- User-facing and operator-facing changes are documented.

### Lenses

A lens is an optional file of extra checks for one kind of change. The review is complete without any lens, and a lens only ever adds checks the core does not already cover.

Each lens opens with an `applies_when` block that says which changed files, or which kind of change, it is for. The skill reads only the lenses that fit the change, and the comment lists them on its `Lenses:` line (or says "core only"). You can also name a lens when you run the skill, or ask for the core only.

The lenses included in this folder are examples:

| Lens                                    | Adds checks for                                                                                      |
| --------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| [service](references/lenses/service.md) | Server-side request handling, data access, and migrations (validation, authorization, idempotency)   |
| [api-spec](references/lenses/api-spec.md) | Projects that document an HTTP API in an OpenAPI/Swagger spec (spec updated, new surface documented) |

To add a lens for your own stack, see [references/lenses/README.md](references/lenses/README.md).
