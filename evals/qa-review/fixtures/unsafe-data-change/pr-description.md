PR: #18
Title: OD-21: Split customer_name into first_name and last_name
State: OPEN
Base branch: main
Head branch: od-21-split-name
Changed files: README.md, migrations/003_split_customer_name.sql, tests/test_migrate.py

Body:
Adds migration 003, which gives `orders` separate `first_name` and `last_name` columns and removes `customer_name`.

- README table updated.
- Tests check that all three migrations apply to a new database, that applying twice changes nothing, and that `customer_name` is gone.

Checked by running the migrations on a new database.
