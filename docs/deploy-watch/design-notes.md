# Deploy Watch: initial design notes

Early ideas for a new skill, `/deploy-watch`, that checks the health of a deployment from evidence before, during, and after a release. These are brainstorming notes, not a plan. A roadmap and its tickets come after these decisions are agreed. Tracked in Jira as QARS-17 (epic) and QARS-18 (these notes).

## What it is

A read-only skill that answers "is this deployment healthy?" from the evidence in the release tooling, and says so honestly when the evidence is not enough.

The three rows below are stages of one continuous watch, not three commands. The person starts the skill a little before the planned deployment (for a 10:00 deployment, at 9:45). It checks that the environment looks healthy, notices each service's deployment starting, follows it, and keeps watching until the last soak window ends.

| Phase  | Question                      | Main evidence                                                                                                                            |
| ------ | ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Before | Is it safe to deploy now?     | The deployment source (what is released, to where, what else is deploying), GitHub (the changes in the release), Datadog (open monitors) |
| During | Is the rollout going well?    | The deployment source (run and step status), Datadog (error rate, latency and monitors against the pre-deploy baseline)                  |
| After  | Did it work, and does it hold | Datadog (the same signals over a soak window), plus the release and its changes                                                          |

The output is a verdict (`healthy`, `degraded` or `unknown`) with the evidence behind it.

**Deployment source:** where the skill learns that a service is deploying, done, or failed. There are two, and one release can mix them:

- **Octopus Deploy:** a deployment of a release to an environment.
- **GitHub Actions:** a deploy workflow run (or a GitHub deployment) for a repository.

Everything after "the deployment says it is done" (the signals, baselines, soak windows and verdicts) is the same for both. Only the part that reads the state differs, so that part sits behind one small interface in the scripts.

## The use case behind it

A weekly deployment of 3 to 5 services, deployed one after the other, which takes about 30 minutes in total. Sometimes a hotfix deploys just one of those services. Other teams' deployments will differ, so the skill must not assume a fixed number or order of services. Watching a deployment means watching several services at once, and a hotfix is the same thing with one service.

## Decisions so far

- **First-version signals:** error rate, latency, and monitor state.
- **Several services per release.** One run watches a list of services (see "Watching several services" below). One service is just a list of one.
- **A config file is part of the first version,** to map each service to its tools (see the sketch below).
- **Scripts call the tools' REST APIs and shrink the data before the model sees it.** The repo has no rule for or against adapters any more: each skill picks MCP, a CLI or a script by token cost (see "Cost"). `qa-review` is unchanged. The phase 1 and phase 4 docs were updated to say so.
- **The watch mode is in the first version.** The skill has no point without it.
- **Skills should also work in VS Code Copilot,** not only in Claude Code (see "Working on more than one platform").
- **Cost is a design goal.** Gate and watch mode for polling, rules in scripts, a token budget per eval case, and evals run only when needed.
- **Soak window:** 30 minutes by default, and a service can override it in the config.
- **`healthy so far` is a note, not a fourth verdict.** The verdicts stay `healthy`, `degraded` and `unknown`. A service still inside its soak window reads `healthy (soak ends 14:35)`.
- **No `before|during|after` argument.** One command follows the whole rollout. The person starts it a few minutes before the deployment, and the `before` check is the first stage of the watch (see "Baseline").
- **Baseline:** the last 1 to 4 hours before a service's deployment starts, overridable in the config. There is no "same time last week" baseline.
- **The planned release is known in advance,** because CI prepares it. The skill takes it as input, preferably from the Confluence release document (see "Knowing what is about to deploy").
- **For GitHub Actions, a deployment is the workflow run** named in the config.
- **The name stays `deploy-watch`.** A future "act" mode does not need to be in the name.
- **Confluence output (later) is a comment on the existing release document,** never an edit of its body, so the release doc is not changed or damaged.
- **Read-only.** The services are live, probably production. The skill never deploys, rolls back, promotes, or mutes a monitor. It can recommend an action for a person to take. Acting may be added much later, behind explicit approval, and is not part of the first version.
- **Run by hand.** A person runs it on their own machine. It does not run in a pipeline for now: output is harder to see there, and a human should read the verdict.
- **Fixtures come from public API documentation.** There is no real deployment to copy. Every fixture is synthetic, built from the public API docs of the tools. No employer-specific names, URLs, or data anywhere in the repo.
- **Output goes to the terminal first.** A later step can write the result into a Confluence release document. The Atlassian MCP server the repo already expects can do this with no new connection: checked on 2026-11-11, `createConfluenceComment` adds a footer comment to a page (Markdown body, at most 4096 characters), `updateConfluenceComment` edits a comment, and `listConfluenceComments` reads them. So the skill can comment on the release page and never edit its body. The 4096-character limit means the comment must be a short summary: the overall verdict, a line per service, and a link to the details.

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
- **The state comes from each service's deployment source on every check** (Octopus Deploy or GitHub Actions, and a release can mix them), so a check always knows which services are done, with no memory of earlier runs. The watch mode (see "Cost") repeats the check until something changes, so one command follows the whole rollout.

## Soak window

The time after a service finishes deploying during which the skill keeps looking before it calls the service healthy. Some problems appear late: a cache warming up, a queue backing up, memory climbing, or a scheduled job running ten minutes later. Healthy right after the deploy and healthy 30 minutes later are different claims.

The default is 30 minutes. A service can override it in the config (a database-backed service may need longer than a stateless one). Until a service's soak window has passed, its line reads `healthy (soak ends 14:35)`, as a note on `healthy` and not as a separate verdict.

## Baseline

The signals from before a service's deployment, which the signals after it are compared to. The window is the last 1 to 4 hours, with a default of 2 hours (a proposal, change it if another length suits your services), set in the config as a default and per service. It ends when that service's deployment starts. There is no "same time last week" baseline: it would complicate the skill for little gain.

The baseline needs time before the deployment, so the person starts the skill a few minutes ahead of it. While waiting, the skill does the old `before` check: it reads the signals for the look-back window and the monitors' state right now, and says whether the environment looks healthy to deploy into (or `degraded` or `unknown`, with the reason). The skill is read-only and never blocks a deployment. It tells the person, who decides.

Each service then moves through waiting, deploying, soaking and done, and the report shows where each one is.

## Knowing what is about to deploy

CI prepares the release in advance, so what is about to go out is known before the deployment starts, whether it goes through GitHub Actions or Octopus. The skill takes that planned release as input: the services expected, and their versions or artifacts. Sources, in order of preference:

1. The release document in Confluence, which lists the release artifacts. The skill reads it through the Atlassian MCP server, from a page given to it.
2. The command's arguments.
3. The config (every service in it).

With a planned release the skill can also compare what actually deploys with what was planned, and report a service that was not deployed, one deployed that was not planned, or a version that differs.

Usage idea: `/deploy-watch <environment> [release document]`.

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
    fetch_summary.py          call the APIs, print one compact summary per service (the gate lives here)
    watch_release.py          poll on its own, exit on a meaningful change or when every soak window is over
  assets/
    report-template.md
```

A config file in the repo being watched, `.claude/deploy-watch/config.yaml`, maps each service to its deployment source (an Octopus project, or a GitHub repository and deploy workflow), its Datadog monitors and tags, and its soak window. This is the same idea as the project patterns file in `qa-review`. Roughly:

```yaml
defaults:
  soak_minutes: 30
  baseline_hours: 2
services:
  orders:
    deploy: { source: octopus, project: "Orders" }
    datadog: { service: "orders", monitors: ["orders-error-rate"] }
    baseline_hours: 1
  payments:
    deploy: { source: github_actions, repo: "example-org/payments", workflow: "deploy.yml" }
    datadog: { service: "payments", monitors: ["payments-latency"] }
    soak_minutes: 45
```

The usage idea is `/deploy-watch <environment> [release document]`. The services come from the planned release (see "Knowing what is about to deploy"), falling back to the whole config. A hotfix is a planned release with one service. A service entry that sets neither value uses the `defaults`.

## Cost: tokens and eval spend

Token cost is a design goal from the start, not something to tune later. Three things multiply it: several services per run, repeated checks during a 30-minute rollout, and monitoring APIs that return a lot of data. The same approach that keeps `qa-review` cheap applies here: scripts do the heavy reading, the model does the judgment.

### Decision: scripts call the APIs and shrink the data

The repo no longer has a "use an MCP server instead of a custom adapter" rule. For `deploy-watch`, standard-library Python scripts call the tools' REST APIs directly and print a compact summary. The model never sees a raw metric series, deployment history, or monitor list.

- **Credentials:** read-only keys, taken from environment variables, never written to a file, a log, or the report. Each tool's page in `references/sources/` says which permission is enough.
- **No raw responses in context.** A script prints one summary per service: signal, baseline p50 and p95, current p50 and p95, change, monitor state, and a status flag. That is a few hundred tokens per service.
- **Rules live in the script.** A threshold such as "error rate more than double the baseline" is deterministic, so the script flags it. The model spends its tokens on the ambiguous cases, on correlating services, and on writing the report. This also makes a smaller model a candidate for the judgment step, which the evals can confirm because the runner records the model used.
- **Budgets in the config:** a cap on points per series, log lines, and monitors per service, keeping the top N by severity.
- **Expected tools** then lists the three services' APIs and their keys, plus the Atlassian MCP server only for the later Confluence step.

### Polling: a check that costs almost nothing

During a rollout, most checks find nothing new. Two ways to keep that cheap:

1. **A gate in the script.** The script saves its last summary locally and compares the new one to it. If nothing meaningful changed (no service started or finished, no threshold crossed, no monitor changed state), it prints `no change` and the model has nothing to do.
2. **A watch mode, so nobody has to re-run it.** `watch_release.py` loops on its own with `time.sleep`, polls every interval (for example 60 seconds), and exits when something meaningful changes or when every service's soak window has passed. While it waits it costs no tokens. Where the host can run a command in the background and wake the session when it exits (Claude Code), one slash command covers the whole rollout. Elsewhere it runs in slices of `--max-wait` (see "Working on more than one platform"), or in a terminal window with the result brought back to the agent. It needs the person's machine to stay on for the duration, and the keys in its environment.

The model is therefore called once per meaningful change, not once per interval.

### Keep the prompt cheap too

- `SKILL.md` stays short, with detail in `references/` that is read only when a step needs it.
- The stable text (instructions) comes first and the changing data last, so prompt caching applies.
- Reports are short: the verdict and the evidence per service, not a narrative.

### Keep the eval spend low

Evals call the real model and cost money, so they run only when a change needs them, not on every edit. Applying what `qa-review` taught:

- Script behavior is covered by unit tests, which are free. Most of the logic (windows, baselines, thresholds, the gate) is in scripts, so most changes need no eval run.
- Evals run with the existing speed-ups: `--jobs`, prompt caching, `--tag` and `--case`, to run only the cases a change can affect. A full run is for the end of a ticket that changed skill text.
- Fixtures hold large raw API responses, as recorded by the scripts' tests, so the shrinking is tested without the model.
- Each case carries a token budget, in the same way `max_comment_words` guards comment length. A change that makes the skill read raw data then fails.
- Record the tokens and cost of every full run in the PR description, as for `qa-review`.

### Rough size (a guess, to be measured)

A check with a change, over 5 services: about 10 to 15k input and 1 to 2k output tokens. A check with no change: under 1k. These are targets, to be replaced by measured numbers from the first fixtures.

## Working on more than one platform

The goal is that a skill in this repo works in Claude Code and in VS Code Copilot with no changes to its files. Checked against the [VS Code Agent Skills docs](https://code.visualstudio.com/docs/agent-customization/agent-skills) (Copilot reads the same skill format):

- **Same format.** A skill is a folder with a `SKILL.md`, plus optional scripts, templates and references. VS Code reads project skills from `.github/skills/`, `.claude/skills/` and `.agents/skills/`, and personal skills from `~/.copilot/skills/`, `~/.claude/skills/` and `~/.agents/skills/`. `.claude/skills/` is the one location both tools read, so the install instructions keep using it.
- **Frontmatter that works in both:** `name` (lowercase letters, numbers and hyphens, and it must match the folder name), `description`, `argument-hint`, and `disable-model-invocation`. `user-invocable` exists in VS Code too. `context: fork` is experimental there, and is not used.
- **Referenced files load when linked.** VS Code loads only the files the instructions reference, by a path relative to `SKILL.md`. That matches how `references/` already works.

### Where the two tools differ (from the docs, and not tested yet)

| Area               | Claude Code today                                                      | What to do in `deploy-watch`                                                                                                 |
| ------------------ | ---------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Skill folder path  | `${CLAUDE_SKILL_DIR}` is filled in when the skill loads                | The VS Code page documents no such variable. Refer to scripts by a path relative to the skill, and check what VS Code does   |
| Tool names         | MCP tools are named `mcp__<server>__<tool>`                            | The VS Code names differ. Describe each need in words and keep one "Expected tools" table with the name on each platform     |
| Arguments          | `$ARGUMENTS` is filled in with what follows the command                | The VS Code page says only that extra context can follow the command. Have the skill read its arguments from the user's text |
| Progress list      | A task tool such as `TodoWrite`                                        | Keep the tool-neutral rule `qa-review` already has (use the session's task tool, otherwise print the steps)                  |
| Ending the session | `/compact` command                                                     | Say what to keep in plain words, with the command as the Claude Code form                                                    |
| Background command | A command can run in the background and wake the session when it exits | Not documented for Copilot. See the time limit below                                                                         |

### Rules for the new skill

- Use only the frontmatter listed above, and name the folder exactly as `name`.
- Scripts must run from any terminal with plain `python3` and no Claude-specific environment. The skill passes them every path as an argument, so a script never needs the skill folder variable.
- The watch mode must work without the host's background-command feature. A command that waits 30 minutes can exceed a tool call's time limit, so `watch_release.py` takes `--max-wait` and exits with `still watching` after that time, having saved its state. The agent then runs it again, which costs one call and no model reasoning. Where background commands exist, the same script just runs with a long `--max-wait`.
- `SKILL.md` stays in plain Markdown instructions. Anything Claude-specific is marked as such and has a neutral fallback.
- Evals use the Anthropic API, so they only test the skill under Claude. Use in Copilot is checked by hand, once per skill, and the result goes in the skill's README. The unit tests of the scripts are platform-independent.

`qa-review` has the same points (`${CLAUDE_SKILL_DIR}` in Step 3, the `mcp__atlassian__*` names in Steps 2 and 10, `$ARGUMENTS`, the `/compact` message). Checking it in VS Code and fixing what differs is a separate piece of work, not part of this one.

## Hard parts

1. **Evals without a live system.** Record API responses as fixtures (a deployment, a metric series, a monitor state) and plant the problems: error rate doubled after the deploy, a metric went silent, a flapping monitor, an unrelated incident in the same window, and a clean deployment.
2. **Causality.** See "Correlated, not caused" above.
3. **Size of the responses.** See "Cost" above.
4. **Credentials.** Scripts that call the APIs handle keys. They must use read-only keys, and never print them or write them anywhere.
5. **Request limits.** The tools' APIs have rate limits. A watch mode that polls every minute for 5 services must stay well inside them, so check the documented limits for each.
6. **What each tool's API offers.** Check each tool's public API docs for the calls and fields the first slice needs, and for any required plan or permission. This decides the "Expected tools" section.
7. **What "done" means for a GitHub Actions deployment.** A workflow run can finish while the deployment is still waiting for an approval, or can have several jobs of which only one deploys. Decide whether the skill reads the workflow run, a specific job, or the GitHub deployment status for an environment, and what it reports when a run is waiting. The Octopus equivalent (a task's state) is simpler.
8. **Two sources, one meaning.** The Octopus and GitHub Actions states (queued, running, succeeded, failed, cancelled, waiting) must map to the same few states in the scripts, with a fixture for each source.

## Suggested first slice

The first version follows a rollout from the first service starting to the last soak window ending, over several services, with the watch mode. Without the watch mode the skill has no point, so it is in. That covers all three stages: the check before the deployment (the baseline and the environment's state), the rollout, and the soak. All three use the same comparison script. The first slice reads which services their deployment source (Octopus or GitHub Actions) reports as started and done, and applies each service's soak window.

## Open questions

- What does the release document in Confluence look like (a table, a list of artifacts with versions), and how does the skill read it cheaply? Reading a whole page costs tokens, so it should fetch only the part that lists the artifacts. The real document cannot be copied into the repo, so the fixtures need a synthetic example in the same shape.
- How long does the skill wait for a deployment to start before it gives up (for example 60 minutes after it was started), and what does it report then?
- Is 2 hours a good default look-back for the baseline? It is a proposal.
- What does the skill report when the environment looks unhealthy before the deployment has started? It cannot stop the deployment, so the proposal is a clear `degraded` result at the top of the report, with the signals that caused it.
- Does a service that deploys through GitHub Actions wait for a manual approval? The workflow run would show `running` or `waiting` while nothing is deploying yet. The proposal is to report `waiting for approval` when the run says so. (See hard part 7.)

## Next steps

1. Review and agree these notes (QARS-18).
2. Check the three tools' public API docs and write down the calls and fields the first slice needs.
3. Write a roadmap in the style of the other phase docs, then file tickets under QARS-17.
