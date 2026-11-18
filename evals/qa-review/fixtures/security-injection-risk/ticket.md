Key: CAT-14
Type: Story
Status: In QA
Summary: Search the catalog by product name

Description:
Shoppers need to find a product without browsing every page. Add a search endpoint that takes a piece of text.

Acceptance criteria:
1. `GET /products/search?q=<text>` returns 200 with the products whose name contains the text, ordered by name.
2. When nothing matches, it returns 200 with an empty list.
3. The README documents the new endpoint.

Linked issues: none

Comments:
- Dev (2026-03-11): PR 31 is up for QA.
