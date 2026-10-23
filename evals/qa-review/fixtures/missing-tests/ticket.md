Key: SLUG-7
Type: Story
Status: In QA
Summary: Add truncate_slug to slugkit

Description:
Callers need to fit a slug into a length limit, such as a database column or a URL segment, without cutting a word in half. Add a public `truncate_slug(slug, max_length)` function to the slugkit library.

Acceptance criteria:
1. A slug that is already at most `max_length` characters is returned unchanged.
2. A longer slug is cut at the last hyphen that fits, so no word is split.
3. A single word longer than `max_length` is cut at `max_length` characters.
4. The result never ends with a hyphen. A `max_length` below 1 raises `ValueError`.
5. The function is exported from the package and documented in the README.

Linked issues: none

Comments:
- Dev (2026-03-09): PR 15 is up for QA.
