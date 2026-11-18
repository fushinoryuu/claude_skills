Key: GW-4
Type: Story
Status: In QA
Summary: Accept bearer tokens at the gateway

Description:
Mobile clients cannot keep a session cookie. Let them sign in with a token that the auth service issued, sent in the `Authorization` header.

Acceptance criteria:
1. `user_from_token(token)` returns the user id and role for a token that the auth service issued.
2. A token that is not valid, or is missing the user id or the role, returns None.
3. The README describes the header and the claims.

Linked issues: none

Comments:
- Dev (2026-03-18): PR 27 is up for QA.
