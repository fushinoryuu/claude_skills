"""Structure checks over every real skill in skills/. The rules live in evals/structure.py."""

from pathlib import Path

import pytest

from evals.structure import check_skill, find_skill_folders

ROOT = Path(__file__).parents[2]
SKILLS_DIR = ROOT / "skills"
EVALS_DIR = ROOT / "evals"

FOLDERS = find_skill_folders(SKILLS_DIR) or [
    pytest.param(None, marks=pytest.mark.skip(reason="no skills in skills/ yet"))
]


@pytest.mark.parametrize("folder", FOLDERS)
def test_skill_structure(folder):
    problems = check_skill(SKILLS_DIR, EVALS_DIR, folder)
    assert not problems, "\n" + "\n".join(f"  - {p}" for p in problems)
