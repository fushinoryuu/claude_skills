# QA Review Skill

Runs a structured QA review session for a Jira ticket + one or more PRs. This could serve as the formal QA verification step for a given team/project: when all gaps are resolved and you are satisfied, mark the ticket Done.

The skill is project-agnostic. It applies to any code or feature a QA engineer would review, whatever the stack. A universal core checklist always applies, and optional lenses add stack-specific checks on top.

## Initial setup

This skill assumes that you have the following tools already set up and fully authenticated:

- GitHub CLI (`gh`). The skill needs it to read the pull requests.
- Atlassian MCP with write access to post comments (setup is in the repository README). Without it, the skill asks you to paste the ticket text and gives you the finished comment to post by hand.
- Python 3.9 or newer, as `python3`. Check with `python3 --version`. The skill runs small scripts that suggest which lenses fit the change and which changed source files have no matching test change. They use only the standard library, so there is nothing to install. If a script cannot run, the skill says so and does that step by hand, which is slower and less consistent.
- Set effort level to `high` before running skill

On Windows, `python3` can be a Microsoft Store shortcut and not Python: running it only prints "Python was not found" and offers the Store. If `python3 --version` does that, install Python from the Store or from [python.org](https://www.python.org/downloads/), then open a new terminal and check again.

Optional: put a `.claude/qa-review/patterns.md` file in the repo you are reviewing, with your team's known recurring gaps under an **Implementation Gaps** heading. The skill reads it as a checklist and never edits it. At the end of a review it suggests patterns worth adding, for you to commit.

### Progress list

The skill shows a list of its 12 steps and where it is. It uses the session's task tool when there is one. In some Claude Code builds that tool is off by default; set `CLAUDE_CODE_ENABLE_TODO_TOOLS` to `1` once under `env` in `~/.claude/settings.json` to turn it on:

```json
{
  "env": {
    "CLAUDE_CODE_ENABLE_TODO_TOOLS": "1"
  }
}
```

Without a task tool, the skill prints the 12 steps once and a `Step N of 12` line as each step starts.

### If `git fetch` fails with an SSL certificate error

On Windows, antivirus software that scans HTTPS traffic replaces GitHub's certificate with its own. `gh` and browsers use the Windows certificate store, which trusts it, but Git for Windows does not, so `git fetch` fails with an SSL certificate error. Either fix works:

- Add an exception for `github.com` and `*.github.com` in the antivirus software's HTTPS scanning settings.
- Or make Git use the Windows certificate store: `git config --global http.sslBackend schannel`.

## Review modes

There are two modes, used at different points in the ticket lifecycle:

| Mode      | When to use                              | Functional/Integration tests | On gaps found                                                     |
| --------- | ---------------------------------------- | ---------------------------- | ----------------------------------------------------------------- |
| `initial` | First time the ticket reaches QA         | Skipped                      | Report all gaps, send back to dev                                 |
| `final`   | After dev has addressed initial feedback | Evaluated and implemented    | Fix what can be fixed in session without touching production code |

## Usage

```
/qa-review <MODE> <JIRA-TICKET> <PR#> [PR#2 PR#3 ...] [json]
```

End the command with `json` to also get the findings as a JSON block at the end of the report. Without it you get a readable list only.

**Examples:**

```
/qa-review initial ABC-123 456
/qa-review final ABC-123 456
/qa-review final ABC-123 456 789
/qa-review final ABC-123 456 json
```

## What each mode does

**`initial` review:**

1. Load any prior review memory for this ticket if it exists
2. Fetch the Jira ticket, its linked tickets, and the PR diffs
3. Understand the change and select lenses
4. Check acceptance criteria coverage and the implementation
5. Identify test coverage gaps
6. _(Functional/Integration tests skipped)_
7. Check interfaces and documentation
8. Sanity-check each gap against the current base branch
9. _(Nothing is fixed in `initial` mode, every open gap is reported)_
10. Post the initial review comment to the Jira ticket (after you confirm any derived acceptance criteria), and stop

**`final` review:**

1. Load any prior review memory for this ticket if it exists - cross-references gaps from the initial review
2. Fetch the Jira ticket, its linked tickets, and the PR diffs
3. Understand the change and select lenses
4. Check acceptance criteria coverage and the implementation; verify initial review gaps are closed and identify any new gaps
5. Check test coverage
6. Check for missing functional/integration tests
7. Check interfaces and documentation
8. Sanity-check each gap against the current base branch
9. Fix the test and documentation gaps that step 8 confirmed are still open, where possible without touching production code. This includes writing the functional/integration tests
10. Post the final review comment to the Jira ticket (after you confirm any derived acceptance criteria). If gaps remain for dev, the comment is another initial-style review instead.

## What you get

- **A Jira comment**, in Markdown (bold headings, related lines grouped together), using the template for the mode. It aims for 750 words for an `initial` review and 1000 for a `final` one, and never drops a gap to get there: a review with many gaps can run longer. It has the verdict, one line per acceptance criterion, a summary of the change, and the gaps by section. It is posted without asking, because the skill only adds comments and a comment can be edited or deleted in Jira. The report at the end shows the comment as posted. Two cases still stop for you: if the ticket has no acceptance criteria, the skill derives them from the description, marks them "(derived from the description)", and asks you to confirm them before posting; and if the ticket was pasted or the Atlassian tool is missing, it gives you the comment to post by hand.
- **A report** at the end of the session: a summary, the comment as posted, and the findings as a readable list (a severity, a category, a file and a one-sentence summary for each gap). It never goes to Jira. Add `json` to the command to also get the same findings as a JSON block for tools and evals. The format is in [references/output-format.md](references/output-format.md).

The state of a pull request (open, merged or closed) never changes the verdict. The Jira ticket tracks the work, so a PR that is already merged is reviewed like any other and the comment does not mention it.

## What it checks

### The core checklist

[references/qa-core.md](references/qa-core.md) applies to every review. Each item is applied only when it is relevant to the change.

**Requirements and implementation**

- Every acceptance criterion is implemented, and unclear requirements are flagged instead of assumed.
- Fixes and new rules are applied consistently across similar places.
- Failure behavior, regression risk, data and state, security basics, observability and testability.

**Test coverage**

- New and changed behavior has tests at an appropriate level, including failure paths and edge cases.
- Tests assert real outcomes.

**Higher-level tests** _(final mode only)_

- Behavior the acceptance criteria describe, which lower-level tests cannot fully verify, is covered in the project's designated test location.
- If for some reason a functional/integration test can't be created at this moment, a `.todo` stub is added to keep track of missing tests in source control.
- Test data created by a test is cleaned up afterwards.

**Interfaces and documentation**

- A changed externally visible interface (an API, command-line flags, a file format, a schema, a config option) has its documentation updated.
- User-facing and operator-facing changes are documented.

### Lenses

A lens is an optional file of extra checks for one kind of change. The review is complete without any lens, and a lens only ever adds checks the core does not already cover.

Each lens opens with an `applies_when` block that says which changed files, or which kind of change, it is for. The skill reads only the lenses that fit the change, and the comment lists them on its `Lenses:` line (or says "core only"). A script (`scripts/suggest_lenses.py`) gives the first suggestion by matching the changed files against each lens, and the skill makes the final call. You can also name a lens when you run the skill, or ask for the core only.

The lenses included in this folder are examples:

| Lens                                      | Adds checks for                                                                                      |
| ----------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| [service](references/lenses/service.md)   | Server-side request handling, data access, and migrations (validation, authorization, idempotency)   |
| [api-spec](references/lenses/api-spec.md) | Projects that document an HTTP API in an OpenAPI/Swagger spec (spec updated, new surface documented) |

To add a lens for your own stack, see [references/lenses/README.md](references/lenses/README.md). A team can also keep its own lenses in `.claude/qa-review/lenses/` in the repo being reviewed, in the same format. A lens there replaces a bundled lens with the same name.

### Test patterns

Step 5 starts with a script (`scripts/missing_tests.py`) that lists changed source files with no matching test file in the change. It compares file names and folders, it never reads a test, and the skill treats its output as a signal. Folders tell same-named files apart (`tests/b/test_utils.py` does not cover `src/a/utils.py`). A same-name test in a differently named folder, such as `scripts/` and `qa_review/`, is not counted as a match, but when no other changed file accounts for it the script lists it as a likely match (`likely_test_elsewhere`) so the reviewer reads it before reporting a gap. Out of the box it knows the usual test names for Python, JavaScript and TypeScript, Java, Kotlin, Go, Ruby, C#, PHP and Swift. If your project names or places its tests differently, commit a file named `.claude/qa-review/test-patterns` in the repo being reviewed. The script reads it on every run:

```
# One pattern per line. {name} is the source file's name without its extension.
spec/{name}_spec.rb
checks/{name}.check.py

# Add source extensions the script does not know.
source-ext: .gleam, .res
```

A pattern is a glob: `*` stays inside one folder, `**` crosses folders, and `?` is one character. A pattern without `{name}` only marks files as tests. To run the script by hand, use `--test-pattern GLOB` (repeatable) to add a pattern, `--no-default-patterns` to use only your own, `--source-ext .EXT` to add a source extension, and `--project-patterns FILE` to read the patterns from another file. `--help` lists the output.
