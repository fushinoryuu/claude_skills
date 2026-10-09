import pytest

from evals.runner.loader import EvalConfigError
from evals.runner.skills import load_catalog, parse_frontmatter


def test_parses_frontmatter():
    meta = parse_frontmatter("---\nname: a\ndescription: Does a thing.\n---\n# Body\n")
    assert meta == {"name": "a", "description": "Does a thing."}


@pytest.mark.parametrize(
    "text, message",
    [
        ("", "missing frontmatter"),
        ("# No frontmatter", "missing frontmatter"),
        ("---\nname: a\n", "not closed"),
        ("---\nname: [oops\n---\n", "invalid frontmatter"),
        ("---\njust a string\n---\n", "must be a mapping"),
    ],
)
def test_bad_frontmatter(text, message):
    with pytest.raises(EvalConfigError, match=message):
        parse_frontmatter(text)


def test_catalog_reads_sample_skill(skills_dir):
    [info] = load_catalog(skills_dir)
    assert (info.folder, info.name) == ("todo-check", "todo-check")
    assert info.description.startswith("Sample skill")


def test_catalog_collapses_multiline_descriptions(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "SKILL.md").write_text(
        "---\nname: a\ndescription: >\n  First line\n  second line.\n---\n"
    )
    assert load_catalog(tmp_path)[0].description == "First line second line."


def test_catalog_requires_name_and_description(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "SKILL.md").write_text("---\nname: a\n---\n")
    with pytest.raises(EvalConfigError, match="'name' and 'description'"):
        load_catalog(tmp_path)


def test_empty_skills_dir_raises(tmp_path):
    with pytest.raises(EvalConfigError, match="no skills found"):
        load_catalog(tmp_path)
