from pathlib import Path

import pytest

SAMPLE_DIR = Path(__file__).parent / "data" / "eval-sample"


@pytest.fixture
def skills_dir() -> Path:
    return SAMPLE_DIR / "skills"


@pytest.fixture
def evals_dir() -> Path:
    return SAMPLE_DIR / "evals"
