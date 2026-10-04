# QA Review Skill

Runs a structured QA review session for a Jira ticket + one or more PRs. This could serve as the formal QA verification step for a given team/project: when all gaps are revolved and you are satisfied, mark the ticket Done.

### Review modes
There are two modes, used at different points in the ticket lifecycle:

| Mode      | When to use                              | Functional/Integration tests | On gaps found                                                     |
| --------- | ---------------------------------------- | ---------------------------- | ----------------------------------------------------------------- |
| `initial` | First time the ticket reaches QA         | Skipped                      | Report all gaps, send back to dev                                 |
| `final`   | After dev has addressed initial feedback | Evaluated and implemented    | Fix what can be fixed in session without touching production code |

### Usage

```
/qa-review <mode> <JIRA-TICKET> <PR#> [PR#2 PR#3 ...]
```

**Examples:***
```
/qa-review initial ABC-123 456
/qa-review final ABC-123 456
/qa-review final ABC-123 456 789
```

### What each mode does

**`initial` review:**

1. Load any prior review memory for this ticket if it exists
2. Fetch the Jira ticket and all PR diffs in parallel
3. Check acceptance criteria coverage
4. Identify unit test gaps (reports only - does not fix)
5. _(Functional/Integration tests skipped)_
6. Identify OpenAPI spec gaps (reports only - does not fix)
7. Post an initial review comment and stop

**`final` review:**

1. Load any prior review memory for this ticket if it exists - cross-references gaps from the initial review
2. Fetch the Jira ticket and all PR diffs in parallel
3. Check acceptance criteria coverage
4. Verify initial review gaps are closed; identify any new gaps
5. Evaluate and implement functiona/integration tests
6. Verify OpenAPI spec; fix if needed
7. Fix unit test and spec gaps in session where possible
8. Post a final review comment

### what it checks

- New or modified core logic (factories, utilities, sub-resource handlers) has unit test coverage.
- New or modified branches in existing handlers have test coverage (eg. error handling branches).
- New db actions/blocks have happy-path + unique-violation + rethrow tests.

**Functional/Integration tests** _(final mode only)_

- Observable API behavior is covered in designated test directory. This includes response shape, status codes, filtering, pagination, and any other behavior described in AV that cannot be fully verified by unit tests.
- If for some reason a functional/integration tests can't be created at this moment, a `.todo` stub is added to keep track of missing tests in source control.
- Every `beforeAll` that creates test data has matching `afterAll` that cleans it up.

**OpenAPI spec**

- Source files edited for endpoints/domains affected by the PR are checked for necessary updates.
- New query params, request body fields, and response codes are documented.
- If project contains script for validating OpenAPI spec changes (e.g. spectral is used to validate spec files are correct), it should pass with 0 errors.

