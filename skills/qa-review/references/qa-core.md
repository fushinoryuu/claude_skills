# QA Core Checklist

The universal checks, applied to every review whatever the project. It is written without reference to any stack. Stack-specific extras live in optional lenses (see `references/lenses/README.md`) and only ever add to this list.

How to use it:

- Every item is **apply when relevant to the change**. Skip an item that does not apply instead of forcing a finding, and say so when skipping it is not obvious.
- Each item says what evidence to look for. A finding without a file and symbol (or test name) is too vague to act on.
- Every gap states three things: what is missing or wrong, where (file and symbol), and what change or test would close it.
- The sections are grouped by the workflow step in `SKILL.md` that uses them.

## Requirements and implementation (Step 4)

- **Requirements.** Every acceptance criterion is implemented. Behavior beyond the ticket is called out. Unclear requirements are flagged, not assumed. *Evidence:* map each criterion to the file and symbol, or the test, that shows it.
- **Consistency.** When a fix, new field, or new rule is applied to one of several similar places (sibling modules, entities, call sites), it is applied to all of them. *Evidence:* search the siblings and confirm the same change is present in each.
- **Error handling and failure behavior.** What happens when an input, a dependency, or a step fails, and whether the failure is visible and recoverable. *Evidence:* look for new calls to outside systems, parsing, and conversions that have no failure path.
- **Regression risk.** What existing behavior could be affected, and whether existing tests cover it. *Evidence:* shared code that changed, defaults that changed, and callers of anything whose behavior changed.
- **Data and state.** Schema or data migrations, persisted data, backward compatibility, and rollback or recovery. *Evidence:* migrations or format changes without a recovery path, or a stricter rule added without handling data that already exists.
- **Security and privacy basics.** Secrets, permissions, sensitive data in logs or output, untrusted input. *Evidence:* new inputs from outside, new credentials or permissions, new logging.
- **Observability and supportability.** Logging, error messages, and enough information to diagnose a failure. *Evidence:* new failure paths that fail silently or with an unhelpful message.
- **Testability.** Whether the change can be tested in this repo's environment, and what a QA engineer needs (test data, flags, environments) to verify it manually. *Evidence:* behavior that depends on configuration or data the repo does not provide.

## Test coverage (Step 5)

- New and changed behavior has tests at an appropriate level for this project.
- New or changed branches have tests, especially failure and error branches, not only the happy path.
- Tests assert real outcomes, not just that the code ran without throwing.
- Edge cases and inputs, as relevant to the change: empty, maximum, invalid, duplicate, and concurrent inputs or states.

*Evidence:* compare the changed source files with the changed test files, then read the assertions in the tests that exist.

## Higher-level tests (Step 6, `final` mode only)

- Observable behavior that the acceptance criteria describe and lower-level tests cannot fully verify is covered at the project's own higher level (whatever it calls functional, integration, or end-to-end tests), in its designated location and style.
- Test data a test creates is removed afterwards (for example with setup and teardown pairs). Check existing tests touched by the change as well as new ones.
- When a needed test cannot be written now (missing environment, dependency, or credentials), the gap is still recorded with the reason. Step 9 adds a pending stub in the framework's own style so the gap is tracked in source control.
- Only evaluate in this step. Step 9 writes the tests and runs them with the project's test command, and reports the result honestly.

## Interfaces and documentation (Step 7)

- **Interfaces and contracts.** Any externally visible interface that changed (an API, command-line flags, a file format, a schema, a config option, an event) has its documentation updated, and its consumers are accounted for. Breaking changes are called out. *Evidence:* a changed signature, flag, field, or format with no matching change to its documentation.
- **Documentation and release notes.** User-facing and operator-facing changes are documented. When new scripts, config, or environment variables are added, the README and any example configuration are updated to match.
- When the change touches no externally visible interface and no user-facing behavior, report this step as not applicable.
