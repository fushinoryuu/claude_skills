import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / "skills" / "qa-review" / "assets"
TEMPLATES = ["initial-comment.md", "final-comment.md"]


def template_body(name: str) -> str:
    text = (ASSETS / name).read_text(encoding="utf-8")
    return text[text.index("## Template") :]


def template_rules(name: str) -> str:
    return (ASSETS / name).read_text(encoding="utf-8").split("## Template")[0]


def test_each_template_states_a_word_limit_in_its_rules():
    for name in TEMPLATES:
        assert re.search(r"\b\d+ words or fewer", template_rules(name)), name


def test_the_initial_limit_matches_the_one_the_evals_enforce():
    limit = int(re.search(r"(\d+) words or fewer", template_rules("initial-comment.md")).group(1))
    cases = (ROOT / "evals" / "qa-review" / "cases").glob("*.yaml")
    limits = {re.search(r"max_comment_words: (\d+)", c.read_text(encoding="utf-8")).group(1) for c in cases}
    assert limits == {str(limit)}


def test_headings_are_bold_markdown_not_single_asterisk_text():
    for name in TEMPLATES:
        for line in template_body(name).splitlines():
            assert not re.match(r"^\*[^*]", line), f"{name}: {line}"
        assert "**Verdict**" in template_body(name)


def test_lines_are_broken_with_plain_newlines_only():
    """Jira shows a plain line break as a line break, so trailing spaces and backslashes are not needed."""
    for name in TEMPLATES:
        body = template_body(name)
        for line in body.splitlines():
            assert line == line.rstrip(), f"{name}: trailing space in {line!r}"
            assert not line.endswith("\\"), f"{name}: backslash at the end of {line!r}"
        assert "\n\n\n" not in body, f"{name}: more than one blank line in a row"


def test_header_lines_and_acceptance_criteria_are_grouped_without_blank_lines():
    header = r"\*\*(Initial|Final) QA Review - .*\*\*\nPRs: .*\nReviewed: .*\nLenses: "
    for name in TEMPLATES:
        body = template_body(name)
        assert re.search(header, body), name
        assert "✓ {{ AC item text - met }}\n✗ {{ AC item text" in body, name
