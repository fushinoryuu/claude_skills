PR: #5
Title: RI-4: Add the report uploader policy
State: OPEN
Base branch: main
Head branch: ri-4-uploader-policy
Changed files: README.md, infra/iam/report-uploader.json, tests/test_policies.py

Body:
Adds `infra/iam/report-uploader.json` for the nightly exporter.

- The policy allows the exporter to upload reports.
- The existing format test covers the new file, and a new test checks that it allows `s3:PutObject`.
- README table updated.
