Key: SHOP-14
Type: Story
Status: In QA
Summary: Let the storefront call the API from the browser

Description:
The storefront runs at `https://shop.example.test`, on another site than the API. The browser blocks its calls, and the shopper's sign-in cookie is not sent.

Acceptance criteria:
1. A browser call from the storefront can send the sign-in cookie and read the response.
2. A call that has no `Origin` header is not changed.
3. The README describes the cross-origin calls.

Linked issues: none

Comments:
- Dev (2026-03-20): PR 44 is up for QA.
