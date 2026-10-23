import pytest

from evals.runner.loader import EvalConfigError
from evals.runner.prompt import (
    build_system_prompt,
    build_user_message,
    load_skill,
    with_lenses,
)


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


def test_loads_text_assets_and_skips_binary_ones(tmp_path):
    assets = tmp_path / "s" / "assets"
    assets.mkdir(parents=True)
    (tmp_path / "s" / "SKILL.md").write_text("---\nname: s\n---\nbody")
    (assets / "comment.md").write_text("template")
    (assets / "logo.png").write_bytes(b"\x89PNG\xff\xfe")
    assert load_skill(tmp_path, "s").assets == {"assets/comment.md": "template"}


def test_system_prompt_contains_assets(tmp_path):
    (tmp_path / "s" / "assets").mkdir(parents=True)
    (tmp_path / "s" / "SKILL.md").write_text("---\nname: s\n---\nbody")
    (tmp_path / "s" / "assets" / "comment.md").write_text("template\n")
    system = build_system_prompt(load_skill(tmp_path, "s"))
    assert '<asset path="assets/comment.md">\ntemplate\n</asset>' in system


def skill_with_lenses(tmp_path):
    lenses = tmp_path / "s" / "references" / "lenses"
    lenses.mkdir(parents=True)
    (tmp_path / "s" / "SKILL.md").write_text("---\nname: s\n---\nbody")
    (tmp_path / "s" / "references" / "core.md").write_text("core")
    for name in ("README", "service", "web"):
        (lenses / f"{name}.md").write_text(name)
    return load_skill(tmp_path, "s")


def test_with_lenses_none_keeps_every_lens(tmp_path):
    skill = skill_with_lenses(tmp_path)
    assert with_lenses(skill, None) == skill


def test_with_lenses_keeps_only_the_named_lenses_plus_core_and_index(tmp_path):
    kept = with_lenses(skill_with_lenses(tmp_path), ("web",))
    assert list(kept.references) == [
        "references/core.md",
        "references/lenses/README.md",
        "references/lenses/web.md",
    ]


def test_with_lenses_empty_leaves_the_core_only(tmp_path):
    kept = with_lenses(skill_with_lenses(tmp_path), ())
    assert list(kept.references) == ["references/core.md", "references/lenses/README.md"]


def test_with_lenses_rejects_a_lens_the_skill_does_not_have(tmp_path):
    with pytest.raises(EvalConfigError, match=r"no lens ghost \(available: service, web\)"):
        with_lenses(skill_with_lenses(tmp_path), ("ghost",))


def test_with_lenses_does_not_treat_the_index_as_a_lens(tmp_path):
    with pytest.raises(EvalConfigError, match="no lens README"):
        with_lenses(skill_with_lenses(tmp_path), ("README",))
