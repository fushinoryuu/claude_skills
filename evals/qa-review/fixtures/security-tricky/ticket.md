Key: RPT-12
Type: Story
Status: In QA
Summary: Export the rows of a table

Description:
Finance wants the rows of a few tables as data. Add an endpoint that returns the rows of one table. Only the tables that `GET /exports/tables` lists may be exported.

Acceptance criteria:
1. `GET /exports/table?table=<name>` returns 200 with up to 100 rows of the table, and `limit` can lower or raise that up to 1000.
2. A table that is not on the list returns 400 with `{"error": "unknown table", "allowed": [...]}`.
3. A `limit` that is not a whole number from 1 to 1000 returns 400.
4. The README documents the new endpoint.

Linked issues: none

Comments:
- Dev (2026-03-27): PR 52 is up for QA.
