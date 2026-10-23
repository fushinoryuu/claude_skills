Key: WK-5
Type: Story
Status: In QA
Summary: Add pluralize to wordkit

Description:
Callers keep writing "1 items". Add a helper that writes a count with its word and only adds an "s" when the count is not one.

Acceptance criteria:
1. `pluralize(1, "item")` returns "1 item".
2. `pluralize(0, "item")` and any other count return the count followed by the plural word, for example "3 items".
3. The README documents the function.

Linked issues: none

Comments:
- Dev (2026-04-03): PR 4 is up for QA.
