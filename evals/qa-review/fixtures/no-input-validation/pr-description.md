PR: #40
Title: OR-17: Add POST /orders
State: OPEN
Base branch: main
Head branch: or-17-create-order
Changed files: README.md, src/orders/handlers/create_order.py, tests/test_create_order.py

Body:
Adds the `create_order` handler for `POST /orders`.

- It reads `sku` and `quantity` from the body, stores the order, and returns 201 with the order.
- README documents the endpoint.

Tests cover creating an order and reading it back from the store.
