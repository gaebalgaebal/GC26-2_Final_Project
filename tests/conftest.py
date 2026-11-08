import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(scope="session")
def source_dir():
    configured = os.getenv("EXAM_DATA_DIR")
    if configured:
        return Path(configured)
    matches = list(Path(__file__).resolve().parents[2].glob("최종평가*/최종평가"))
    if not matches:
        pytest.skip("Set EXAM_DATA_DIR to run supplied-file integration tests")
    return matches[0]


@pytest.fixture(scope="session")
def exam(source_dir):
    from exam_helper.data import analyze
    return analyze(next(source_dir.glob("*문제.pdf")).read_bytes(),
                   next(source_dir.glob("*정답.pdf")).read_bytes(),
                   (source_dir / "sample_data.xlsx").read_bytes())
