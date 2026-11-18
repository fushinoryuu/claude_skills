PR: #23
Title: INV-9: Add GET /invoices/<id>
State: OPEN
Base branch: main
Head branch: inv-9-get-invoice
Changed files: README.md, src/billing/handlers/get_invoice.py, src/billing/routes.py, tests/test_get_invoice.py, tests/test_routes.py

Body:
Adds the `get_invoice` handler for `GET /invoices/<id>`.

- It looks the invoice up by id and returns it, or 404 `{"error": "invoice not found"}`.
- The route is registered in `routes.py`. It is not in `PUBLIC`, so a signed-in user is required like for every other route.
- README documents the endpoint.

Tests cover reading an invoice, an unknown id, and the route registration (in `test_routes.py`).
