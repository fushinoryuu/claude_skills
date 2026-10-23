Key: RI-4
Type: Story
Status: In QA
Summary: Let the nightly exporter upload reports

Description:
The nightly exporter job writes the daily reports file. It needs permission to upload objects to the `reports-prod` bucket. Add an access policy for it, next to the existing reader policy.

Acceptance criteria:
1. A new policy file lets the exporter upload objects to the reports bucket.
2. The policy format is checked by the existing policy tests.
3. The README lists the new policy.

Linked issues: none

Comments:
- Dev (2026-03-26): PR 5 is up for QA.
