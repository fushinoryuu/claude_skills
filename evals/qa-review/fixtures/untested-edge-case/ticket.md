Key: GM-30
Type: Story
Status: In QA
Summary: Cap inventory stacks at 99

Description:
Picking up items has no limit, so a stack can grow without bound and break the item counter in the inventory screen. Add a way to put items into the inventory that stops a stack at 99. Items that do not fit must not disappear, so the caller needs to know how many were left over.

Acceptance criteria:
1. A new function adds items to the inventory.
2. A stack never holds more than 99 items.
3. The function returns how many items did not fit.
4. Adding zero items changes nothing, and a negative count is rejected.
5. The README describes the function.

Linked issues: none

Comments:
- Dev (2026-03-27): PR 61 is up for QA.
