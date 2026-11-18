Key: NTF-5
Type: Story
Status: In QA
Summary: Send a welcome email through the mail provider

Description:
New customers should get a welcome email. We use the mail provider's HTTP API for this and not our own relay.

Acceptance criteria:
1. `send_welcome(http, email, name)` posts the email to the provider's API.
2. When the provider refuses the email, the function raises.
3. The README says where the provider's address is set.

Linked issues: none

Comments:
- Dev (2026-03-13): PR 12 is up for QA.
