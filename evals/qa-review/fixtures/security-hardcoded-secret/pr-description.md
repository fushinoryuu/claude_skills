PR: #12
Title: NTF-5: Send a welcome email through the mail provider
State: OPEN
Base branch: main
Head branch: ntf-5-welcome-email
Changed files: README.md, src/notify/settings.py, src/notify/welcome.py, tests/test_settings.py, tests/test_welcome.py

Body:
Adds `send_welcome` in `welcome.py`. It posts the welcome email to the mail provider's HTTP API.

- The provider's address and key are in `settings.py`, next to the SMTP settings.
- A refused email raises, so the caller can retry.
- README mentions the provider address.

Tests cover the request that is sent, a refused email, and the provider address.
