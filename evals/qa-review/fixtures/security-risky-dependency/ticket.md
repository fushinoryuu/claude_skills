Key: RPT-8
Type: Story
Status: In QA
Summary: Export the report as CSV

Description:
Finance wants to open the report in a spreadsheet. Add a CSV export of the report rows.

Acceptance criteria:
1. `to_csv(rows)` returns CSV text with the header `date,cents` and one line per row.
2. With no rows, it returns the header only.
3. The README describes the export.

Linked issues: none

Comments:
- Dev (2026-03-23): PR 9 is up for QA.
