---
name: qa-review
description: Run a structured QA review of a Jira ticket and its pull request(s), checking acceptance criteria coverage, test coverage and interface documentation, then post the findings to the Jira ticket. Works on any kind of project. Use when the user invokes /qa-review.
argument-hint: <MODE> <JIRA-TICKET> <PR#> [PR#2 PR#3 ...] [json]
disable-model-invocation: true
---

# QA Review

You are performing a QA review for the given repository and take on the role of a QA engineer. These review sessions are the formal QA verification step in the ticket lifecycle. When all gaps are resolved and the user is satisfied, the ticket can be marked Done. The Jira ticket is the source of truth for the state of the work, so all findings are posted there.

This skill is project-agnostic. It applies to any code or feature a QA engineer would review, whatever the stack or kind of project. The universal checks live in [references/qa-core.md](references/qa-core.md). Optional lenses add stack-specific checks on top, and the review is complete without them (see Step 3).

## Invocation

```
/qa-review <MODE> <JIRA-TICKET> <PR#> [PR#2 PR#3 ...] [json]
```

## Arguments

`$ARGUMENTS` = `<MODE> <JIRA-TICKET> <PR#> [PR#2 ...] [json]`

- `MODE`: `initial` or `final`
- `JIRA-TICKET`: Jira issue key, e.g. `ABC-123`
- `PR#`: one or more GitHub PR numbers in the current repository (integers only, no `#` prefix required). The PRs must be in the same repo as the current working tree.
- `json` (optional, last): also print the findings as a JSON block at the end of the report (Step 12). Without it, print no JSON.

The mode, the ticket and at least one PR number are required. If the mode is not `initial` or `final`, the ticket key is missing, or no PR numbers are given, stop and show the usage line. Do not guess.

## Modes

The mode is the first argument, chosen by the user. Never infer it from the state of the PR.

| Step | `initial`: first time the ticket reaches QA | `final`: after dev addressed the initial feedback                      |
| ---- | ------------------------------------------- | ---------------------------------------------------------------------- |
| 1-5  | Run in full                                 | Run in full, and check that each gap from the initial review is closed |
| 6    | Skipped                                     | Evaluates higher-level tests                                           |
| 7-8  | Run in full                                 | Run in full                                                            |
| 9    | Changes nothing                             | Fixes test and documentation gaps                                      |
| 10   | Initial comment                             | Final comment, or an initial-style comment if gaps remain for dev      |

## Expected tools

| Need                                                                               | Tool                                                                                                                                  | If it is not available                                                                                                                                                                               |
| ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| The Jira ticket, its linked tickets and comments, and posting the review comment   | The Atlassian MCP server (`mcp__atlassian__getJiraIssue`, `mcp__atlassian__executeRead`, `mcp__atlassian__addOrEditJiraIssueComment`) | Ask the user to paste the ticket text: summary, description, acceptance criteria, linked tickets and comments. Work from that, and give the finished comment to the user as a draft to post by hand. |
| The pull request: description, changed files, diff                                 | The GitHub CLI (`gh`), already authenticated                                                                                          | None. Stop and tell the user.                                                                                                                                                                        |
| A first pass at choosing lenses (Step 3)                                           | `python3`, running `scripts/suggest_lenses.py`                                                                                        | Choose the lenses by hand from their `applies_when` blocks, and say so in one line.                                                                                                                  |
| A first pass at finding changed source files with no matching test change (Step 5) | `python3`, running `scripts/missing_tests.py`                                                                                         | Compare the changed source files with the changed test files by hand, and say so in one line.                                                                                                        |

Do not install tools, change authentication, or look for another way around a missing tool.

## Fetching

Token spend matters, so read only what the review needs.

- Fetch the ticket and each PR once. Afterwards work from the criteria you extracted and the list of changed files, not from repeated fetches.
- Start with the changed files. Run `gh pr view <PR#> --json title,body,baseRefName,headRefName,state,files` and request only those fields, never the full object.
- Apply "What to skip" to the list of files before you read any diff.
- Read the diff of a file only when it matters to the review: `gh api repos/{owner}/{repo}/pulls/<PR#>/files --paginate --jq '.[] | select(.filename == "<path>") | .patch'`. A bare `gh pr diff` of the whole PR is acceptable only when the PR is small.
- When the diff is too large to review carefully, review the highest-risk files first: changes to data, security, interfaces, and the code the acceptance criteria describe, before tests and documentation. Say in the report which files you did not review and why. Never silently truncate.

## What to skip

Leave these out of the review, and do not fetch their diffs:

- Lockfiles, generated files, bundled or minified output, and snapshots.
- Formatting, whitespace and naming-style points that the project's linter or formatter owns.
- Code the PR did not touch. A gap in unchanged code is out of scope unless the change depends on it.

When you skipped files that could have mattered, say so in one line in the report.

## Effort Handling

Run the review at the session's default effort level. Do not ask the user to raise the session-wide effort setting for a review.

Note: The skill's instructions cannot inspect or set the session's effort level, that control lives outside what these steps can enforce. Users should set their session effort to **high or above** before running `/qa-review`, the analysis in steps 3 and above assumes at least that floor.

If a specific finding is genuinely ambiguous (a contested AC interpretation, a subtle concurrency/data-integrity question) and cannot be resolved with confidence at the default effort, delegate just that sub-question to a single `Agent` call with an explicit higher `effort` override set to `max`. Keep the rest of the review (AC mapping, checklist scans, spec checks, etc.) at the default effort.

## Ground rules

- Tools: see Expected tools. If `gh` is unavailable or unauthenticated, stop and tell the user. If the Atlassian tool is unavailable, use the paste fallback and nothing else.
- Never run `git commit`, `git push`, `git add`, or any other command that records or publishes changes (`git fetch` is fine, it only updates remote-tracking refs). The engineer controls commits. Leave edits in the working tree and list the files changed in your summary.
- Never modify production code. Only test files, test fixtures, and interface documentation or contract files (such as an API spec) may be edited, and only in `final` mode during Step 9.
- Find first, fix later. Steps 4 to 7 only find gaps and record each one: what is wrong, where, and what change would close it. Step 8 checks which of those gaps are still open. Step 9 is the only step that edits a file or writes a test, and it acts only on gaps that Step 8 confirmed. Do not fix a gap at the moment you find it.
- Do not create files in the repo other than the tests and documentation or contract updates required by the review. Review state lives in Claude Code memory, not in the repo.
- The state of a PR (open, merged or closed) never changes the verdict. The Jira ticket tracks the work, and a PR that is already merged is reviewed like any other. Do not mention the PR state in the comment.
- Post comments to the Jira ticket only. Do not comment on the PRs.
- Do not transition the ticket's status unless the user asks.
- Discover the project's conventions instead of assuming them (see Step 3). This skill must work on any kind of project, with or without a matching lens.

## Progress Checklist

Immediately after parsing arguments (before Step 1), show the user a progress list so they can see where the review is at a glance, which matters most on reviews that run long. Use the session's task tool if it has one (`TodoWrite`, or `TaskCreate` and `TaskUpdate`) and create one entry per step below. If the session has no task tool, print the 12 steps once as a numbered list, then print a line `Step N of 12: <step name>` as each step starts. Word the entries so someone skimming the list understands what's happening without re-reading this file:

1. Load prior review memory for `{{ JIRA-TICKET }}`
2. Fetch Jira ticket, linked tickets, and PR(s) `{{ PR list }}`
3. Understand the change and select lenses
4. Acceptance criteria and implementation check
5. Test coverage
6. Functional/Integration test check
7. Interfaces and documentation check
8. Sanity check
9. Handle gaps
10. Write and post the Jira comment
11. Save/update memory
12. Final report

With a task tool, mark an item `in_progress` when you begin that step and flip it to `completed` the moment the step's work is actually done, not in a batch at the end, and not before the work behind it is real (e.g. don't complete the Jira comment entry until `addOrEditJiraIssueComment` has actually returned successfully, or the draft has been handed over). If Step 9 turns up enough gaps that tracking them individually would help, add them as sub-items under the "Handle gaps" entry rather than replacing it. The numbered list above should stay stable as the backbone so the progress list reads consistently across every review session. Add new items only as sub-items under the relevant step.

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

1. Jira, in two moves. If the tool is unavailable or a call fails, ask the user to paste the ticket text (see Expected tools).
   - Call `mcp__atlassian__getAccessibleAtlassianResources` once and keep the `cloudId`. Pass it on every Atlassian call, as its own argument. If the account has more than one site, use the one the ticket belongs to, and ask the user when that is unclear.
   - Then, in parallel, call `mcp__atlassian__getJiraIssue` with the ticket key and `view: "evidence"`, which returns the summary, description (acceptance criteria are usually in it), status, and `fields.issuelinks`, and read the comments. The issue call reports only how many comments there are, so read them with `mcp__atlassian__executeRead` using `name: "listJiraIssueComments"`, the `cloudId`, and `inputs` holding `issueIdOrKey` and `orderBy: "created"`. Page with `startAt` until `isLast` is true. Where a comment has a visibility restriction, do not quote it.
2. For each PR number, `gh pr view <PR#> --json title,body,baseRefName,headRefName,state,files`.

Then read the diffs of the files that matter, following Fetching and What to skip.

If the working tree is not on a PR's head branch and `final` mode needs to edit files, tell the user which branch to check out instead of switching branches yourself. If the head branch no longer exists (the PR was merged and the branch deleted), tell the user to make the fixes on a new branch from the base branch.

#### Step 2b: Fetch linked tickets (required before proceeding to Step 3)

If the ticket was pasted, skip this step: linked tickets are only available if the user pastes them too.

Inspect `fields.issuelinks` from the Step 2a response. For every linked ticket, fetch it now the same way as the main ticket: `mcp__atlassian__getJiraIssue` with the `cloudId` and `view: "evidence"`, and its comments.

**Do not proceed to Step 3 until all linked tickets have been fetched.** If there are many linked tickets, you may need to run these calls in parallel. If any linked ticket is inaccessible, warn the user and skip it, but continue with the review. If there are no linked tickets, note that and continue.

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
4. **Select lenses.** A lens is an optional file of extra checks for one kind of change. See [references/lenses/README.md](references/lenses/README.md) for the format. Lenses come from two places: the skill's own `references/lenses/` and the reviewed repo's `.claude/qa-review/lenses/`. If both have a lens with the same name, the repo's lens replaces the skill's.
   - **Run the script.** List the changed files of every PR (`gh pr diff <PR#> --name-only`) and pipe the combined list into `python3 ${CLAUDE_SKILL_DIR}/scripts/suggest_lenses.py`. It prints JSON: `matched` lenses with the changed files that matched their `paths`, and `unmatched` lenses with their `touches` line. Each entry has a `source` (`bundled` or `project`) that says which folder holds the lens file.
   - **Treat the output as a signal, not a verdict.** Read each matched lens and keep it only if it fits the change. For an unmatched lens, use its `touches` line to judge whether it still fits. A change can need several lenses, one, or none, and an unusual change may match nothing and still deserve a lens.
   - **If the script cannot run** (no `python3`, an error, or `status` is `no_input`), say so in one line and decide by hand. Read the `applies_when` block at the top of each file in the two lens folders and apply the same judgment.
   - Read only the lenses that apply. Any number of lenses, including none, is valid.
   - If the user names a lens, load it. If the user asks for the core only, load none, whatever the script suggested.
   - State which lenses you applied and why, or "core only". The core review stands on its own when no lens applies.

### Step 4: Acceptance criteria and implementation

List each acceptance criterion from the main ticket (linked tickets are only for extra context). For each, decide whether the PR(s) implement it. Mark each `Covered`, `Partial`, or `Missing`, citing the file and line or test name that shows it. If the ticket has no explicit acceptance criteria, derive them from the description and say so. Write "(derived from the description)" after each derived criterion in the comment. A derived criterion is a working assumption: if the change does not satisfy one, tell the user, but never list it as an unmet acceptance criterion or count it as a gap. Ask the user to confirm the derived criteria before posting (Step 10).

Then review the PR diff itself for implementation-level issues. These are gaps in the actual change, for example incorrect logic, a fix applied inconsistently across similar places, an incomplete data migration, or a missing config or documentation update. Missing test coverage is Step 5 and missing interface documentation is Step 7. Use the *Requirements and implementation* section of [references/qa-core.md](references/qa-core.md), plus the Step 4 checks of every lens you applied.

If the repo being reviewed has `.claude/qa-review/patterns.md`, read its **Implementation Gaps** section as a checklist before concluding. If you are about to move on without flagging anything, scan that list first. The file belongs to the team, so only read it.

When an AC item or test step describes behavior the code doesn't actually implement (or actively contradicts), flag it directly. Do not assume the AC is wrong.

Report implementation-level findings under *Other Findings* in the comment. This step applies in *both* `initial` and `final` modes. Implementation-level issues are visible from the PR diff alone and don't require a live test run.

### Step 5: Test coverage

Check the changed code against the *Test coverage* section of [references/qa-core.md](references/qa-core.md), plus the Step 5 checks of every lens you applied.

Start with a check by file name:

- **Run the script.** From the root of the repo being reviewed, pipe the combined list of changed files from Step 3 into `python3 ${CLAUDE_SKILL_DIR}/scripts/missing_tests.py`. It reads the team's own test-file patterns from `.claude/qa-review/test-patterns` when that file exists. It prints JSON: `missing_test_change` lists changed source files with no matching test file in the change, `has_test_change` lists those with one, `test_files_changed` lists every changed test file, `could_not_tell` lists files it cannot judge by name, and `not_checked` lists files that need no test (documentation, configuration, lock and generated files).
- **Treat the output as a signal, not a verdict.** It compares file names and folders and never reads a test. A file in `missing_test_change` may be covered by a test file with another name (check `test_files_changed`, and `same_name_tests_elsewhere`). A `likely_test_elsewhere` entry names a same-name test in another folder that probably covers the file, so read it before you report a gap. A file in `has_test_change` can still have untested branches, edge cases or weak assertions, so read the tests either way, and a file with `ambiguous_with` may share its test with another file of the same name. A file the PR deleted needs no test.
- **A project with no tests.** The script sees only the change. If Step 3 found that the project has no tests at all, do not report each file in `missing_test_change`. Report one gap for the change as a whole, naming the main changed source file.
- **If the script cannot run** (no `python3`, an error, or `status` is `no_input` or `could_not_tell`), say so in one line and compare the changed source files with the changed test files by hand.

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

### Step 10: Write and post the Jira comment

Write the comment for the Jira ticket using the template for the active mode:

1. **`initial` mode** → [assets/initial-comment.md](assets/initial-comment.md)
2. **`final` mode AND the verdict is either Option A or B (nothing remains blocking)** → [assets/final-comment.md](assets/final-comment.md)
3. **`final` mode AND the verdict is either Option C or D (any gaps remain unresolved and the ticket must go back to dev)** → DO NOT post a "Final" comment. A final review that finds a gap didn't actually reach a final, ready-to-close state (this endedup being another initial-review cycle), downgrade the review:
   - From the comments already fetched in Step 2a, count how many prior comments on this ticket have a title matching `Initial QA Review`.
   - Set `N` = that count + 1.
   - Post using [assets/initial-comment.md](assets/initial-comment.md), titled `Initial QA Review` if `N` is 1, otherwise `{{N}}{{ordinal suffix e.g. 2nd, 3rd, 4th, ...}} Initial QA Review`.
   - Follow the initial template's structure and rules exactly. Fold anything closed from the prior rounds into the *Implementation* narration. Any new gap found in Steps 4-7 (including ones surfaced via functional/integration testing) is reported as a plain `Gap:` entry in the matching section (*Tests*, *Interfaces and Documentation*, or *Other Findings*) with the recommendation worded into the description.
   - This relabeling changes only how the comment is posted (steps 3-9 still ran in full `final`-mode depth) and the *next* review of this ticket is still invoked as `/qa-review final ...` once dev addresses the gaps.

Post only the text under the "Template" heading, and follow the rules section of the template. Fill in every `{{ placeholder }}`, keep only the applicable verdict and the applicable branch of each conditional (delete the `{{ ... }}` marker lines), and remove no sections (write "None" or "Not applicable" instead). Keep it scannable: facts and file names, no padding. Aim for the word limit in the template's rules, but never drop a gap to reach it.

The comment must look like a normal comment from a person. Post it as Markdown exactly as the template formats it, with the default content format. Keep the `**bold**` headings, because Jira shows `*text*` as italics, and keep the line grouping the template uses (a blank line only between groups), because Jira shows a blank line as extra space. Never wrap it in a code fence, code block, `{code}`, `{noformat}` or panel, since Jira renders those as a grey box.

Then decide how it goes out. The skill only adds comments, and a comment can be edited or deleted in Jira, so do not ask for approval when there is nothing to confirm:

- **Post it right away** when the ticket states its own acceptance criteria and the Atlassian tool is available. Use `mcp__atlassian__addOrEditJiraIssueComment`, giving the `cloudId`, `issueIdOrKey` and `commentBody`. Never pass `commentId`: that edits an existing comment, and this skill only adds new ones. Keep the `commentId` the call returns for Step 11.
- **Ask first** when you derived acceptance criteria in Step 4. Show the finished comment as a draft, list the derived criteria under it, and ask the user to confirm them. Wait for a clear yes. If the user wants changes, edit the draft and show it again. When the user agrees, post it as above.
- **Do not post** when the ticket was pasted or the Atlassian tool is unavailable. Give the draft to the user to post by hand, and say so.

Do not transition the ticket yourself. If the verdict is "Ready to mark Done" or a status change would clearly be next, offer it and wait for the user to say yes.

### Step 11: Save memory

Write or update a memory file at `~/.claude/projects/<project_name>/memory/qa-review-<JIRA-TICKET>.md` recording:

- Mode (`initial` or `final`). If step 10 downgraded a `final` review to an "Nth Initial Review" comment, record the mode as `final` (that's the depth the review actually ran at) but note explicitly that the comment was posted using the initial template/title due to a remaining gap, so a later review doesn't miscount comment numbering or assume this ticket never had a final-depth pass.
- PR numbers reviewed
- All gaps found (even if none), the final review depends on this list.
- Actions taken (reported to dev, fixed in session, n/a)
- The Jira comment ID returned by the post, or "not posted" if the user posts it by hand
- Any patterns specific to this ticket worth remembering for future reviews (e.g. AC misinterpretation, test framework gotchas, etc.). If you saw a gap pattern that `.claude/qa-review/patterns.md` does not list, do not edit that file. Note it here and suggest it in the final report (Step 12).

Follow the memory file format from the system prompt (frontmatter plus body). Update the existing memory if there is one rather than creating a second. Update `MEMORY.md` index if a new file was created.

### Step 12: Report to the user

End with a report in this order. Give each part its own `##` heading, so a reader (and a tool) can tell where the Jira comment ends.

1. **`## Summary`**: verdict, number of gaps by status, files modified in the working tree (`final` only, uncommitted), commands run with pass/fail, and the posted comment's ID and link (or a note that it was not posted).
2. **`## Comment`**: the Jira comment exactly as it was posted, so the user sees what went out. If you already showed it as a draft in Step 10 (derived criteria, or a pasted ticket), say that and do not print it again.
3. **`## Findings`**: the gaps as a readable list, as described in [references/output-format.md](references/output-format.md), starting with a `Lenses applied:` line. It is for the session only. Never include it in the Jira comment.
4. **`## Suggested additions to .claude/qa-review/patterns.md`**: only if Step 11 found a gap pattern worth keeping. A short list, one or two lines each, for the team to commit. Only edit that file if the user asks you to.

If the user ended the command with `json`, finish with the structured findings block described in [references/output-format.md](references/output-format.md), after the list. Without `json`, print no JSON.

`/compact` cannot be triggered automatically. As the final action of every review, output the following message to the user verbatim, they can run the command as-is to cleanup the session with a consistent focus and memory state:

```
/compact Keep: ticket key and PR numbers reviewed; mode (initial/final); each gap found with its category (e.g. unit test, integration test, spec, implementation, etc) and action taken (e.g. fixed in session, sent back to dev, .todo stub added, etc); files created or modified and what changed in each; Jira comment ID. Discard everything else.
```
