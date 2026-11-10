# Deploy Watch: initial design notes

Early ideas for a new skill, `/deploy-watch`, that checks the health of a deployment from evidence before, during, and after a release. These are brainstorming notes, not a plan. A roadmap and its tickets come after these decisions are agreed. Tracked in Jira as QARS-17 (epic) and QARS-18 (these notes).

## What it is

A read-only skill that answers "is this deployment healthy?" from the evidence in the release tooling, and says so honestly when the evidence is not enough.

| Phase  | Question                      | Main evidence                                                                                                                     |
| ------ | ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Before | Is it safe to deploy now?     | Octopus Deploy (what is released, to where, what else is deploying), GitHub (the changes in the release), Datadog (open monitors) |
| During | Is the rollout going well?    | Octopus Deploy (task and step status), Datadog (error rate, latency and monitors against the pre-deploy baseline)                 |
| After  | Did it work, and does it hold | Datadog (the same signals over a soak window), plus the release and its changes                                                   |

The output is a verdict (`healthy`, `degraded` or `unknown`) with the evidence behind it.

## The use case behind it

A weekly deployment of 3 to 5 services, deployed one after the other, which takes about 30 minutes in total. Sometimes a hotfix deploys just one of those services. Other teams' deployments will differ, so the skill must not assume a fixed number or order of services. Watching a deployment means watching several services at once, and a hotfix is the same thing with one service.

## Decisions so far

- **First-version signals:** error rate, latency, and monitor state.
- **Several services per release.** One run watches a list of services (see "Watching several services" below). One service is just a list of one.
- **A config file is part of the first version,** to map each service to its tools (see the sketch below).
- **The name stays `deploy-watch`.** A future "act" mode does not need to be in the name.
- **Confluence output (later) is a comment on the existing release document,** never an edit of its body, so the release doc is not changed or damaged.
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

## Watching several services

- **A release is a list of services,** each with its own state: not started, deploying, deployed, failed. The services deploy one after the other, so at any moment some are done and some are not.
- **Each service gets its own verdict and baseline.** The baseline window for a service ends when its deployment starts, not when the release starts. A service deployed 20 minutes into the release must not be compared to a baseline that already includes the earlier services.
- **One overall verdict on top.** The release is `healthy` only if every service is. One `degraded` service makes the release `degraded`, and a service that cannot be judged makes the overall result at best `unknown`. The report lists the services in deploy order.
- **Interactions between services.** A fault in a service that is not deploying can still come from one that just did (for example a downstream error rate). The report names the services deployed in the preceding window next to any degraded service.
- **A skill run is a snapshot, not a 30-minute watcher.** To follow a rollout, the person re-runs it, or runs it on a repeat (the harness's `/loop`). Each run reads the current Octopus state, so it knows which services are done. Decide later whether the skill should help with this by saying when to check again.

## Soak window

The time after a service finishes deploying during which the skill keeps looking before it calls the service healthy. Some problems appear late: a cache warming up, a queue backing up, memory climbing, or a scheduled job running ten minutes later. Healthy right after the deploy and healthy 30 minutes later are different claims.

Proposal: a default of 30 minutes, set per service in the config (a database-backed service may need longer than a stateless one) and overridable per run, for example for a hotfix. Until a service's soak window has passed, its best verdict is `healthy so far`, not `healthy`. Needs the user's agreement.

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

A config file in the repo being watched, `.claude/deploy-watch/config.yaml`, maps each service to its Octopus project, its Datadog monitors and tags, and its soak window. This is the same idea as the project patterns file in `qa-review`. Roughly:

```yaml
services:
  orders:
    octopus_project: "Orders"
    datadog: { service: "orders", monitors: ["orders-error-rate"] }
    soak_minutes: 30
  payments:
    octopus_project: "Payments"
    datadog: { service: "payments", monitors: ["payments-latency"] }
    soak_minutes: 45
```

The usage idea changes to `/deploy-watch <before|during|after> <environment> [service ...]`. With no service named, it watches every service in the release that Octopus reports for that environment, falling back to the whole config.

## Hard parts

1. **Evals without a live system.** Record API responses as fixtures (a deployment, a metric series, a monitor state) and plant the problems: error rate doubled after the deploy, a metric went silent, a flapping monitor, an unrelated incident in the same window, and a clean deployment.
2. **Causality.** See "Correlated, not caused" above.
3. **Size of the responses.** Monitoring APIs return a lot. Every call needs a narrow query, and the scripts should shrink the data before the model sees it.
4. **Which tool for GitHub.** The repo uses the `gh` CLI instead of a GitHub MCP server to save tokens. Decide whether this skill follows that rule.
5. **Where the tool access comes from.** Check whether each of the three tools has an MCP server or only a REST API, and what a person needs to authenticate. This decides the "Expected tools" section.

## Suggested first slice

Start with the `after` mode only, over several services. It has the clearest question and the clearest evidence, and `before` and `during` reuse the same comparison script. Because the per-service state matters for a release in progress, the first slice also reads which services Octopus reports as done.

## Open questions

- Agree the soak window proposal above (30 minutes by default, per service in the config, overridable per run)?
- Is "healthy so far" a fourth verdict, or a note on `healthy`?
- Can the Atlassian MCP server add a comment to a Confluence page (and not only create or update pages)? Check this against the tool list before promising the Confluence output.
- How does the skill find the baseline for a service: a fixed window before the deployment start (for example the previous hour), or the same time of day on the previous week? The weekly deploy may make "same time last week" a good second baseline, but it needs the data to exist.
- Where does the person say which release or deployment is meant: by Octopus release version, or "the latest deployment to this environment"?

## Next steps

1. Review and agree these notes (QARS-18).
2. Check the three tools' public API docs and write down the calls and fields the first slice needs.
3. Write a roadmap in the style of the other phase docs, then file tickets under QARS-17.
