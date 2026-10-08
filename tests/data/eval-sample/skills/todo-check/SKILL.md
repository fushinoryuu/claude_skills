---
name: todo-check
description: Sample skill used to test the eval runner. Flags leftover TODO comments added in a diff.
---

# TODO check

Read the diff in `pr.diff`. For every added line (starting with `+`) that contains a `TODO` comment, report one finding with category `leftover-todo`, the file it is in, severity `low`, and a one-line summary.

If no added line contains a `TODO`, report no findings. Do not report anything else.

End your answer with the findings block:

```json
{
  "findings": [
    {"category": "leftover-todo", "file": "src/app.py", "severity": "low", "summary": "TODO left in new code."}
  ]
}
```

See [references/notes.md](references/notes.md) for what counts as a TODO.
