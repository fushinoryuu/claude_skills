PR: #40
Title: OR-17: Add POST /orders
State: OPEN
Base branch: main
Head branch: or-17-create-order
Changed files: README.md, src/orders/handlers/create_order.py, src/orders/routes.py, tests/test_create_order.py

Body:
Adds the `create_order` handler for `POST /orders`.

- It reads `sku` and `quantity` from the body, stores the order, and returns 201 with the order. The route is registered in `routes.py`.
- README documents the endpoint.

Tests cover creating an order, reading it back from the store, and the route registration.
