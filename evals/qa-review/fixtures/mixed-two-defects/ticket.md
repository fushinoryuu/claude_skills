Key: PK-9
Type: Story
Status: In QA
Summary: Add a discount helper to pricekit

Description:
Shops that use pricekit all write the same percentage-discount code. Add a public helper that takes a percentage off a price in cents.

Acceptance criteria:
1. `apply_discount(price_cents, percent)` returns the discounted price in cents, rounded to the nearest cent.
2. A percent outside 0 to 100 raises `ValueError`.
3. The function is importable from `pricekit`.

Linked issues: none

Comments:
- Dev (2026-04-01): PR 22 is up for QA.
