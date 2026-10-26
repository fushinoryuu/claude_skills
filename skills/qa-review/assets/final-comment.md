# QA Review Final Review Comment Template

Use this template when posting the Jira comment for a `final` mode review. Fill in every `{{ placeholder }}`, pick the correct verdict, and delete the unused verdict option before posting.

---

## Rules for final review comments

1. Always include the *Gaps from Previous Review* section, even if there was no prior initial review.
2. Each new gap entry (Tests, Interfaces and Documentation, and Other Findings sections) needs both a **Gap** line and an **Action** line - unlike the initial review which only has a Gap line. Gaps from the previous review use the one-line ✓/✗ format instead.
3. Keep each gap description to one sentence: what is untested and why it matters.
4. Keep each action to one sentence: what was done or why it was sent back.
5. Use `**Section Name**` for bold headers. The comment is posted as Markdown, where a single `*` gives italics, not bold.
6. Use `✓`/`✗` for AC items and gap closure status, `✅`/`❌` for the verdict line.
7. Do not include file line numbers - they change and go stale.
8. Do not include any code snippets in the comment.
9. Never wrap the comment, or any part of it, in a code fence, code block, `{code}`, `{noformat}` or panel. Jira renders those as a grey box instead of a normal comment.
10. Do not use Markdown tables. Use one line per item.
11. Never change Jira ticket status.
12. Keep the lines of one group on consecutive lines with no blank line between them: the title and the `PRs`, `Reviewed` and `Lenses` lines, the acceptance criteria, and the Gap (and Action) lines of one section. Leave one blank line between groups and sections. Jira shows a single line break as a line break but a blank line as extra space, so blank lines between every line make the comment look loose. Do not add trailing spaces or backslashes to force a break.
13. Keep the whole comment to 600 words or fewer. If it is longer, shorten the Implementation summary and the wording of each Gap and Action before dropping a gap.

---

## Verdict decision guide

| Situation                                                                                               | Verdict  |
| ------------------------------------------------------------------------------------------------------- | -------- |
| All initial gaps closed, no new gaps, functional/integration tests pass or are not required             | Option A |
| All initial gaps closed, new gaps were found and all fixed in this session, tests pass or not required  | Option B |
| Test .todo stubs added, unable to write tests for some reason, and no gap needs dev action              | Option C |
| Any gap remains that cannot be fixed in this session (e.g. it would require changes to production code) | Option D |
| Implementation is wrong or AC not met                                                                   | Option D |
| Tests fail and the failure is a genuine bug that needs a dev fix (first try to fix the test in session) | Option D |

If more than one row applies, Option D takes precedence over Option C.

---

## Template

Post everything below this line as the comment body. It is Markdown comment text, not a code block.

**Final QA Review - {{ JIRA TICKET }}**
PRs: {{ PR list, e.g. #123 #456}}
Reviewed: {{ YYYY-MM-DD }}
Lenses: {{ names of the lenses applied, or "core only" }}

---

**Verdict**

{{ OPTION A - All clear, nothing to fix }}
✅ QA verified. No gaps found. Ready to mark Done.

{{ OPTION B - Gaps fixed in this session }}
✅ QA verified with fixes. {{ N }} gap(s) resolved in this session (see below). Ready to mark Done.

{{ OPTION C - Gaps remain, unable to create tests and .todo stubs added }}
❌ {{ N }} gap(s) require QA Engineer to triage issues creating integration tests. Ticket remains in QA.

{{ OPTION D - Gaps remain, sent back }}
❌ {{ N }} gap(s) require Developer action (see below). Sending back to dev.

---

**Acceptance Criteria**

{{ One line per AC item: }}
✓ {{ AC item text - met }}
✗ {{ AC item text - not met, with brief reason }}

---

**Implementation Changes Since Last Review**

{{ 2-4 sentence summary of what the new PR(s) actually did to fix the gaps identified in the previous review. Write for a reader who has not seen the diff. Focus on the approach taken, not just what the ticket asked for. }}

---

**Gaps from Previous Review**

{{ If no initial review was found in memory or in the Jira ticket comments: }}
No initial review found.

{{ If all gaps from previous review are confirmed closed: }}
All gaps from previous review confirmed closed.

{{ Otherwise one line per gap from the initial review: }}
✓ {{ Gap description }} - closed. {{ How it was closed, e.g. by dev or by QA in this session }}
✗ {{ Gap description }} - still open. {{ What is still missing }}

---

**Tests**

{{ If no new gaps: }}
No new gaps found.

{{ If new gaps found and fixed in this session (one Gap line and one Action line per gap): }}
Gap: {{ Describe what is untested }} - `{{ file }}`.
Action: Fixed in this session - {{ describe what was fixed, e.g. "added 3 tests to sample.test.ts for input validation" }}

{{ If new gaps found but not fixable in this session (one Gap line and one Action line per gap): }}
Gap: {{ Describe what is untested }} - `{{ file }}` - {{ Test that would close it }}.
Action: Sent back to dev - {{ brief reason why it cannot be fixed in session, e.g. "an update to production code would be required" }}

{{ Repeat per gap }}

---

**Functional/Integration Tests**

{{ If all updates are fully testable with only unit tests: }}
Not required - behavior is fully covered by unit tests.

{{ If no missing functional/integration tests: }}
Fully tested with existing test suite.

{{ If tests that could not be written now: }}
Not written: `{{ stub file }}` - {{ why it could not be written now }}. A `.todo` stub tracks it in source control.

{{ Tests added: }}
Added: `{{ test file }}` - {{ behavior it covers }}.

{{ Result: }}
{{ Command run and pass/fail count }}

---

**Interfaces and Documentation**

{{ If the change touches no externally visible interface or user-facing behavior: }}
Not applicable - no interface or user-facing change.

{{ If no changes were needed and documentation is untouched: }}
No documentation changes required.

{{ If documentation was updated correctly by the dev: }}
Correct. Updated: {{ list files }}.

{{ If new gaps found and fixed in this session (one Gap line and one Action line per gap): }}
Gap: {{ What was missing or wrong in the documentation or contract }} - `{{ file }}`.
Action: Fixed in this session - {{ describe the change, e.g. "added the missing response code to the spec" }}

{{ If new gaps found but not fixable (one Gap line and one Action line per gap): }}
Gap: {{ What is missing or wrong in the documentation or contract }} - `{{ file }}`.
Action: Sent back to dev - {{ brief reason, e.g. "an update to production code would be required" }}

{{ Repeat per gap }}

---

**Other Findings**

{{ If no other findings: }}
None.

{{ If findings (one Gap line and one Action line per finding; they need a developer fix because production code may not be changed in this review): }}
Gap: {{ Describe the implementation-level issue and why it matters }} - `{{ file }}` - {{ Change that would close it }}.
Action: Sent back to dev - {{ brief reason }}

{{ Repeat per gap }}
