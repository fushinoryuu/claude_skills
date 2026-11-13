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


def test_each_template_tells_the_model_to_put_names_in_backticks():
    """Jira reads __tests__ as bold, so file names, folder names and identifiers need backticks everywhere."""
    for name in TEMPLATES:
        rules = template_rules(name)
        assert "in backticks" in rules and "__tests__" in rules, name


SKILL_MD = ROOT / "skills" / "qa-review" / "SKILL.md"


def skill_step(number: int) -> str:
    text = SKILL_MD.read_text(encoding="utf-8")
    return re.split(rf"^### Step {number}:", text, flags=re.MULTILINE)[1].split("\n### ")[0]


def test_step_10_repeats_the_backtick_rule_for_names():
    assert "in backticks" in skill_step(10)


def test_the_report_always_has_the_patterns_section_even_when_empty():
    item = next(line for line in skill_step(12).splitlines() if "Suggested additions" in line)
    assert "every review" in item and "None found." in item
    assert "only if" not in item.lower()
    assert "Never include it in the Jira comment" in item


def test_step_11_records_the_pattern_result_on_every_review():
    assert "on every review" in skill_step(11) and "no new gap pattern" in skill_step(11)


def step_12_item(marker: str) -> str:
    return next(line for line in skill_step(12).splitlines() if marker in line)


def test_the_compact_block_has_a_heading_and_comes_last():
    step = skill_step(12)
    assert "## Run this to compact context" in step
    assert step.index("## Run this to compact context") < step.index("/compact Keep:")
    assert step.index("after the JSON block") > step.index("## Run this to compact context")
    assert step.rstrip().endswith("```")


def test_the_comment_section_is_printed_unchanged_or_marked_shortened():
    item = step_12_item("`## Comment`")
    assert "unchanged" in item and "shortened" in item
    assert "never call a shortened copy exactly" in item


def test_the_summary_holds_only_the_listed_items():
    item = step_12_item("`## Summary`")
    assert "only these items" in item and "Add no other bullets" in item
