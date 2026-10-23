PR: #61
Title: GM-30: Add add_item with a stack limit of 99
State: OPEN
Base branch: main
Head branch: gm-30-stack-limit
Changed files: README.md, src/inventory/__init__.py, src/inventory/items.py, tests/test_items.py

Body:
Adds `add_item(inventory, item, count, limit=99)`.

- It adds as many items as fit under the limit and returns how many did not.
- A count of zero changes nothing, and a negative count raises `ValueError`.
- README describes it.

Tests cover starting a new stack and adding to an existing one.
