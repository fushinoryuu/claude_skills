# QA Review Final Review Comment Template

Use this template when posting the Jira comment for an `final` mode review. Fill in every `{{ placeholder }`, pick the correct verdict, and delete the unused verdict option before posting.

---

## Rules for final review comments

- Always include the _Gaps from Initial Review_ section, even if there was no prior initial review.
- Each gap entry needs both a **Gap** line and an **Action** line - unlike the initial review which only has a Gap line.
- Keep each gap description to one sentence: what is missing and why it matters.
- Keep each action to one sentence: what was done or why it was sent back.
- Use `*Section Name*` for bold headers (Jira rendering).
- Use `✓`/`✗` for AC items and gap closure status, `✅`/`❌` for the verdict line.
- Do not include file line numbers - they change and go stale.
- Do not include any code snippets in the comment.
- Never wrap the comment, or any part of it, in a code fence, code block, `{code}`, `{noformat}` or panel. Jira renders those as a grey box instead of a normal comment.
- Do not use Markdown tables. Use one line per item.
- Never change Jira ticket status.

---

## Verdict decision guide

| Situation                                                                                               | Verdict  |
| ------------------------------------------------------------------------------------------------------- | -------- |
| All initial gaps closed, no new gaps, functional/integration tests pass                                 | Option A |
| All initial gaps closed, new gaps were found and fixed in this session                                  | Option B |
| Test .todo stubs added, unable to write tests for some reason                                           | Option C |
| Any gap remains that cannot be fixed in this session (e.g. it would require changes to production code) | Option D |
| Implementation is wrong or AC not met                                                                   | Option D |

---

## Template

Post everything below this line as the comment body. It is plain comment text, not a code block.

Final QA Review - {{ JIRA TICKET }}
PRs: {{ PR list, e.g. #123 #456}}
Reviewed: {{ YYYY-MM-DD }}

---

*Verdict*

{{ OPTION A - All clear, nothing to fix }}
✅ QA verified. No gaps found. Ready to mark Done.

{{ OPTION B - Gaps fixed in this session }}
✅ QA verified with fixes. {{ N }} gap(s) resolved in this session (see below). Ready to mark Done.

{{ OPTION C - Gaps remain, unable to create tests and .todo stubs added }}
❌ {{ N }} gap(s) require QA Engineer to triage issues creating integration tests. Ticket reamins in QA.

{{ OPTION D - Gaps remain, sent back }}
❌ {{ N }} gap(s) require Developer action (see below). Sending back to dev.

---

*Acceptance Criteria*
{{ One line per AC item: }}
✓ {{ AC item text - met }}
✗ {{ AC item text - not met, with brief reason }}

---

*Implementation Changes Since Last Review*
{{ 2-4 sentence summary of what the new PR(s) actually did to fix the gaps identified in the previous review. Write for a reader who has not seen the diff. Focus on the approach taken, not just what the ticket asked for. }}

---

*Gaps from Previous Review*
{{ If there was no initial review on record: }}
No prior review on record.

{{ If all gaps from previous review are confirmed closed: }}
All gaps from previous review confirmed closed.

{{ Otherwise one line per gap from the initial review: }}
✓ {{ Gap description }} - closed. {{ How it was closed, e.g. by dev or by QA in this session }}
✗ {{ Gap description }} - still open. {{ What is still missing }}

---

*Unit Tests*
{{ If no new gaps: }}
No new gaps found.

{{ If new gaps found and fixed in this session (one block per gap): }}
Gap: {{ Describe what is untested }} - `{{ file }}`.
Action: Fixed in this session - {{ describe what was fixed, e.g. "added 3 tests to sample.test.ts for input validation" }}

{{ If new gaps found but not fixable in this session (one block per gap): }}
Gap: {{ Describe what is untested }} - `{{ file }}`- {{ Test that would close it }}.
Action: Sent back to dev - {{ brief reason why it can't be fixed in session, e.g. "an update to production code would be required" }}

{{ Repeat per gap }}

---

*Functional/Integration Tests*
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

*OpenAPI Spec*
{{ If project does not contain any API contracts/specs: }}
Not applicable - no API contract in this project.

{{ If no changes were needed and spec is untouched: }}
No spec changes required.

{{ If spec was updated correctly by the dev: }}
Correct. Changes in source files only ({{ list files }}).

{{ If new gaps found and fixed in this session (one block per gap): }}
Gap: {{ What was missing or wrong in the spec }} - `{{ spec file }}`.
Action: Fixed in this session - {{ describe the change, e.g. "added missing response code" }}

{{ If new gaps found but not fixable (one block per gap): }}
Gap: {{ What is missing or wrong in the spec }} - `{{ spec file }}`.
Action: Sent back to dev - {{ brief reason, e.g. "an update to production code would be required" }}

{{ Repeat per gap }}

---

*Changes Made In This Session*
{{ If no files were edited: }}
None.

{{ Otherwise: }}
The following files were edited and are not committed:
- `{{ file }}` - {{ what changed }}

---

*Remaining Work For Dev*
{{ If none: }}
None.

{{ Otherwise one line per open gap that needs a production code change: }}
- {{ Gap }}
