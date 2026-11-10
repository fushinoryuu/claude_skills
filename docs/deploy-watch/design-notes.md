# Deploy Watch: initial design notes

Early ideas for a new skill, `/deploy-watch`, that checks the health of a deployment from evidence before, during, and after a release. These are brainstorming notes, not a plan. A roadmap and its tickets come after these decisions are agreed. Tracked in Jira as QARS-17 (epic) and QARS-18 (these notes).

## What it is

A read-only skill that answers "is this deployment healthy?" from the evidence in the release tooling, and says so honestly when the evidence is not enough.

| Phase  | Question                      | Main evidence                                                                                                                      |
| ------ | ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Before | Is it safe to deploy now?     | Octopus Deploy (what is released, to where, what else is deploying), GitHub (the changes in the release), Datadog (open monitors)  |
| During | Is the rollout going well?    | Octopus Deploy (task and step status), Datadog (error rate, latency and monitors against the pre-deploy baseline)                  |
| After  | Did it work, and does it hold | Datadog (the same signals over a soak window), plus the release and its changes                                                    |

The output is a verdict (`healthy`, `degraded` or `unknown`) with the evidence behind it.

## Decisions so far

- **Read-only.** The services are live, probably production. The skill never deploys, rolls back, promotes, or mutes a monitor. It can recommend an action for a person to take. Acting may be added much later, behind explicit approval, and is not part of the first version.
- **Run by hand.** A person runs it on their own machine. It does not run in a pipeline for now: output is harder to see there, and a human should read the verdict.
- **Fixtures come from public API documentation.** There is no real deployment to copy. Every fixture is synthetic, built from the public API docs of the tools. No employer-specific names, URLs, or data anywhere in the repo.
- **Output goes to the terminal first.** A later step can write the result into a Confluence release document. The Atlassian MCP server the repo already expects has Confluence tools, so this needs no new connection.

## Principles carried over from `qa-review` and the Phase 3 plan

- **`unknown` is a first-class answer.** A missing metric, or a monitor that is quiet because nothing is reporting, must never read as healthy. This is the biggest risk in the skill.
- **Every claim cites evidence:** the monitor or query, and the time window.
- **Always compare to a baseline.** "5% errors" means nothing without the window before the deploy. The report states which baseline window it used.
- **Correlated, not caused.** A spike during a deploy is not necessarily caused by it. The report names other changes and incidents in the same window.
- **Scripts only for deterministic work:** window and baseline comparison, mapping a release to its changes. The model reads the evidence and writes the verdict.
- **Evals use fixtures with planted problems,** scored the same way as the other skills.

## Sketch of the skill

Nothing here is final.

```
skills/deploy-watch/
  SKILL.md                    workflow, modes, ground rules
  references/
    signals.md                what to check per phase, and what "bad" looks like
    verdict-rules.md          healthy / degraded / unknown, soak window, baseline rules
    sources/                  one file per tool: which calls to make, what the fields mean
  scripts/
    compare_windows.py        baseline versus current, from metric series in JSON
    release_changes.py        the changes between two releases
  assets/
    report-template.md
```

Usage idea: `/deploy-watch <before|during|after> <project> <environment> [release]`.

A config file in the repo being watched, `.claude/deploy-watch/config.yaml`, would map a service to its Octopus project, its Datadog monitors and tags, and its soak window. This is the same idea as the project patterns file in `qa-review`.

## Hard parts

1. **Evals without a live system.** Record API responses as fixtures (a deployment, a metric series, a monitor state) and plant the problems: error rate doubled after the deploy, a metric went silent, a flapping monitor, an unrelated incident in the same window, and a clean deployment.
2. **Causality.** See "Correlated, not caused" above.
3. **Size of the responses.** Monitoring APIs return a lot. Every call needs a narrow query, and the scripts should shrink the data before the model sees it.
4. **Which tool for GitHub.** The repo uses the `gh` CLI instead of a GitHub MCP server to save tokens. Decide whether this skill follows that rule.
5. **Where the tool access comes from.** Check whether each of the three tools has an MCP server or only a REST API, and what a person needs to authenticate. This decides the "Expected tools" section.

## Suggested first slice

Start with the `after` mode only. It has the clearest question and the clearest evidence, and `before` and `during` reuse the same comparison script.

## Open questions

- Which signals are in the first version: error rate and latency only, or also saturation and monitor state?
- How long is the default soak window, and is it set in the config or per run?
- What does the Confluence output look like: a new page, or a section added to an existing release page?
- Does a config file belong in the first version, or are the project and environment arguments enough?
- Name check: `deploy-watch` works for a skill that only observes. Keep it, or pick a name that covers a future "act" mode?

## Next steps

1. Review and agree these notes (QARS-18).
2. Check the three tools' public API docs and write down the calls and fields the first slice needs.
3. Write a roadmap in the style of the other phase docs, then file tickets under QARS-17.
