"""Each structure rule, broken on purpose. Starts from the sample skill, which passes every rule."""

import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from evals.structure import (
    MAX_SKILL_LINES,
    check_skill,
    find_skill_folders,
    referenced_paths,
)

SAMPLE = Path(__file__).parents[2] / "data" / "eval-sample"
DESCRIPTION = "Sample skill used to test the structure checks. Flags leftover TODOs in a diff."


@pytest.fixture
def tree(tmp_path):
    shutil.copytree(SAMPLE, tmp_path, dirs_exist_ok=True)
    return SimpleNamespace(
        skills=tmp_path / "skills",
        evals=tmp_path / "evals",
        skill=tmp_path / "skills" / "todo-check",
        kit=tmp_path / "evals" / "todo-check",
    )


def problems(tree) -> list[str]:
    return check_skill(tree.skills, tree.evals, "todo-check")


def assert_problem(tree, text: str):
    found = problems(tree)
    assert any(text in p for p in found), f"expected a problem containing {text!r}, got {found}"


def write_skill_md(tree, *, name="todo-check", description=DESCRIPTION, body="See references/notes.md.\n", **extra):
    meta = {"name": name, "description": description, **extra}
    frontmatter = "".join(f"{k}: {v!r}\n" for k, v in meta.items() if v is not None)
    (tree.skill / "SKILL.md").write_text(f"---\n{frontmatter}---\n\n{body}")


def edit_case(tree, case_id: str, mutate):
    path = tree.kit / "cases" / f"{case_id}.yaml"
    data = yaml.safe_load(path.read_text())
    mutate(data)
    path.write_text(yaml.safe_dump(data))


def test_sample_skill_passes_every_rule(tree):
    assert problems(tree) == []


# --- discovery ---


def test_find_skill_folders_ignores_hidden_and_files(tmp_path):
    (tmp_path / "b").mkdir()
    (tmp_path / "a").mkdir()
    (tmp_path / ".hidden").mkdir()
    (tmp_path / ".gitkeep").write_text("")
    assert find_skill_folders(tmp_path) == ["a", "b"]


def test_find_skill_folders_when_dir_is_missing(tmp_path):
    assert find_skill_folders(tmp_path / "nope") == []


def test_folder_without_skill_md(tree):
    (tree.skill / "SKILL.md").unlink()
    assert problems(tree) == ["todo-check: missing SKILL.md"]


# --- frontmatter ---


def test_missing_frontmatter(tree):
    (tree.skill / "SKILL.md").write_text("# Just a heading\n\nSee references/notes.md.\n")
    assert_problem(tree, "missing frontmatter")


def test_name_must_match_folder(tree):
    write_skill_md(tree, name="other-name")
    assert_problem(tree, "must match the folder name")


@pytest.mark.parametrize("name", ["Todo_Check", "todo check", "-todo", "x" * 65])
def test_name_must_be_kebab_case_and_short(tree, name):
    write_skill_md(tree, name=name)
    assert_problem(tree, "kebab-case")


def test_missing_name_and_description(tree):
    (tree.skill / "SKILL.md").write_text("---\nfoo: bar\n---\nSee references/notes.md.\n")
    assert_problem(tree, "'name' is missing")
    assert_problem(tree, "'description' is missing")


def test_description_too_short(tree):
    write_skill_md(tree, description="Checks things.")
    assert_problem(tree, "say what the skill does")


def test_description_too_long(tree):
    write_skill_md(tree, description="word " * 300)
    assert_problem(tree, "maximum 1024")


# --- size ---


def write_skill_md_with_lines(tree, total_lines: int):
    """Write a valid SKILL.md of exactly total_lines lines."""
    write_skill_md(tree)
    current = len((tree.skill / "SKILL.md").read_text().splitlines())
    write_skill_md(tree, body="See references/notes.md.\n" + "line\n" * (total_lines - current))
    assert len((tree.skill / "SKILL.md").read_text().splitlines()) == total_lines


def test_skill_md_one_line_over_budget(tree):
    write_skill_md_with_lines(tree, MAX_SKILL_LINES + 1)
    assert_problem(tree, f"{MAX_SKILL_LINES + 1} lines (budget {MAX_SKILL_LINES})")


def test_skill_md_exactly_at_budget_is_fine(tree):
    write_skill_md_with_lines(tree, MAX_SKILL_LINES)
    assert problems(tree) == []


# --- references ---


def test_markdown_link_to_missing_file(tree):
    write_skill_md(tree, body="See [notes](references/notes.md) and [more](references/gone.md).\n")
    assert_problem(tree, "'references/gone.md', which does not exist")


def test_backticked_path_to_missing_script(tree):
    write_skill_md(tree, body="See references/notes.md. Run `scripts/check.py` first.\n")
    assert_problem(tree, "'scripts/check.py', which does not exist")


def test_existing_script_reference_is_fine(tree):
    (tree.skill / "scripts").mkdir()
    (tree.skill / "scripts" / "check.py").write_text("print('ok')\n")
    write_skill_md(tree, body="See references/notes.md. Run `python scripts/check.py`.\n")
    assert problems(tree) == []


def test_orphaned_reference(tree):
    (tree.skill / "references" / "extra.md").write_text("never linked\n")
    assert_problem(tree, "references/extra.md exists but SKILL.md never mentions it")


def test_lens_files_are_not_orphans(tree):
    write_lens(tree, name="web-ui")
    assert problems(tree) == []


def test_other_nested_reference_files_are_still_orphans(tree):
    nested = tree.skill / "references" / "extra"
    nested.mkdir()
    (nested / "deep.md").write_text("never linked\n")
    assert_problem(tree, "references/extra/deep.md exists but SKILL.md never mentions it")


def test_gitkeep_in_references_is_not_an_orphan(tree):
    (tree.skill / "references" / ".gitkeep").write_text("")
    assert problems(tree) == []


def test_link_escaping_the_skill_folder(tree):
    write_skill_md(tree, body="See references/notes.md and [x](../../outside.md).\n")
    assert_problem(tree, "outside the skill folder")


def test_urls_and_anchors_are_not_file_references(tree):
    write_skill_md(
        tree,
        body="See references/notes.md, [docs](https://example.com/a.md), [mail](mailto:a@b.c), [top](#top).\n",
    )
    assert problems(tree) == []


def test_link_with_fragment_checks_the_file(tree):
    write_skill_md(tree, body="See [notes](references/notes.md#section).\n")
    assert problems(tree) == []


def test_repo_root_style_paths_are_not_matched():
    assert referenced_paths("see skills/pr-review/references/x.md and ../references/y.md") == set()


def test_trailing_punctuation_is_not_part_of_the_path():
    assert referenced_paths("Read references/a.md, then references/b.md.") == {"references/a.md", "references/b.md"}


def test_directory_mentions_are_ignored():
    assert referenced_paths("Files live in references/ and scripts/.") == set()


# --- eval kit ---


def test_missing_categories_file(tree):
    (tree.kit / "categories.yaml").unlink()
    assert_problem(tree, "categories.yaml")


def test_case_using_slug_outside_vocabulary(tree):
    edit_case(tree, "todo-check-has-todo-01", lambda d: d["expect"]["findings"][0].update(category="zzz"))
    assert_problem(tree, "'zzz' is not in categories.yaml")


def test_case_pointing_at_missing_fixture(tree):
    shutil.rmtree(tree.kit / "fixtures" / "has-todo")
    assert_problem(tree, "case todo-check-has-todo-01: missing fixture folder")


def test_no_clean_case(tree):
    edit_case(tree, "todo-check-no-todo-01", lambda d: d.update(tags=[]))
    assert_problem(tree, "needs a clean case")


def test_clean_case_with_too_high_max_findings(tree):
    edit_case(tree, "todo-check-no-todo-01", lambda d: d["expect"].update(max_findings=5))
    assert_problem(tree, "needs a clean case")


def test_case_tagged_clean_must_not_expect_findings(tree):
    edit_case(tree, "todo-check-has-todo-01", lambda d: d.update(tags=["clean"]))
    assert_problem(tree, "tagged 'clean' but expects findings")


def test_case_that_checks_lenses_must_carry_the_lenses_tag(tree):
    edit_case(tree, "todo-check-has-todo-01", lambda d: d["expect"].update(lenses=[]))
    assert_problem(tree, "sets expect.lenses but is not tagged 'lenses'")
    edit_case(tree, "todo-check-has-todo-01", lambda d: d.update(tags=["defect", "lenses"]))
    assert problems(tree) == []


def test_missing_triggers_file(tree):
    (tree.kit / "triggers.yaml").unlink()
    assert_problem(tree, "triggers.yaml")


@pytest.mark.parametrize(
    "content, message",
    [
        ("should_trigger: []\nshould_not_trigger: [a]\n", "no should_trigger prompts"),
        ("should_trigger: [a]\nshould_not_trigger: []\n", "no should_not_trigger prompts"),
    ],
)
def test_triggers_need_both_kinds(tree, content, message):
    (tree.kit / "triggers.yaml").write_text(content)
    assert_problem(tree, message)


def write_manual_only_skill_md(tree, value):
    # The key has hyphens, so it cannot be a keyword argument.
    write_skill_md(tree, **{"disable-model-invocation": value})


def test_manual_only_skill_needs_no_triggers_file(tree):
    write_manual_only_skill_md(tree, True)
    (tree.kit / "triggers.yaml").unlink()
    assert problems(tree) == []


def test_skill_that_can_be_auto_selected_still_needs_triggers(tree):
    write_manual_only_skill_md(tree, False)
    (tree.kit / "triggers.yaml").unlink()
    assert_problem(tree, "triggers.yaml")


def test_manual_only_skill_still_needs_its_cases(tree):
    write_manual_only_skill_md(tree, True)
    (tree.kit / "cases").rename(tree.kit / "cases-gone")
    assert_problem(tree, "cases")


def test_all_problems_are_reported_together(tree):
    write_skill_md(tree, name="wrong", description="Short.")
    (tree.kit / "triggers.yaml").unlink()
    assert len(problems(tree)) >= 3


# --- lenses and stack-neutral wording ---

LENS = """\
---
name: {name}
description: Extra checks for one kind of change.
applies_when:
  paths: ["**/*.sample"]
  touches: "a sample kind of change"
---

# Sample lens
"""


def write_lens(tree, name="sample", text=None):
    lenses = tree.skill / "references" / "lenses"
    lenses.mkdir(parents=True, exist_ok=True)
    (lenses / f"{name}.md").write_text(LENS.format(name=name) if text is None else text)


def test_valid_lens_passes(tree):
    write_lens(tree)
    assert problems(tree) == []


def test_lenses_readme_is_not_checked_as_a_lens(tree):
    write_lens(tree)
    (tree.skill / "references" / "lenses" / "README.md").write_text("# How to add a lens\n")
    assert problems(tree) == []


def test_lens_without_frontmatter(tree):
    write_lens(tree, text="# No frontmatter\n")
    assert_problem(tree, "references/lenses/sample.md: missing frontmatter")


def test_lens_name_must_equal_its_file_name(tree):
    write_lens(tree, text=LENS.format(name="other"))
    assert_problem(tree, "'name' must equal the file name 'sample'")


def test_lens_needs_a_description(tree):
    write_lens(tree, text=LENS.replace("description: Extra checks for one kind of change.\n", "").format(name="sample"))
    assert_problem(tree, "needs a non-empty 'description'")


def test_lens_needs_applies_when(tree):
    write_lens(tree, text="---\nname: sample\ndescription: Extra checks.\n---\n")
    assert_problem(tree, "needs an 'applies_when' block")


@pytest.mark.parametrize(
    "paths",
    ['"**/*.sample"', "[]", '["", "a"]', "[1]"],
    ids=["a string, not a list", "empty list", "blank glob", "not a string"],
)
def test_lens_paths_must_be_a_list_of_globs(tree, paths):
    write_lens(tree, text=LENS.replace('["**/*.sample"]', paths).format(name="sample"))
    assert_problem(tree, "applies_when.paths must be a non-empty list of file globs")


def test_lens_needs_a_touches_line(tree):
    write_lens(tree, text=LENS.replace('  touches: "a sample kind of change"\n', "").format(name="sample"))
    assert_problem(tree, "applies_when.touches must be one plain-language line")


def test_skill_md_must_not_name_a_specific_lens(tree):
    write_lens(tree)
    write_skill_md(tree, body="See references/notes.md and [the lens](references/lenses/sample.md).\n")
    assert_problem(tree, "SKILL.md names the lens file 'sample.md'")


def test_skill_md_may_link_the_lenses_readme(tree):
    write_lens(tree)
    write_skill_md(tree, body="See references/notes.md and [lenses](references/lenses/README.md).\n")
    (tree.skill / "references" / "lenses" / "README.md").write_text("# How to add a lens\n")
    assert problems(tree) == []


def test_core_reference_must_not_name_a_specific_lens(tree):
    write_lens(tree)
    (tree.skill / "references" / "notes.md").write_text("Also read lenses/sample.md.\n")
    assert_problem(tree, "references/notes.md names the lens file 'sample.md'")


@pytest.mark.parametrize("word", ["endpoint", "Endpoints", "Terraform", "back-end", "SQL"])
def test_skill_md_must_not_use_stack_specific_words(tree, word):
    write_lens(tree)
    write_skill_md(tree, body=f"See references/notes.md. Check each {word} for gaps.\n")
    assert_problem(tree, f"SKILL.md uses the stack-specific word '{word.lower().removesuffix('s')}'")


def test_core_reference_must_not_use_stack_specific_words(tree):
    write_lens(tree)
    (tree.skill / "references" / "notes.md").write_text("Check the Kubernetes manifest.\n")
    assert_problem(tree, "references/notes.md uses the stack-specific word 'kubernetes'")


def test_a_lens_may_use_stack_specific_words(tree):
    write_lens(tree, text=LENS.format(name="sample") + "Check every endpoint and every SQL migration.\n")
    assert problems(tree) == []


def test_words_that_only_contain_a_stack_term_are_fine(tree):
    write_lens(tree)
    write_skill_md(tree, body="See references/notes.md. A reactive, sequel-like cssd result is fine.\n")
    assert problems(tree) == []


def test_skill_without_lenses_is_not_scanned_for_stack_words(tree):
    write_skill_md(tree, body="See references/notes.md. Check each endpoint.\n")
    assert problems(tree) == []


# --- output format and the category list ---

OUTPUT_FORMAT = """\
# Findings block

## Categories

| Slug             | Use it when        |
| ---------------- | ------------------ |
| `leftover-todo`  | A TODO is left in  |

## Severity

- `high`: a row like | `not-a-category` | here does not count
"""


def write_output_format(tree, text=OUTPUT_FORMAT):
    (tree.skill / "references" / "output-format.md").write_text(text)
    write_skill_md(tree, body="See references/notes.md and references/output-format.md.\n")


def test_output_format_matching_the_category_list_passes(tree):
    write_output_format(tree)
    assert problems(tree) == []


def test_category_missing_from_the_output_format(tree):
    write_output_format(tree, OUTPUT_FORMAT.replace("`leftover-todo`", "`other`"))
    assert_problem(tree, "categories.yaml has 'leftover-todo', which the Categories table does not")


def test_category_in_the_output_format_but_not_in_the_list(tree):
    write_output_format(tree, OUTPUT_FORMAT.replace("| `leftover-todo`  | A TODO is left in  |\n", "| `leftover-todo` | x |\n| `extra-slug` | y |\n"))
    assert_problem(tree, "the Categories table has 'extra-slug', which categories.yaml does not")


def test_output_format_needs_a_categories_section(tree):
    write_output_format(tree, "# Findings block\n")
    assert_problem(tree, "needs a '## Categories' section")
