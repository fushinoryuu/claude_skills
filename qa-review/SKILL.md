---
name: qa-review
description: Run a structured QA review of a Jira ticket and its pull request(s), checking acceptance criteria coverage, test coverage and API spec accuracy, then post the findings to the Jira ticket. Use when the user invokes /qa-review.
argument-hint: <initial|final> <JIRA-TICKET> <PR#> [PR#2 PR#3 ...]
disable-model-invocation: true
---

# QA Review

Formal QA verification step for a Jira ticket and one or more PRs. The Jira ticket is the source of truth for the state of the work, so all findings are posted there.

## Arguments

`$ARGUMENTS` = `<mode> <JIRA-TICKET> <PR#> [PR#2 ...]`

- `mode`: `initial` or `final`
- `JIRA-TICKET`: Jira issue key, e.g. `ABC-123`
- `PR#`: one or more GitHub PR numbers in the current repository

If the mode is not `initial` or `final`, the ticket key is missing, or no PR numbers are given, stop and show the usage line. Do not guess.

## Ground rules

- Tools: Jira through the Atlassian MCP server, GitHub through the `gh` CLI. If either is unavailable or unauthenticated, stop and tell the user. Do not work around it.
- Never run `git commit`, `git push`, `git add`, or any other command that records or publishes changes. The engineer controls commits. Leave edits in the working tree and list the files changed in your summary.
- Never modify production code. Only test files, test fixtures, and API spec/contract files may be edited, and only in `final` mode.
- Do not create files in the repo other than tests/specs required by the review. Review state lives in Claude Code memory, not in the repo.
- Post comments to the Jira ticket only. Do not comment on the PRs.
- Do not transition the ticket's status unless the user asks.
- Discover the project's conventions instead of assuming them (see "Discover the project" below). This skill must work for back-end, front-end, infra, and library projects.

## Workflow

### Step 1: Load prior review memory

Look in Claude Code memory for a project memory named `qa-review-<JIRA-TICKET>` (lowercase the key). If it exists, read it: it holds the gaps and verdict from earlier reviews of this ticket.

- `initial` with prior memory: this is a repeat review. Say so, and use the memory only for context.
- `final` with no prior memory: warn that there is no initial review to cross-reference, then continue treating every gap as new.

### Step 2: Gather inputs (in parallel)

Make these calls in the same turn:

- Jira: fetch the ticket (summary, description, acceptance criteria, comments, linked issues).
- GitHub: for each PR, `gh pr view <PR#> --json title,body,baseRefName,headRefName,files,state` and `gh pr diff <PR#>`.

If the working tree is not on a PR's head branch and `final` mode needs to edit files, tell the user which branch to check out instead of switching branches yourself.

### Step 3: Discover the project

Before judging anything, work out how this project does things. Read what exists; do not assume:

- Test framework, test file locations and naming (look at config files and neighbouring tests).
- How tests are split: unit vs. functional/integration/e2e/component tests, and where each lives.
- Available scripts for tests, lint, type-check, and spec validation (`package.json`, `Makefile`, CI config, etc.).
- Whether the project has an API contract (OpenAPI/Swagger, GraphQL schema, protobuf, etc.). If not, the API spec check is skipped and reported as "not applicable".
- Project docs that state testing expectations (`CLAUDE.md`, `CONTRIBUTING.md`, `README`).

The checks below describe intent. Map them onto whatever the project actually uses. For example, "handlers" means controllers in one codebase and components or hooks in another.

### Step 4: Acceptance criteria coverage (both modes)

List each acceptance criterion from the ticket. For each, decide whether the PR(s) implement it and whether a test exercises it. Mark each `Covered`, `Partial`, or `Missing`, citing the file and line or test name that shows it. If the ticket has no explicit acceptance criteria, derive them from the description, say so, and ask the user to confirm them before posting.

### Step 5: Unit test coverage (both modes)

Check the changed code against these expectations:

- New or modified core logic (factories, utilities, helpers, sub-resource handlers, reducers, hooks, modules) has unit tests.
- New or modified branches in existing code have tests, especially error-handling branches.
- New data-access actions/blocks have a happy-path test, a unique-constraint-violation test, and a test that unexpected errors are rethrown. Skip this bullet if the project has no database layer.

Every gap gets: what is untested, where (file and symbol), and what test would close it.

### Step 6: Functional/integration tests (`final` only)

In `initial` mode skip this step and say it was skipped.

In `final` mode, evaluate whether observable behaviour is covered at the integration level: response shape, status codes, filtering, pagination, rendered output, user flows, or any behaviour in the AC that unit tests cannot fully verify. Use the project's own designated directory and style for these tests.

- Write the missing tests.
- If a test cannot be written right now (missing environment, dependency, credentials), add a `.todo` stub (or the framework's equivalent) so the gap is tracked in source control, and record why in the review comment.
- Every `beforeAll`/setup that creates test data must have a matching `afterAll`/teardown that cleans it up. Check existing tests touched by the PR as well as new ones.
- Run the new tests with the project's test command and report the result honestly.

### Step 7: API spec check (both modes)

Skip as "not applicable" if Step 3 found no API contract.

- Spec source files for the endpoints or domains touched by the PR are updated where necessary.
- New query params, request body fields, and response codes are documented.
- If the project has a spec validation script (e.g. spectral), run it. It must finish with 0 errors.

In `initial` mode, report gaps only. In `final` mode, fix the spec files where needed and re-run validation.

### Step 8: Previous gaps (`final` only)

Using the memory from Step 1, mark every gap from the initial review as `Closed`, `Still open`, or `Closed differently` (with a note). Then list any new gaps found in this review.

### Step 9: Fix what can be fixed (`final` only)

Fix remaining unit-test and spec gaps in this session where possible, following the ground rules (no production code changes, no commits). Run the relevant tests and validation afterwards. Anything that needs a production code change goes into the comment as a gap for dev.

### Step 10: Post the Jira comment

Read the template for the mode and compose the comment from it:

- `initial`: [templates/initial-comment.md](templates/initial-comment.md)
- `final`: [templates/final-comment.md](templates/final-comment.md)

Post only the text under the "Template" heading, and follow the rules section of the template. Fill in every `{{ placeholder }}`, keep only the applicable verdict and the applicable branch of each conditional (delete the `{{ ... }}` marker lines), and remove no sections (write "None" or "Not applicable" instead). Keep it scannable: facts and file names, no padding.

The comment must look like a normal comment from a person. Post it as plain text exactly as the template formats it. Never wrap it in a code fence, code block, `{code}`, `{noformat}` or panel, since Jira renders those as a grey box. Post it to the ticket with the Atlassian MCP, then show the user the same text in the session.

- `initial`: post the comment and stop. The ticket goes back to dev for the listed gaps.
- `final`: post the comment. The verdict is **Ready to mark Done** (no open gaps) or **Gaps remain** (list them).

Do not transition the ticket yourself. If the verdict is "Ready to mark Done" or a status change would clearly be next, offer it and wait for the user to say yes.

### Step 11: Save memory

Save or update a Claude Code project memory named `qa-review-<JIRA-TICKET>` containing:

- The PR numbers reviewed.
- The date and mode of each review.
- The full list of gaps, each with an id, description and status.
- The verdict.

Follow the memory file format from the system prompt (frontmatter plus body). Update the existing memory if there is one rather than creating a second.

### Step 12: Report to the user

End with a short summary: verdict, number of gaps by status, files modified in the working tree (`final` only, uncommitted), commands run with pass/fail, and a link to the posted comment.
