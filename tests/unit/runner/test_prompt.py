import pytest

from evals.runner.loader import EvalConfigError
from evals.runner.prompt import build_system_prompt, build_user_message, load_skill


def test_loads_skill_and_references(skills_dir):
    skill = load_skill(skills_dir, "todo-check")
    assert skill.name == "todo-check"
    assert skill.skill_md.startswith("---\nname: todo-check")
    assert list(skill.references) == ["references/notes.md"]


def test_missing_skill_raises(skills_dir):
    with pytest.raises(EvalConfigError, match="SKILL.md"):
        load_skill(skills_dir, "absent")


def test_skill_without_references_folder(tmp_path):
    (tmp_path / "s").mkdir()
    (tmp_path / "s" / "SKILL.md").write_text("---\nname: s\n---\nbody")
    assert load_skill(tmp_path, "s").references == {}


def test_system_prompt_contains_preamble_skill_and_references(skills_dir):
    system = build_system_prompt(load_skill(skills_dir, "todo-check"))
    assert system.startswith("You are running inside an automated evaluation")
    assert '<skill name="todo-check">' in system
    assert "# TODO check" in system
    assert '<reference path="references/notes.md">' in system
    assert "What counts as a TODO" in system


def test_user_message_wraps_files_in_order_then_prompt():
    message = build_user_message({"a.diff": "one\n", "b.md": "two"}, "Review this.")
    assert message == '<file name="a.diff">\none\n</file>\n\n<file name="b.md">\ntwo\n</file>\n\nReview this.'
