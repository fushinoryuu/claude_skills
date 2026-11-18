PR: #18
Title: ACC-6: Add POST /accounts
State: OPEN
Base branch: main
Head branch: acc-6-signup
Changed files: README.md, src/accounts/handlers/signup.py, src/accounts/routes.py, tests/test_routes.py, tests/test_signup.py

Body:
Adds the `signup` handler for `POST /accounts`.

- It reads `email` and `password` from the body. A missing value gives 400.
- The password is hashed before it is stored. The response holds `id` and `email` only.
- The handler logs the request, to help us follow sign-ups while the feature is new.
- The route is registered in `routes.py`. README documents the endpoint.

Tests cover creating an account, the stored hash, the missing values, and the route registration (in `test_routes.py`).
