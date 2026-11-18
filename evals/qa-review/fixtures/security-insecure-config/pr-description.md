PR: #44
Title: SHOP-14: Let the storefront call the API from the browser
State: OPEN
Base branch: main
Head branch: shop-14-cors
Changed files: README.md, src/shop/middleware/cors.py, tests/test_cors.py

Body:
Adds `add_cors_headers` in `src/shop/middleware/cors.py`.

- When a request has an `Origin` header, the response allows that origin and the sign-in cookie, and sets `Vary: Origin`.
- A request with no `Origin` header gets no extra headers.
- README describes the cross-origin calls.

Tests cover the storefront call and a call without an origin.
