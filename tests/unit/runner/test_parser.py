import pytest

from evals.runner.parser import (
    ParseError,
    extract_comment,
    parse_findings,
    parse_lenses_applied,
)

BLOCK = '```json\n{"findings": [{"category": "a", "file": "x.py"}]}\n```'


def test_parses_block_at_end_of_output():
    text = f"Here is my review.\n\n{BLOCK}\n"
    assert parse_findings(text) == [{"category": "a", "file": "x.py"}]


def test_empty_findings_list_is_valid():
    assert parse_findings('```json\n{"findings": []}\n```') == []


def test_uses_last_block_and_ignores_earlier_json():
    text = '```json\n{"findings": [{"category": "old"}]}\n```\nmore text\n' + BLOCK
    assert parse_findings(text) == [{"category": "a", "file": "x.py"}]


def test_skips_trailing_json_without_findings():
    text = BLOCK + '\n```json\n{"note": "unrelated"}\n```'
    assert parse_findings(text) == [{"category": "a", "file": "x.py"}]


def test_skips_invalid_json_and_falls_back_to_earlier_block():
    text = BLOCK + "\n```json\n{not json}\n```"
    assert parse_findings(text) == [{"category": "a", "file": "x.py"}]


def test_fence_label_is_case_insensitive():
    assert parse_findings('```JSON\n{"findings": []}\n```') == []


def test_windows_line_endings():
    assert parse_findings('```json\r\n{"findings": []}\r\n```') == []


@pytest.mark.parametrize(
    "text",
    [
        "",
        "no block here",
        "```\n{\"findings\": []}\n```",  # fence without json label
        "```json\n[1, 2]\n```",  # not an object
        '```json\n{"findings": "none"}\n```',  # findings not a list
        '```json\n{"findings": ["a"]}\n```',  # findings not objects
        "```json\n{broken\n```",
    ],
)
def test_raises_parse_error(text):
    with pytest.raises(ParseError):
        parse_findings(text)


def test_lenses_applied_comes_from_the_same_block_as_the_findings():
    text = '```json\n{"lenses_applied": ["x"], "findings": []}\n```\n\n```json\n{"lenses_applied": ["service"], "findings": []}\n```'
    assert parse_lenses_applied(text) == ["service"]


def test_empty_lenses_applied_means_core_only():
    assert parse_lenses_applied('```json\n{"lenses_applied": [], "findings": []}\n```') == []


@pytest.mark.parametrize("extra", ["", ', "lenses_applied": "service"', ', "lenses_applied": [1]'])
def test_missing_or_malformed_lenses_applied_is_none(extra):
    assert parse_lenses_applied('```json\n{"findings": []' + extra + "}\n```") is None


# --- the drafted comment ---

START = r"^[^\w\n]*(?:\d+(?:st|nd|rd|th) )?(?:Initial|Final) QA Review - "

OUTPUT = """Here is my review. I will post it as the Initial QA Review - X after you agree.

---

Initial QA Review - T-1
PRs: #1

---

*Verdict*
Fine.

---

## Summary

- done

```json
{"findings": []}
```
"""


def test_comment_runs_from_its_title_to_the_next_heading_without_trailing_rules():
    assert extract_comment(OUTPUT, START) == "Initial QA Review - T-1\nPRs: #1\n\n---\n\n*Verdict*\nFine."


def test_comment_title_may_be_bold_or_numbered():
    assert extract_comment("**2nd Initial QA Review - T-1**\n\nbody", START) == "**2nd Initial QA Review - T-1**\n\nbody"
    assert extract_comment("**Final QA Review - T-1**\nbody\n```json\n{}\n```", START) == "**Final QA Review - T-1**\nbody"


def test_comment_uses_the_last_title_and_ignores_mentions_inside_a_line():
    text = "Initial QA Review - A\nold draft\n\n## Revised\n\nInitial QA Review - B\nnew draft"
    assert extract_comment(text, START) == "Initial QA Review - B\nnew draft"


def test_no_comment_when_no_line_starts_with_the_title():
    assert extract_comment("I will post the Initial QA Review - X later.", START) is None
