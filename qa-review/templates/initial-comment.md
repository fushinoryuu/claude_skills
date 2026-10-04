# QA Review Initial Review Comment Template

Use this template when posting the Jira comment for an `initial` mode review. Fill in every `{{ placeholder }`, pick the correct verdict, and delete the unused verdict option before posting.

---

## Template

````markdown
## QA Review (initial)

**PRs:** {{ #PR_NUMBER, #PR_NUMBER }}
**Reviewed:** {{ YYYY-MM-DD }}

**Verdict:** Send back to dev - {{ N }} gap(s) found
**Verdict:** No gaps found - ready for final review

### Acceptance criteria

| # | Criterion | Status | Evidence |
| - | --------- | ------ | -------- |
| AC1 | {{ short criterion text }} | Covered / Partial / Missing | {{ file:line or test name }} |

### Gaps

Each gap has an id so the final review can reference it. Write "None" if there are no gaps.

**Unit tests**
- **G1** - {{ what is untested }} (`{{ file }}` - `{{ symbol }}`). Needed: {{ test that would close it }}.

**API spec** _(write "Not applicable - no API contract in this project" if so)_
- **G2** - {{ what is missing or wrong in the spec }} (`{{ spec file }}`). Needed: {{ change that would close it }}.

**Other**
- **G3** - {{ anything outside the categories above }}

### Not evaluated

- Functional/integration tests - skipped in the initial review, evaluated in the final review.

### Next steps

{{ one or two sentences: what dev should address before requesting the final review }}
````
