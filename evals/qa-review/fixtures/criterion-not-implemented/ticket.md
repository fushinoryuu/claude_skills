Key: TC-14
Type: Story
Status: In QA
Summary: Let cache entries expire

Description:
The cache keeps entries forever, so stale values pile up. Add an optional time to live (ttl), in seconds, so entries can expire.

Acceptance criteria:
1. An entry is not returned once its ttl has passed, and it is removed when it is read.
2. The cache takes a default ttl in its constructor. Without one, entries never expire.
3. `set` takes an optional `ttl` that overrides the cache default for that entry.
4. `len(cache)` does not count entries that have expired.

Linked issues: none

Comments:
- Dev (2026-03-18): PR 33 is up for QA.
