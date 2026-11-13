# Baseline eval for `qa-review`

This records how the `qa-review` skill scores on its eval set at the end of Phase 1, on three Claude models. The skill is written and tuned against Claude Sonnet 5.5 (the eval runner's default). The other two models are measured so a reader knows what to expect, and the skill text is not tuned for them. How the eval works is in [eval-format.md](eval-format.md).

## Setup

- Date: 2026-11-13, after QARS-4, QARS-5, QARS-6 and QARS-10 were merged.
- Skill text: as merged in pull request #25. `SKILL.md` is 305 lines.
- The eval set has 15 cases and each ran 3 times (45 runs per model). A case passes when most of its runs pass.
- All three runs sent the same prompt: the input, cache write and cache read token counts are identical, so the skill text did not change between them.

The commands, run from the repository root with `ANTHROPIC_API_KEY` set:

```
uv run python -m evals.runner --skill qa-review --runs 3 --jobs 8
uv run python -m evals.runner --skill qa-review --runs 3 --jobs 8 --model claude-haiku-5-5
uv run python -m evals.runner --skill qa-review --runs 3 --jobs 8 --model claude-opus-5-5
```

## Results

| Model                       | Cases passed | Recall | False-positive rate | Input tokens | Cache write | Cache read | Output tokens |
| --------------------------- | ------------ | ------ | ------------------- | ------------ | ----------- | ---------- | ------------- |
| `claude-sonnet-5-5` (tuned) | 15 of 15     | 1.00   | 0.00                | 86,481       | 42,187      | 930,323    | 209,666       |
| `claude-haiku-5-5`          | 14 of 15     | 1.00   | 0.67                | 86,481       | 42,187      | 930,323    | 275,428       |
| `claude-opus-5-5`           | 14 of 15     | 1.00   | 0.22                | 86,481       | 42,187      | 930,323    | 206,123       |

- **Recall** is the share of planted defects the skill reported. It is 1.00 for every model: none of them missed a planted gap.
- **False-positive rate** is the share of runs, on the clean and tricky cases, that reported anything that was not expected. Lower is better.
- Input, cache write and cache read are the same for every model because the prompt is the same. Output tokens differ. Compare the full input as the sum of the three input counts.

### Cases that did not pass

Both failures are over-reporting. The skill found every planted defect, then reported more other gaps than the case allows.

| Case                           | Sonnet | Haiku  | Opus   | What the extra findings were                                                                                                                                                                                                                                   |
| ------------------------------ | ------ | ------ | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `vague-criteria-01`            | 3 of 3 | 0 of 3 | 1 of 3 | The case expects no gaps and allows at most 1 finding. Haiku reported 2 or 3 low-severity findings on every run, and Opus reported 2 on two runs. Sonnet reported none. They look plausible: for example an unchecked input type, or an untested error branch. |
| `criterion-not-implemented-01` | 3 of 3 | 3 of 3 | 2 of 3 | The case allows 4 findings. Opus reported 6 on one run, one in each of six categories. Sonnet and Haiku reported at most 4 on any run, which is exactly the limit, so this case has little room on any model.                                                  |

Every other case passed 3 of 3 on all three models.

## What the eval does not cover

The eval sends the skill text and a fixture to the model in one API call. So it does not test:

- **Tool use.** The model cannot run `gh`, read files or call Jira, so it never fetches anything itself. The fixtures supply the diff and the ticket.
- **The scripts.** `suggest_lenses.py`, `missing_tests.py`, `changed_interfaces.py` and `openapi_changed.py` are not run. Their output is part of the fixture where a case needs it, and the scripts have their own unit tests.
- **The Jira connection.** The comment is scored as text and nothing is posted.
- **Other providers.** The runner calls only Anthropic models. The skill is not checked on other models, or in other tools such as VS Code Copilot (tracked as QARS-22).
- **A long review.** The fixtures are small pull requests. A large diff is not covered.

A live run of `/qa-review` on a real pull request covers what the eval cannot. One was done for each extra model.

## Live checks

One `/qa-review initial QARS-25 23` run per extra model, on 2026-11-13 with effort `high`, to check tool use, the scripts and Jira. Pull request #23 (ticket QARS-25) is already merged. It rewords Step 12 of `SKILL.md` and adds three tests. Claude Sonnet reviewed it earlier and found no gaps (Jira comments 10100 and 10101).

| Model              | Jira comment               | What it showed                                                                                                                                                                                                                                                 |
| ------------------ | -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `claude-haiku-5-5` | 10106 (2nd Initial Review) | Passed. It read the ticket and the pull request, posted a comment in the template with core lenses only, and numbered the title after the earlier reviews. It found one low-severity gap.                                                                      |
| `claude-opus-5-5`  | 10107 (3rd Initial Review) | Passed. Same steps and the same gap, worded more precisely. It also noticed the 2nd review and checked whether anything had changed since. Its comment says the 13 tests in the changed test file pass and that it did not re-run the full `uv run poe check`. |

The gap both found: the Summary test in `tests/unit/qa_review/test_comment_templates.py` checks "only these items" and "Add no other bullets" but not the clause that limits "commands run" to commands. This is a real, low-severity gap, and Sonnet missed it twice. So on this pull request the extra findings were useful, not noise.

How far to trust this:

- **Not a blind comparison.** The skill reads earlier comments on the ticket, so both runs saw Sonnet's "no gaps" comments, and Opus also saw Haiku's. Opus agreeing with Haiku is not independent. Both still reported a gap against that earlier verdict.
- **Not recorded.** The two session reports were not kept, so whether each run used the scripts, and any tool errors that did not change the result, are not recorded here.
- **One small pull request, in `initial` mode.** `final` mode (which can write tests) and a large diff were not checked.

## Reading the results

- Sonnet is the model to use. It is the only one the skill is tuned against, and it is the only one that passes every case.
- Haiku and Opus find every planted gap, so a gap is not lost by using them. They report more extra low-severity gaps, which makes a review longer to read. Haiku does it the most.
- Extra findings are not always noise. On the live check, both Haiku and Opus found a real low-severity gap that Sonnet had missed.
- These are three runs per case on one date. A single 2 of 3 is a signal, not a measurement, and the numbers move a little from one run of the eval to the next.
- Making the skill quieter on Haiku and Opus is future work and was not done here, because the skill is tuned only against Sonnet.
