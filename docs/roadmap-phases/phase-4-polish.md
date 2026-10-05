# Phase 4: Polish

Make the repo easy to understand, easy to try, and easy to talk about. A reviewer or hiring manager should grasp what it does in a couple of minutes and see it working.

## Goals

- Every skill is documented with a real example.
- A short demo shows the skills in action.
- The README tells the story and links to everything else.
- The project is summarized in resume-ready form.

## Deliverables

| Deliverable | Location |
|---|---|
| Per-skill docs | `docs/skills/<skill>.md` |
| Eval results summary | `docs/eval-results.md` |
| Demo asset (GIF or transcript) | `docs/demo/` and linked from `README.md` |
| Final README | `README.md` |
| Resume bullet(s) | kept outside the repo, drafted here for reference |

## Tasks

### 1. Per-skill documentation

For each skill (`pr-review` including its extensions, `failure-analysis`, `defect-drafting`, `regression-selection`), write `docs/skills/<skill>.md` with:

- [ ] **Purpose:** two or three sentences on the problem it solves.
- [ ] **When it triggers:** a few example prompts.
- [ ] **Inputs:** what it needs and where it gets them (MCP server, pasted text, file).
- [ ] **Outputs:** what the report looks like, with the structured findings block explained.
- [ ] **Example run:** a real input and the real output, trimmed for length. Use fixture data so it is reproducible.
- [ ] **Scripts:** what each does, its inputs and outputs, how to run it standalone.
- [ ] **Limitations:** what it does not do and where it is likely to be wrong.
- [ ] **How it is tested:** the fixtures, planted defects, and eval results.

Keep each doc to roughly one page. Link to the SKILL.md and references rather than repeating them.

### 2. Eval results summary

- [ ] Run the full eval suite several times per case (for example 5 runs).
- [ ] Record per-skill recall, false-positive rate, and trigger accuracy in `docs/eval-results.md`.
- [ ] Record the model used and the date, since results change with the model.
- [ ] Note known weak spots honestly. A repo that shows what fails and why is more credible than one that shows only passes.
- [ ] Include the command to reproduce the numbers.

### 3. Demo

Pick one format and do it well:

- **Terminal or chat recording (GIF):** one scenario, under a minute, showing a PR review that catches a planted defect.
- **Annotated transcript:** the prompt, the output, and short callouts on what the skill did and why.

Suggested scenario: a PR with a missing unit test and an undocumented endpoint, reviewed against its ticket, followed by a failure-analysis run on a failing test report. This shows two skills and the handoff idea.

- [ ] Script the demo so it is repeatable.
- [ ] Use fixture data only, with no real company, ticket, or credential information anywhere in the recording.
- [ ] Embed in the README near the top.

### 4. README final pass

- [ ] One-paragraph summary at the top: what the repo is and who it is for.
- [ ] Demo directly below the summary.
- [ ] Skill table: name, one-line purpose, link to its doc.
- [ ] Quick start: install instructions, required MCP servers, and how to invoke each skill.
- [ ] Expected tools section from Phase 0, kept current.
- [ ] Testing section: how to run unit, structure, and eval suites.
- [ ] Design notes: why MCP instead of custom adapters, why scripts only for deterministic work, why evals use planted defects. These show engineering judgment.
- [ ] Roadmap and contributing notes, if any.
- [ ] CI badge and license.

### 5. Repo hygiene

- [ ] Run a secrets scan and confirm no tokens, internal URLs, or company-specific details exist in fixtures or history.
- [ ] Confirm fixtures are fully synthetic.
- [ ] Check licensing choices for anything copied or adapted.
- [ ] Remove dead files, stale TODOs, and unused scripts.
- [ ] Pin the repo description and topics on GitHub.
- [ ] Verify a fresh clone follows the README successfully.

### 6. Resume and interview material

Draft a few bullets and revise to fit the resume. Examples of the shape (adjust the specifics to what was actually built and measured):

- Built a multi-skill QA automation toolkit for AI coding agents covering PR review, failure triage, defect drafting, and regression test selection, with an eval harness using planted-defect fixtures and CI.
- Designed deterministic scripts for diff analysis, OpenAPI breaking-change detection, and test-to-module mapping, with unit tests running in CI.
- Measured skill quality with repeated eval runs, tracking recall and false-positive rate per skill.

Also prepare short answers for likely interview questions:

- [ ] Why use MCP servers instead of custom API adapters?
- [ ] How do you test something non-deterministic?
- [ ] What did the evals show that surprised you?
- [ ] How would you roll this out to a team of engineers?
- [ ] Where does it fail, and how would you improve it?

## Acceptance criteria

- A stranger can read the README, watch the demo, and run one skill against a fixture in under ten minutes.
- Every claim in the README and resume bullets is backed by something in the repo (a test, an eval result, or a script).
- The repo contains no sensitive or company-specific content.

## Risks and notes

- **Overclaiming.** Only cite metrics you actually measured, with the model and date.
- **Stale docs.** Examples copied from output go out of date when skills change. Generate example output from the eval runner where possible, or note the date.
- **Scope creep.** Polish is the last phase. If the earlier phases are incomplete, ship fewer skills with better docs instead of more skills with thin ones.
