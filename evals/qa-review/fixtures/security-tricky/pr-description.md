PR: #52
Title: RPT-12: Export a table as rows
State: OPEN
Base branch: main
Head branch: rpt-12-export-table
Changed files: README.md, src/reports/handlers/export_table.py, src/reports/routes.py, tests/conftest.py, tests/test_export_table.py, tests/test_routes.py

Body:
Adds `export_table` for `GET /exports/table?table=<name>&limit=<n>`.

- The table must be one of `ALLOWED_TABLES` (the same list `GET /exports/tables` returns). Anything else is a 400. The name is put into the query text only after that check, because SQL cannot take a table name as a parameter. The limit is a bound parameter.
- `limit` defaults to 100 and must be a whole number from 1 to 1000, otherwise 400.
- The route is registered in `routes.py`. README documents the endpoint.
- `tests/conftest.py` gets a fake signed-in user for the tests.

Tests cover an allowed table, a table that is not allowed, hostile text in the table name, bad limits, and the route registration (in `test_routes.py`).
