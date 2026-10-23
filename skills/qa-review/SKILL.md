---
name: qa-review
description: Run a structured QA review of a Jira ticket and its pull request(s), checking acceptance criteria coverage, test coverage and interface documentation, then post the findings to the Jira ticket. Works on any kind of project. Use when the user invokes /qa-review.
argument-hint: <MODE> <JIRA-TICKET> <PR#> [PR#2 PR#3 ...]
disable-model-invocation: true
---

# QA Review

You are performing a QA review for the given repository and take on the role of a QA engineer. These review sessions are the formal QA verification step in the ticket lifecycle. When all gaps are resolved and the user is satisfied, the ticket can be marked Done. The Jira ticket is the source of truth for the state of the work, so all findings are posted there.

This skill is project-agnostic. It applies to any code or feature a QA engineer would review, whatever the stack or kind of project. The universal checks live in [references/qa-core.md](references/qa-core.md). Optional lenses add stack-specific checks on top, and the review is complete without them (see Step 3).

## Invocation

```
/qa-review <MODE> <JIRA-TICKET> <PR#> [PR#2 PR#3 ...]
```

## Arguments

`$ARGUMENTS` = `<MODE> <JIRA-TICKET> <PR#> [PR#2 ...]`

- `MODE`: `initial` or `final`
- `JIRA-TICKET`: Jira issue key, e.g. `ABC-123`
- `PR#`: one or more GitHub PR numbers in the current repository (integers only, no `#` prefix required). The PRs must be in the same repo as the current working tree.

All arguments are required. If the mode is not `initial` or `final`, the ticket key is missing, or no PR numbers are given, stop and show the usage line. Do not guess.

## Effort Handling

Run the review at the session's default effort level. Do not ask the user to raise the session-wide effort setting for a review.

Note: The skill's instructions cannot inspect or set the session's effort level, that control lives outside what these steps can enforce. Users should set their session effort to **high or above** before running `/qa-review`, the analysis in steps 3 and above assumes at least that floor.

If a specific finding is genuinely ambiguous (a contested AC interpretation, a subtle concurrency/data-integrity question) and cannot be resolved with confidence at the default effort, delegate just that sub-question to a single `Agent` call with an explicit higher `effort` override set to `max`. Keep the rest of the review (AC mapping, checklist scans, spec checks, etc.) at the default effort.

## Ground rules

- Tools: Jira through the Atlassian MCP server, GitHub through the `gh` CLI. If either is unavailable or unauthenticated, stop and tell the user. Do not work around it.
- Never run `git commit`, `git push`, `git add`, or any other command that records or publishes changes (`git fetch` is fine, it only updates remote-tracking refs). The engineer controls commits. Leave edits in the working tree and list the files changed in your summary.
- Never modify production code. Only test files, test fixtures, and interface documentation or contract files (such as an API spec) may be edited, and only in `final` mode during Step 9.
- Find first, fix later. Steps 4 to 7 only find gaps and record each one: what is wrong, where, and what change would close it. Step 8 checks which of those gaps are still open. Step 9 is the only step that edits a file or writes a test, and it acts only on gaps that Step 8 confirmed. Do not fix a gap at the moment you find it.
- Do not create files in the repo other than the tests and documentation or contract updates required by the review. Review state lives in Claude Code memory, not in the repo.
- Post comments to the Jira ticket only. Do not comment on the PRs.
- Do not transition the ticket's status unless the user asks.
- Discover the project's conventions instead of assuming them (see Step 3). This skill must work on any kind of project, with or without a matching lens.

## Progress Checklist

Immediately after parsing arguments (before Step 1), create a todo list with `TodoWrite` so the user can see review progress at a glance, this matters most on reviews that run long. Use one entry per step below, worded so someone skimming the list understands what's happening without re-reading this file:

1. Load prior review memory for `{{ JIRA-TICKET }}`
2. Fetch Jira ticket, linked tickets, and PR(s) `{{ PR list }}`
3. Understand the change and select lenses
4. Acceptance criteria and implementation check
5. Test coverage
6. Functional/Integration test check
7. Interfaces and documentation check
8. Sanity check
9. Handle gaps
10. Post Jira comment
11. Save/update memory
12. Final report

Mark an item `in_progress` when you begin that step and flip it to `completed` the moment the step's work is actually done, not in a batch at the end, and not before the work behind it is real (e.g. don't complete "Post Jira comment" until `addCommentToJiraIssue` has actually returned successfully). If Step 9 turns up enough gaps that tracking them individually would help, add them as sub-items under the "Handle gaps" entry rather than replacing it. The numbered list above should stay stable as the backbone so the progress bar reads consistently across every review session. Add new items only as sub-items under the relevant step.

## Workflow

### Step 1: Load prior review memory

Check `~/.claude/projects/<project_name>/memory/MEMORY.md` for a prior review entry for this ticket (e.g. `qa-review-<JIRA-TICKET>`). If one exists, read it: it holds the gaps and verdict from earlier reviews of this ticket.

1. `initial`
   - with prior memory: This is a repeat `initial` review. Note any previously identified gaps so you don't re-report closed ones.
2. `final`
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

### Step 3: Understand the change and select lenses

Before judging anything, work out what the change is and how this project does things. Read what exists; do not assume.

1. **State what the change does.** Write a short plain-language summary of what it does and what it touches (user-facing behavior, data, interfaces, configuration, build or deploy, tests, docs). This also feeds the *Implementation* section of the comment.
2. **Work out how this project is tested.**
   - Test framework, test file locations and naming (look at config files and neighbouring tests).
   - How tests are split: unit vs. functional/integration/e2e/component tests, and where each lives.
   - Available scripts for tests, lint, type-check, and any validation (`package.json`, `Makefile`, CI config, etc.).
   - Project docs that state testing expectations (`CLAUDE.md`, `CONTRIBUTING.md`, `README`).
   - Whether the change touches an externally visible interface, and where that interface is documented.

   If the stack is unfamiliar, say so and apply the core checklist instead of guessing at the stack's conventions.
3. **Read the core checklist.** [references/qa-core.md](references/qa-core.md) always applies, whatever the project. Steps 4 to 7 point at its sections.
4. **Select lenses.** A lens is an optional file of extra checks for one kind of change. See [references/lenses/README.md](references/lenses/README.md) for the format.
   - Each file in `references/lenses/` opens with an `applies_when` block. A lens is a candidate when a changed file matches one of its `paths`. When no path matches, use its `touches` line to judge whether the lens still fits.
   - Read only the lenses that apply. Any number of lenses, including none, is valid.
   - If the user names a lens, load it. If the user asks for the core only, load none.
   - State which lenses you applied and why, or "core only". The core review stands on its own when no lens applies.

### Step 4: Acceptance criteria and implementation

List each acceptance criterion from the main ticket (linked tickets are only for extra context). For each, decide whether the PR(s) implement it. Mark each `Covered`, `Partial`, or `Missing`, citing the file and line or test name that shows it. If the ticket has no explicit acceptance criteria, derive them from the description, say so, and ask the user to confirm them before posting.

Then review the PR diff itself for implementation-level issues. These are gaps in the actual change, for example incorrect logic, a fix applied inconsistently across similar places, an incomplete data migration, or a missing config or documentation update. Missing test coverage is Step 5 and missing interface documentation is Step 7. Use the *Requirements and implementation* section of [references/qa-core.md](references/qa-core.md), plus the Step 4 checks of every lens you applied.

If the repo being reviewed has a `qa-review-patterns` file, load its **Implementation Gaps** section as a checklist before concluding. If you are about to move on without flagging anything, scan that list first.

When an AC item or test step describes behavior the code doesn't actually implement (or actively contradicts), flag it directly. Do not assume the AC is wrong.

Report implementation-level findings under *Other Findings* in the comment. This step applies in *both* `initial` and `final` modes. Implementation-level issues are visible from the PR diff alone and don't require a live test run.

### Step 5: Test coverage

Check the changed code against the *Test coverage* section of [references/qa-core.md](references/qa-core.md), plus the Step 5 checks of every lens you applied.

Every gap gets: what is untested, where (file and symbol), and what test would close it. Record the gap only. Do not write the test here (see Step 9).

### Step 6: Functional/integration tests

In `initial` mode skip this step and say it was skipped.

In `final` mode, evaluate whether observable behaviour is covered at the project's higher test level, using the *Higher-level tests* section of [references/qa-core.md](references/qa-core.md) plus the Step 6 checks of every lens you applied.

Only evaluate here. For each behavior with no higher-level test, record a gap: the behavior, the project's own directory and style where the test belongs, and the test that would close it. If you can already tell that the test cannot be written right now (missing environment, dependency, credentials), note why. Writing the tests, adding `.todo` stubs and running them all happen in Step 9, after Step 8 has confirmed the gap is still open.

### Step 7: Interfaces and documentation

Check the *Interfaces and documentation* section of [references/qa-core.md](references/qa-core.md), plus the Step 7 checks of every lens you applied.

Report this step as not applicable if the change touches no externally visible interface and no user-facing behavior.

In both modes, only record the gaps here: what is missing or wrong, in which documentation, spec, or contract file, and what change would close it. In `final` mode the fixes are made in Step 9.

### Step 8: Sanity-check gaps against the current base branch

Before reporting or fixing any gap, verify it still exists on the PR's base branch as it is now. A gap identified in the PR diff may have already been resolved by a commit or PR merged after the one under review. No gap has been fixed at this point: Steps 4 to 7 only record them.

The base branch is the `baseRefName` from the `gh pr view` result in Step 2a. Do not read the files on disk for this check: the working tree is usually on the PR's own branch, so it shows the PR's version and the gap would always look open. Read the base branch from git instead:

1. Run `git fetch origin <base>` so the base branch is current. This only updates the remote-tracking ref and does not touch the working tree.
2. Read a file with `git show origin/<base>:<path>`, or search with `git grep -n <pattern> origin/<base> -- <path>`.
3. If `git fetch` is not possible, use `gh api repos/{owner}/{repo}/contents/<path>?ref=<base>` instead. If neither works, say that Step 8 could not be run and keep every gap open.

For each gap found in previous steps:

1. Identify the specific file and the change that would close the gap (e.g. a test describe block that should exist, a spec parameter that should be present, etc.).
2. Read that file on the base branch, or search it for the expected pattern, and check whether the fix is already present. A file that does not exist on the base branch means the fix is not there.
3. If that fix is already on the base branch: mark the gap **"already fixed on the base branch - skip"** and exclude it from the report and from any in-session fixes.
4. If the fix is not on the base branch: carry it forward to the next step as normal.

If the PR is already merged, the base branch contains the PR itself. A gap is then still open only if the change that closes it is missing from the base branch as it stands now.

### Step 9: Handle gaps

This is the only step that changes files. Work only on the gaps that Step 8 confirmed are still open. Leave alone any gap marked "already fixed on the base branch - skip".

In `initial` mode, change nothing. Every open gap goes into the comment for dev.

In `final` mode, fix the open gaps that the ground rules allow (test files, test fixtures, documentation and contract files; no production code, no commits):

- **Missing tests (Steps 5 and 6).** Write them in the project's own test directory and style. If a test cannot be written right now (missing environment, dependency, credentials), add a `.todo` stub (or the framework's equivalent) so the gap is tracked in source control, and record why in the comment.
- **Documentation, spec, or contract gaps (Step 7).** Update the files.
- **Verify the fixes.** Run the new and changed tests with the project's test command, and re-run any validation the project has (such as a spec linter). Report the results honestly. A fix that fails verification does not count: report that gap as still open.
- **Anything that needs a production code change** is not fixed here. It goes into the comment as a gap for dev, which includes the implementation findings from Step 4.

### Step 10: Post Jira comment

Use `mcp__atlassian__addCommentToJiraIssue` to post a comment on the Jira ticket using the template for the active mode:

1. **`initial` mode** → [assets/initial-comment.md](assets/initial-comment.md)
2. **`final` mode AND the verdict is either Option A or B (nothing remains blocking)** → [assets/final-comment.md](assets/final-comment.md)
3. **`final` mode AND the verdict is either Option C or D (any gaps remain unresolved and the ticket must go back to dev)** → DO NOT post a "Final" comment. A final review that finds a gap didn't actually reach a final, ready-to-close state (this endedup being another initial-review cycle), downgrade the review:
   - From the comments already fetched in Step 2a, count how many prior comments on this ticket have a title matching `Initial QA Review`.
   - Set `N` = that count + 1.
   - Post using [assets/initial-comment.md](assets/initial-comment.md), titled `Initial QA Review` if `N` is 1, otherwise `{{N}}{{ordinal suffix e.g. 2nd, 3rd, 4th, ...}} Initial QA Review`.
   - Follow the initial template's structure and rules exactly. Fold anything closed from the prior rounds into the *Implementation* narration. Any new gap found in Steps 4-7 (including ones surfaced via functional/integration testing) is reported as a plain `Gap:` entry in the matching section (*Tests*, *Interfaces and Documentation*, or *Other Findings*) with the recommendation worded into the description.
   - This relabeling changes only how the comment is posted (steps 3-9 still ran in full `final`-mode depth) and the *next* review of this ticket is still invoked as `/qa-review final ...` once dev addresses the gaps.

Post only the text under the "Template" heading, and follow the rules section of the template. Fill in every `{{ placeholder }}`, keep only the applicable verdict and the applicable branch of each conditional (delete the `{{ ... }}` marker lines), and remove no sections (write "None" or "Not applicable" instead). Keep it scannable: facts and file names, no padding.

The comment must look like a normal comment from a person. Post it as plain text exactly as the template formats it. Never wrap it in a code fence, code block, `{code}`, `{noformat}` or panel, since Jira renders those as a grey box. Post it to the ticket with the Atlassian MCP, then show the user the same text in the session.

Do not transition the ticket yourself. If the verdict is "Ready to mark Done" or a status change would clearly be next, offer it and wait for the user to say yes.

### Step 11: Save memory

Write or update a memory file at `~/.claude/projects/<project_name>/memory/qa-review-<JIRA-TICKET>.md` recording:

- Mode (`initial` or `final`). If step 10 downgraded a `final` review to an "Nth Initial Review" comment, record the mode as `final` (that's the depth the review actually ran at) but note explicitly that the comment was posted using the initial template/title due to a remaining gap, so a later review doesn't miscount comment numbering or assume this ticket never had a final-depth pass.
- PR numbers reviewed
- All gaps found (even if none), the final review depends on this list.
- Actions taken (reported to dev, fixed in session, n/a)
- The Jira comment ID returned by the post
- Any patterns specific to this ticket worth remembering for future reviews (e.g. AC misinterpretation, test framework gotchas, etc.). If a new gap pattern was observed and the repo being reviewed has a `qa-review-patterns` file, add it there and note it here.

Follow the memory file format from the system prompt (frontmatter plus body). Update the existing memory if there is one rather than creating a second. Update `MEMORY.md` index if a new file was created.

### Step 12: Report to the user

End with a short summary: verdict, number of gaps by status, files modified in the working tree (`final` only, uncommitted), commands run with pass/fail, and a link to the posted comment.

After the summary, print the structured findings block described in [references/output-format.md](references/output-format.md). It is for the session and for tools only. Never include it in the Jira comment.

`/compact` cannot be triggered automatically. As the final action of every review, output the following message to the user verbatim, they can run the command as-is to cleanup the session with a consistent focus and memory state:

```
/compact Keep: ticket key and PR numbers reviewed; mode (initial/final); each gap found with its category (e.g. unit test, integration test, spec, implementation, etc) and action taken (e.g. fixed in session, sent back to dev, .todo stub added, etc); files created or modified and what changed in each; Jira comment ID. Discard everything else.
```
