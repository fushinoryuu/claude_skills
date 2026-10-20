## What and why

<!-- One or two sentences: what this PR changes and the reason. Link the roadmap item or issue if there is one. -->

## How it works

<!-- A short walkthrough for a reviewer who has not seen the code: what runs, what reads what, and where to start reading. -->

## How to see it work

<!-- Commands a reviewer can run, with what they should see. For example `uv run poe check`. -->

## Checks

- [ ] `uv run poe check` passes (lint, table check, tests)
- [ ] If a skill changed: its eval kit is updated (cases, fixtures, trigger prompts), and `uv run poe eval --skill <name> --dry-run` shows the prompts I expect
- [ ] README and `docs/` are updated where commands or behavior changed
- [ ] Roadmap: the finished item is ticked in its phase doc and the matching item in `docs/ROADMAP.md`
- [ ] No secrets, real tickets, or customer data in code, fixtures, or docs

## Not in this PR

<!-- Related work left for a later PR, so the reviewer knows what to skip. Write "Nothing" if there is none. -->
