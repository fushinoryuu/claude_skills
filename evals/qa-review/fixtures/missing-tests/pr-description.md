PR: #15
Title: SLUG-7: Add truncate_slug
State: OPEN
Base branch: main
Head branch: slug-7-truncate-slug
Changed files: README.md, src/slugkit/__init__.py, src/slugkit/text.py

Body:
Adds `truncate_slug(slug, max_length)` to slugkit.

- It returns the slug unchanged when it already fits.
- Otherwise it cuts at the last hyphen that fits, so words are not split. A single long word is cut at `max_length`.
- The result never ends with a hyphen, and a `max_length` below 1 raises `ValueError`.
- Exported from the package and documented in the README.

Checked by hand in a REPL with a few slugs.
