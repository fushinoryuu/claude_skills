Key: ACC-6
Type: Story
Status: In QA
Summary: Let a new customer create an account

Description:
Customers can only be created by support today. Add an endpoint that creates an account from an email and a password.

Acceptance criteria:
1. `POST /accounts` with a JSON body containing `email` and `password` creates an account and returns 201 with its `id` and `email`.
2. The password is not stored in plain text.
3. A body without `email` or without `password` returns 400 with `{"error": "email and password are required"}`.
4. The README documents the new endpoint.

Linked issues: none

Comments:
- Dev (2026-03-16): PR 18 is up for QA.
