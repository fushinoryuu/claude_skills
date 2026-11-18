PR: #31
Title: CAT-14: Add product search
State: OPEN
Base branch: main
Head branch: cat-14-product-search
Changed files: README.md, src/catalog/handlers/search_products.py, src/catalog/routes.py, tests/test_routes.py, tests/test_search_products.py

Body:
Adds `search_products` for `GET /products/search?q=<text>`.

- It returns the products whose name contains the text, ordered by name. No match gives an empty list.
- The route is registered in `routes.py`.
- README documents the endpoint.

Tests cover a search with matches, a search with no match, and the route registration (in `test_routes.py`).
