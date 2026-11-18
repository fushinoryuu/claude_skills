Key: BILL-11
Type: Story
Status: In QA
Summary: Let a customer open and search their receipts

Description:
Customers ask support for copies of their receipts. Let a signed-in customer open a receipt by its id and search their receipts by memo text.

Acceptance criteria:
1. `GET /receipts/<id>` returns 200 with the receipt when it belongs to the signed-in customer, and 404 with `{"error": "receipt not found"}` otherwise.
2. `GET /receipts/search?q=<text>` returns 200 with the customer's receipts whose memo contains the text.
3. A `q` longer than 100 characters returns 400 with `{"error": "q is too long"}`.
4. The README documents both endpoints.

Linked issues: none

Comments:
- Dev (2026-03-25): PR 35 is up for QA.
