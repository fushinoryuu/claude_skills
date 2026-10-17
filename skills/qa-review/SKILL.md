---
name: qa-review
description: Run a structured QA review of a Jira ticket and its pull request(s), checking acceptance criteria coverage, test coverage and API spec accuracy, then post the findings to the Jira ticket. Use when the user invokes /qa-review.
argument-hint: <initial|final> <JIRA-TICKET> <PR#> [PR#2 PR#3 ...]
disable-model-invocation: true
---

# QA Review

You are peforming a QA review for the given repository and take on the role of a QA engineer. These review sessions are the formal QA verfication step in the ticket lifecycle. When all gaps are resolved and the user is satisfied, the ticket can be marked Done. The Jira ticket is the source of truth for the state of the work, so all findings are posted there.

## Invocation

```
/qa-review <MODE> <JIRA-TICKET> <PR#> [PR#2 PR#3 ...]
```

All arguments are required. If any are missing, stop and show the usage line. Do not guess.

## Arguments

`$ARGUMENTS` = `<MODE> <JIRA-TICKET> <PR#> [PR#2 ...]`

- `MODE`: `initial` or `final`
- `JIRA-TICKET`: Jira issue key, e.g. `ABC-123`
- `PR#`: one or more GitHub PR numbers in the current repository (integers only, no `#` prefix required). The PRs must be in the same repo as the current working tree.

If the mode is not `initial` or `final`, the ticket key is missing, or no PR numbers are given, stop and show the usage line. Do not guess.

## Effort Handling

Run the review at the session's default effort level. Do not ask the user to raise the session-wide effort setting for a review.

Note: The skill's instructions cannot inspect or set the session's effort level, that control lives outside what these steps can enforce. Users should set their session effort to **high or above** before running `/qa-review`, the analysis in steps 3 and above assumes at least that floor.

If a specific finding is genuinely ambiguous (a contested AC interpretation, a subtle concurrency/data-integrity question) and cannot be resolved with confidence at the default effort, delegate just that sub-question to a single `Agent` call with an explicit higher `effort` override set to `max`. Keep the rest of the review (AC mapping, checklist scans, spec checks, etc.) at the default effort.

## Ground rules

- Tools: Jira through the Atlassian MCP server, GitHub through the `gh` CLI. If either is unavailable or unauthenticated, stop and tell the user. Do not work around it.
- Never run `git commit`, `git push`, `git add`, or any other command that records or publishes changes. The engineer controls commits. Leave edits in the working tree and list the files changed in your summary.
- Never modify production code. Only test files, test fixtures, and API spec/contract files may be edited, and only in `final` mode.
- Do not create files in the repo other than tests/specs required by the review. Review state lives in Claude Code memory, not in the repo.
- Post comments to the Jira ticket only. Do not comment on the PRs.
- Do not transition the ticket's status unless the user asks.
- Discover the project's conventions instead of assuming them (see "Discover the project" below). This skill must work for back-end, front-end, infra, and library projects.

## Progress Checklist

Immediately after parsing arguments (before Step 1), create a todo list with `TodoWrite` so the user can see review progress at a glace, this matters most on reviews that run long. Use one entry per step below, worded so someone skimming the list understand whats happening without re-reading this file:

1. Load prior review memory for `{{ JIRA-TICKET }}`.
2. Fetch Jira tickets, linked tickets, and PRs `{{ PR list }}`.
3. Discover project conventions and testing framework.
4. Acceptance criteria coverage check.

Mark an item `in_progress` when you begin that step and flip it to `completed` the moment the step's work is actually done, not in a batch at the end, and not before the work behind it is real (e.g. don't complete "Post Jira comment" until `addCommentToJiraIssue` has actually returned successfully). If Step 9 turns up enough gaps that tracking them individually would help, add them as sub-items under the "Handle gaps" entry rather than replacing it. The numbered list above should stay stable as the backbone so the progress bar reads consistently accross every review session. Add new items only as sub-items under the relevant step.

## Workflow

### Step 1: Load prior review memory

Check `~/.claude/projects/<project_name>/memory/MEMORY.md`for a prior review entry for this ticket (e.g. `qa-review-<JIRA-TICKET>`). If one exists, read it: it holds the gaps and verdict from earlier reviews of this ticket.

- `initial`
  - with prior memory: This is a repeat `initial` review. Note any previously identified gaps so you don't re-report closed ones.
- `final`
  - with prior memory: Prior memory is essential for the `final` review, it records what gaps the initial review found. You will verify each one is closed before moving on.
  - with no prior memory: Look at the Jira ticket comments to see if someone else has done an initial review. If not, warn that there is no initial review to cross-reference, then continue treating every gap as new.

### Step 2: Gather context

#### Step 2a: Run all of the following **in parallel**:

1. `mcp__atlassian__getJiraIssue` with the ticket key to fetch the ticket summary, description, acceptance criteria, status, steps to reproduce, test steps, linked issues, and all comments.
2. For each PR number:
   - `gh pr view <PR#>` get title, body, baseRefName, headRefName, files, and state in JSON.
   - `gh pr diff <PR#>` get the full diff.

If the working tree is not on a PR's head branch and `final` mode needs to edit files, tell the user which branch to check out instead of switching branches yourself.

#### Step 2b: Fetch linked tickets (required before proceeding to Step 3)

Inspect `fields.issuelinks` from the Step 2a response. For every linked ticket, fetch it now using `mcp__atlassian__getJiraIssue`.

**Do not proceed to Step 3 until all linked tickets have been fetched.** If there are many linked tickets, you may need to run multiple `mcp__atlassian__getJiraIssue` calls in parallel. If any linked ticket is inaccessible, warn the user and skip it, but continue with the review. If there are no linked tickets, note that and continue.

Use the linked tickets description, attachments, AC, and all comments as additional context when performing the AC check in Step 4.

### Step 3: Discover the project - **THIS SECTION WILL PROBABLY NEED TO BE REDONE AFTER UPDATE ROADMAP**

Before judging anything, work out how this project does things. Read what exists; do not assume:

- Test framework, test file locations and naming (look at config files and neighbouring tests).
- How tests are split: unit vs. functional/integration/e2e/component tests, and where each lives.
- Available scripts for tests, lint, type-check, and spec validation (`package.json`, `Makefile`, CI config, etc.).
- Whether the project has an API contract (OpenAPI/Swagger, GraphQL schema, protobuf, etc.). If not, the API spec check is skipped and reported as "not applicable".
- Project docs that state testing expectations (`CLAUDE.md`, `CONTRIBUTING.md`, `README`).

The checks below describe intent. Map them onto whatever the project actually uses. For example, "handlers" means controllers in one codebase and components or hooks in another.

### Step 4: Acceptance criteria coverage (both modes)

Review the PR diff itself for implementation-level issues (distinct from missing test coverage, that will be done in Step 5) or missing spec documentation (Step 7). These are gaps in the actual code, migration, or config change. For example: incorrect logic, a fix applied inconsistently accross sibling modules/entities, an incomplete migration backfill, a missing config/documentation update. List each acceptance criterion from the ticket. For each, decide whether the PR(s) implement it. Mark each `Covered`, `Partial`, or `Missing`, citing the file and line or test name that shows it. If the ticket has no explicit acceptance criteria, derive them from the description, say so, and ask the user to confirm them before posting.

Load this repo's `qa-review-patterns` file and the **Implementation Gaps** section as a checklist before concluding. If you are about to move on without flagging anything, scan that list first.

- When a bug fix, new field, or new validation constant is applied to one module/entity/handler among several siblings, grep the sibling entities and confim the same change was actually *applied* everywhere its needed, not just tested everywhere (thats Step 5's job).
- When a migration backfills a column and then adds a stricter contraint, (`FOREIGN KEY`/`CHECK`/`NOT NULL`) in the same `up()`, check whether the backfill's match condition covers the column's full historical value space, not just a freshly-seeded reference table.
- When new compose files, scripts, or environment variables are added, check that `README.md` and `.env.example` (if applicable) were updated to match.
- When an AC item or test step described behavior the code doesn't actually implement (or actively contradicts), flag it directly. Do not assume the AC is wrong.

This step applies in *both* `initial` and `final` modes. Implementation-level issues are visible from the PR diff alone and don't require a live test run.

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
