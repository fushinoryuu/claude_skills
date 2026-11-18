PR: #27
Title: GW-4: Accept bearer tokens
State: OPEN
Base branch: main
Head branch: gw-4-bearer-tokens
Changed files: README.md, src/gateway/auth/tokens.py, tests/test_tokens.py

Body:
Adds `user_from_token` in `src/gateway/auth/tokens.py`.

- It reads the user id (`sub`) and the `role` from the token's claims, and returns `{"id", "role"}`.
- A token without `sub` or `role`, or text that is not a token, gives None.
- README describes the header and the claims.

Tests cover a good token, a token without a role, and text that is not a token.
