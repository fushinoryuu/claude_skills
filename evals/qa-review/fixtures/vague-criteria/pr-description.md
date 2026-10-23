PR: #28
Title: NK-31: Skip notifications during quiet hours
State: OPEN
Base branch: main
Head branch: nk-31-quiet-hours
Changed files: README.md, src/notifykit/__init__.py, src/notifykit/core.py, tests/test_core.py

Body:
Adds quiet hours to notifykit.

- Each user has `quiet_start` and `quiet_end`, defaulting to 22:00 and 07:00.
- The check uses the user's own time zone. A window that starts later than it ends runs past midnight.
- `send` skips the message during quiet hours and returns `False`.
- `send` takes an optional `now` so tests do not depend on the clock.
- README has a new Quiet hours section.

Tests cover the default window, the start and end boundaries, per-user hours, time zones, an empty window, and `send` skipping.
