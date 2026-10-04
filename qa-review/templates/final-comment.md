# QA Review Final Review Comment Template

Use this template when posting the Jira comment for an `final` mode review. Fill in every `{{ placeholder }`, pick the correct verdict, and delete the unused verdict option before posting.

---

## Template

````markdown
## QA Review (final)

**PRs:** {{ #PR_NUMBER, #PR_NUMBER }}
**Reviewed:** {{ YYYY-MM-DD }}

**Verdict:** Ready to mark Done - no open gaps
**Verdict:** Gaps remain - {{ N }} open gap(s) need dev attention

### Acceptance criteria

| # | Criterion | Status | Evidence |
| - | --------- | ------ | -------- |
| AC1 | {{ short criterion text }} | Covered / Partial / Missing | {{ file:line or test name }} |

### Initial review gaps

Write "No initial review on record" if there was no prior review for this ticket.

| Gap | Description | Status | Note |
| --- | ----------- | ------ | ---- |
| G1 | {{ gap from the initial review }} | Closed / Still open / Closed differently | {{ how it was closed, or what is still missing }} |

### New gaps

Write "None" if there are no new gaps.

- **G{{ n }}** - {{ what is wrong or missing }} (`{{ file }}`). Needed: {{ change that would close it }}.

### Unit tests

{{ summary of coverage, and any gaps fixed in this session; "No gaps" if none }}

### Functional/integration tests

- **Added:** {{ test files and what behavior they cover }}
- **`.todo` stubs:** {{ stub files and why the test could not be written now, or "None" }}
- **Cleanup:** {{ confirmation that every setup that creates test data has matching teardown, or the exception }}
- **Result:** {{ command run and pass/fail count }}

### API spec

{{ spec changes made, validation command and result (e.g. 0 errors), or "Not applicable - no API contract in this project" }}

### Changes made in this session

Files were edited in the working tree and are **not committed**.

- `{{ file }}` - {{ what changed }}

### Remaining work for dev

{{ list of open gaps that need production code changes, or "None" }}
````
