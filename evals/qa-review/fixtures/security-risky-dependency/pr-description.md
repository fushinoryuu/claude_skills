PR: #9
Title: RPT-8: Export the report as CSV
State: OPEN
Base branch: main
Head branch: rpt-8-csv-export
Changed files: README.md, requirements.txt, src/reports/csv_export.py, tests/test_csv_export.py

Body:
Adds `to_csv` in `src/reports/csv_export.py`.

- It writes the rows as CSV text with the header `date,cents`.
- It uses the `fastcsv` package, which is added to `requirements.txt`.
- README describes the export.

Tests cover a report with rows and an empty report.
