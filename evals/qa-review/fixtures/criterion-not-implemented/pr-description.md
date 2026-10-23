PR: #33
Title: TC-14: Add ttl to tinycache entries
State: OPEN
Base branch: main
Head branch: tc-14-ttl
Changed files: README.md, src/tinycache/cache.py, tests/test_cache.py

Body:
Adds an optional time to live to `Cache`.

- `Cache(ttl=...)` sets a default. Without it entries never expire.
- `set(key, value, ttl=...)` overrides the default for one entry.
- An expired entry is not returned and is removed when it is read.
- The clock is injectable so tests do not sleep.
- README has a new Expiry section.

Tests cover expiry, no ttl, the default ttl, and the per-entry override.
