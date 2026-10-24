PR: #52
Title: SH-31: Cancel an order
State: OPEN
Base branch: main
Head branch: sh-31-cancel-order
Changed files: openapi.yaml, src/shop/routes/orders.py

Body:
Adds `cancel_order` for `DELETE /orders/{id}`.

- It removes the order and returns 204, or returns 404 with the usual error body when the id is unknown.
- `openapi.yaml` documents the `delete` operation with its 204 and 404 responses.

The existing tests still pass.
