PR: #35
Title: BILL-11: Let a customer open and search their receipts
State: OPEN
Base branch: main
Head branch: bill-11-receipts
Changed files: README.md, src/billing/handlers/get_receipt.py, src/billing/handlers/search_receipts.py, src/billing/routes.py, tests/test_get_receipt.py, tests/test_routes.py, tests/test_search_receipts.py

Body:
Adds two handlers and their routes.

- `get_receipt` for `GET /receipts/<id>` returns the signed-in customer's receipt. A receipt that belongs to someone else gives the same 404 as a missing one.
- `search_receipts` for `GET /receipts?q=<text>` returns the customer's receipts whose memo contains the text. The query is parameterized, it only reads the customer's rows, `%` and `_` in `q` are escaped so they match as plain text, and `q` is required and limited to 100 characters.
- Both routes need a signed-in user: they are not in `PUBLIC`, and the dispatcher (not changed here, with its own tests in `tests/test_dispatch.py`) refuses a call with no signed-in user to any route that is not in `PUBLIC`. README documents the endpoints.

Tests cover an own receipt, another customer's receipt, an unknown id, the search scope, `%` and `_`, a quote in the search text, a missing or empty `q`, `q` at and over the limit, and the route registration (in `test_routes.py`).
