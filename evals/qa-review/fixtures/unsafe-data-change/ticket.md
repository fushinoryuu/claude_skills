Key: OD-21
Type: Story
Status: In QA
Summary: Store the customer's first and last name separately

Description:
Support needs to sort and search orders by last name, but the orders table keeps the whole name in one column. Store the first name and the last name in separate columns instead.

Acceptance criteria:
1. The orders table has `first_name` and `last_name` columns.
2. The old `customer_name` column is removed.
3. The README lists the new columns.

Linked issues: none

Comments:
- Dev (2026-03-25): PR 18 is up for QA.
