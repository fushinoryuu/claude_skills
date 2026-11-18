Key: INV-9
Type: Story
Status: In QA
Summary: Let a customer open an invoice by its id

Description:
Customers get a link to an invoice in their billing email. Add an endpoint that returns the invoice for that id.

Acceptance criteria:
1. `GET /invoices/<id>` returns 200 with the invoice (`id`, `customer_id`, `total_cents` and `lines`).
2. An id that does not exist returns 404 with `{"error": "invoice not found"}`.
3. The README documents the new endpoint.

Linked issues: none

Comments:
- Dev (2026-03-09): PR 23 is up for QA.
