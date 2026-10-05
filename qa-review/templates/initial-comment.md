# QA Review Initial Review Comment Template

Use this template when posting the Jira comment for an `initial` mode review. Fill in every `{{ placeholder }`, pick the correct verdict, and delete the unused verdict option before posting.

---

## Rules for initial review comments

1. **Never include an Actions section.** Initial review only reports gaps - it does not fix them.
2. **Never mention functional/integration tests.** These types of tests are evaluated in the final review only.
3. Keep each gap description to one sentence: what is missing and why it matters.
4. Use `*Section Name*` for bold headers (Jira rendering).
5. Use `✓`/`✗` for AC items, `✅`/`❌` for the verdict line.
6. Do not include file line numbers - they change and go stale.
7. Do not include any code snippets in the comment.
8. Never wrap the comment, or any part of it, in a code fence, code block, `{code}`, `{noformat}` or panel. Jira renders those as a grey box instead of a normal comment.
9. Do not use Markdown tables. Use one line per item.
10. Never change Jira ticket status.

---

## Verdict decision guide

| Situation                                    | Verdict  |
| -------------------------------------------- | -------- |
| AC met, unit tests complete, spec correct    | Option A |
| Any gap in: AC coverage, unit tests, or spec | Option B |

---

## Template

Post everything below this line as the comment body. It is plain comment text, not a code block.

Initial QA Review - {{ JIRA TICKET }}
PRs: {{ PR list, e.g. #123 #456}}
Reviewed: {{ YYYY-MM-DD }}

---

*Verdict*

{{ OPTION A - No gaps found }}
✅ No gaps found. Ready for final QA review.

{{ OPTION B - Gaps found }}
❌ {{ N }} gap(s) found (see below). Sending back to dev.

---

*Acceptance Criteria*
{{ One line per AC item: }}
✓ {{ AC item text - met }}
✗ {{ AC item text - not met, with brief reason }}

---

*Implementation*
{{ 2-4 sentence summary of what the PR(s) actually do. Write for a reader who has not seen the diff. Focus on the approach taken, not just what the ticket asked for. }}

---

*Unit Tests*
{{ If no gaps: }}
No gaps found.

{{ If gaps found (one block per gap): }}
Gap: {{ Describe what is untested }} - `{{ file }}`- {{ Test that would close it }}.

{{ Repeat per gap }}

---

*OpenAPI Spec*
{{ If project does not contain any API contracts/specs: }}
Not applicable - no API contract in this project.

{{ If no changes were needed and spec is untouched: }}
No spec changes required.

{{ If spec was updated correctly by the dev: }}
Correct. Changes in source files only ({{ list files }}).

{{ If gaps found (one block per gap): }}
Gap: {{ What is missing or wrong in the spec }} - `{{ spec file }}` - {{ Change that would close it }}.

{{ Repeat per gap }}
