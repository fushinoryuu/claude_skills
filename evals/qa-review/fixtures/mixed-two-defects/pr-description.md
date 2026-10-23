PR: #22
Title: PK-9: Add apply_discount
State: OPEN
Base branch: main
Head branch: pk-9-discount
Changed files: src/pricekit/__init__.py, src/pricekit/discount.py

Body:
Adds `apply_discount(price_cents, percent)`.

- It works in whole cents with integer arithmetic, so there are no float rounding surprises.
- It rounds to the nearest cent, with halves rounding up.
- A percent outside 0 to 100 raises `ValueError`.
- Exported from the package.

Checked by hand in a REPL.
