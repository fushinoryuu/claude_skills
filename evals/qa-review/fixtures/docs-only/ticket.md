Key: TT-8
Type: Task
Status: In QA
Summary: Fix the Python version in the install guide and add troubleshooting

Description:
tasktrack needs Python 3.11 or newer, but the install guide and the README say 3.10. People on 3.10 hit confusing errors. Correct the version, and add a short troubleshooting section to the install guide for the two most common problems: the command not being found after install, and a Python that is too old.

Acceptance criteria:
1. The install guide and the README both say Python 3.11 or newer.
2. The install guide has a troubleshooting section that covers "command not found" and "requires a different Python".

Linked issues: none

Comments:
- Dev (2026-03-16): PR 9 is up for QA. Docs only.
