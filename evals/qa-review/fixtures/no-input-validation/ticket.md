Key: OR-17
Type: Story
Status: In QA
Summary: Add an endpoint to create an order

Description:
Orders can only be read today. Add a `POST /orders` endpoint that creates an order from a SKU and a quantity.

Acceptance criteria:
1. `POST /orders` with a JSON body containing `sku` and `quantity` creates an order and returns 201 with the new order, including its `id`.
2. The created order can be read back with `GET /orders/<id>`.
3. The README documents the new endpoint.

Linked issues: none

Comments:
- Dev (2026-03-30): PR 40 is up for QA.
