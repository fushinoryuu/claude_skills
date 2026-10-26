Key: SH-31
Type: Story
Status: In QA
Summary: Let a customer cancel an order

Description:
Customers can read an order but cannot cancel one. Add a `DELETE /orders/{id}` operation that cancels an order, and document it in the API spec.

Acceptance criteria:
1. `DELETE /orders/{id}` cancels an existing order and returns 204 with no body.
2. Cancelling an order that does not exist returns 404 with `{"error": "order not found"}`.
3. `openapi.yaml` documents the new operation and its responses.

Linked issues: none

Comments:
- Dev (2026-04-06): PR 52 is up for QA.
