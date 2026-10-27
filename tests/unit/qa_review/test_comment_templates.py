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


def template_limit(name: str) -> int:
    return int(re.search(r"(\d+) words or fewer", template_rules(name)).group(1))


def test_each_case_enforces_the_limit_of_the_template_for_its_mode():
    limits = {"initial": template_limit("initial-comment.md"), "final": template_limit("final-comment.md")}
    cases = list((ROOT / "evals" / "qa-review" / "cases").glob("*.yaml"))
    assert cases
    for case in cases:
        text = case.read_text(encoding="utf-8")
        mode = re.search(r"^prompt: \"/qa-review (initial|final) ", text, re.MULTILINE).group(1)
        enforced = int(re.search(r"max_comment_words: (\d+)", text).group(1))
        assert enforced == limits[mode], case.name


def test_every_case_prompt_asks_for_the_json_block_so_scoring_can_read_it():
    for case in (ROOT / "evals" / "qa-review" / "cases").glob("*.yaml"):
        prompt = re.search(r"^prompt: \"(.*)\"$", case.read_text(encoding="utf-8"), re.MULTILINE).group(1)
        command = prompt.split(".")[0]
        assert command.split()[-1] == "json", case.name


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
