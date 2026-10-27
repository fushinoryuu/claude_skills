# Findings

The gaps found are reported twice in the session, never in the Jira comment (the comment is Markdown text and must not contain a code fence, see the comment templates):

- A **readable list** under `## Findings` in the final report (Step 12). Every review prints it.
- A **JSON block** after the list, only when the user ended the command with `json`. Tools and the eval runner read it, so its shape is fixed.

Both hold the same findings and use the same categories, files, severities and summaries. The rules for which gaps to list, and the fields, are the same for both.

## Readable list

Start with one line, `Lenses applied:`, followed by the lens names or `core only`. Then one line per finding, ranked most severe first, in this shape:

```
1. [medium] missing-tests - src/orders/service.py - cancel_order has no test for the already-cancelled case.
```

That is: a number, the severity in brackets, the category slug, the file, and the one-sentence summary, joined by ` - `. When there are no gaps, write `No gaps found.` after the `Lenses applied:` line. Do not use a table and do not repeat the Jira comment's wording of the verdict.

## JSON block (only with `json`)

Print this block after the readable list, and only when the command ended with `json`. Without it, print no JSON.

## Shape

One fenced `json` block holding one object:

```json
{
  "lenses_applied": [],
  "findings": [
    {
      "category": "missing-tests",
      "file": "src/orders/service.py",
      "severity": "medium",
      "summary": "cancel_order has no test for the already-cancelled case."
    }
  ]
}
```

- `lenses_applied` is the list of lens names used in Step 3. It is an empty list for a core-only review.
- `findings` is the list of gaps. It is an empty list when there are none.
- Print exactly one block. Use only the keys shown. Do not add `id`, `status`, `location`, `description` or `recommendation`.

## Fields of a finding

| Field      | Value                                                                                                                      |
| ---------- | -------------------------------------------------------------------------------------------------------------------------- |
| `category` | One slug from the table below. Use `other` only when none fits. Never invent a slug.                                       |
| `file`     | The path of the file the gap is about, as it appears in the diff. For missing tests, the source file that lacks the tests. |
| `severity` | `high`, `medium` or `low`, from the guide below.                                                                           |
| `summary`  | One sentence: what is wrong and why it matters. No line numbers.                                                           |

## Categories

| Slug                           | Use it when                                                                               |
| ------------------------------ | ----------------------------------------------------------------------------------------- |
| `missing-tests`                | New or changed behavior has no test at an appropriate level                               |
| `missing-edge-case-coverage`   | A test exists, but empty, maximum, invalid, duplicate or concurrent cases are not covered |
| `unmet-acceptance-criterion`   | An acceptance criterion is not implemented, or the code contradicts it                    |
| `missing-interface-doc-update` | An externally visible interface changed and its documentation did not                     |
| `missing-input-validation`     | Input from outside is used without being checked                                          |
| `missing-error-handling`       | A failure path (a failed call, bad data, an empty result) is not handled                  |
| `unsafe-data-change`           | A change to stored data or its format has no migration, backfill or recovery path         |
| `excessive-permissions`        | Access is granted more widely than the change needs                                       |
| `other`                        | A real gap that fits none of the above                                                    |

## Severity

- `high`: an acceptance criterion is not met, data could be lost or corrupted, or access is too wide.
- `medium`: new behavior is untested, or an interface change is undocumented.
- `low`: a minor gap that would not stop the ticket from being done.

## Which gaps to list

- List every gap that the Jira comment reports, whether it was sent back to the developer or fixed in the session.
- Do not list a gap marked "already fixed on the base branch".
- One finding per gap. Do not list the same gap twice.
- Acceptance criteria that were met are not findings.
