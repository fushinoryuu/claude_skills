# QA Review Initial Review Comment Template

Use this template when posting the Jira comment for an `initial` mode review. Fill in every `{{ placeholder }}`, pick the correct verdict, and delete the unused verdict option before posting.

---

## Rules for initial review comments

1. **Never include an Actions section.** Initial review only reports gaps - it does not fix them.
2. **Never mention functional/integration tests.** These types of tests are evaluated in the final review only.
3. Keep each gap description to one sentence: what is untested and why it matters.
4. Use `**Section Name**` for bold headers. The comment is posted as Markdown, where a single `*` gives italics, not bold.
5. Use `✓`/`✗` for AC items, `✅`/`❌` for the verdict line.
6. Do not include file line numbers - they change and go stale.
7. Do not include any code snippets in the comment.
8. Never wrap the comment, or any part of it, in a code fence, code block, `{code}`, `{noformat}` or panel. Jira renders those as a grey box instead of a normal comment.
9. Do not use Markdown tables. Use one line per item.
10. Never change Jira ticket status.
11. Keep the lines of one group on consecutive lines with no blank line between them: the title and the `PRs`, `Reviewed` and `Lenses` lines, the acceptance criteria, and the Gap (and Action) lines of one section. Leave one blank line between groups and sections. Jira shows a single line break as a line break but a blank line as extra space, so blank lines between every line make the comment look loose. Do not add trailing spaces or backslashes to force a break.
12. Keep the whole comment to 500 words or fewer. If it is longer, shorten the Implementation summary and the wording of each Gap before dropping a gap.

---

## Verdict decision guide

| Situation                                                                       | Verdict  |
| ------------------------------------------------------------------------------- | -------- |
| AC met, tests complete, documentation correct, no other findings                | Option A |
| Any gap in: AC coverage, tests, interfaces and documentation, or other findings | Option B |

---

## Template

Post everything below this line as the comment body. It is Markdown comment text, not a code block.

**Initial QA Review - {{ JIRA TICKET }}**
PRs: {{ PR list, e.g. #123 #456}}
Reviewed: {{ YYYY-MM-DD }}
Lenses: {{ names of the lenses applied, or "core only" }}

---

**Verdict**

{{ OPTION A - No gaps found }}
✅ No gaps found. Ready for final QA review.

{{ OPTION B - Gaps found }}
❌ {{ N }} gap(s) found (see below). Sending back to dev.

---

**Acceptance Criteria**

{{ One line per AC item: }}
✓ {{ AC item text - met }}
✗ {{ AC item text - not met, with brief reason }}

---

**Implementation**

{{ 2-4 sentence summary of what the PR(s) actually do. Write for a reader who has not seen the diff. Focus on the approach taken, not just what the ticket asked for. }}

---

**Tests**

{{ If no gaps: }}
No gaps found.

{{ If gaps found (one line per gap): }}
Gap: {{ Describe what is untested }} - `{{ file }}` - {{ Test that would close it }}.
{{ Repeat per gap }}

---

**Interfaces and Documentation**

{{ If the change touches no externally visible interface or user-facing behavior: }}
Not applicable - no interface or user-facing change.

{{ If no changes were needed and documentation is untouched: }}
No documentation changes required.

{{ If documentation was updated correctly by the dev: }}
Correct. Updated: {{ list files }}.

{{ If gaps found (one line per gap): }}
Gap: {{ What is missing or wrong in the documentation or contract }} - `{{ file }}` - {{ Change that would close it }}.
{{ Repeat per gap }}

---

**Other Findings**

{{ If no other findings: }}
None.

{{ If findings (one line per finding): }}
Gap: {{ Describe the implementation-level issue and why it matters }} - `{{ file }}` - {{ Change that would close it }}.
{{ Repeat per gap }}
