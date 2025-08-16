from pathlib import Path
import os

from vaayu.utils import default_concurrency, atomic_temp_name, expand_local_globs


def test_default_concurrency_positive():
    assert default_concurrency() >= 2


def test_atomic_temp_name():
    assert atomic_temp_name("/tmp/a") == "/tmp/a.part"


def test_expand_globs(tmp_path: Path):
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "b.txt").write_text("b")
    prev = Path.cwd()
    try:
        os.chdir(tmp_path)
        out = expand_local_globs(["*.txt"])  # type: ignore
        assert len(out) == 2
    finally:
        os.chdir(prev)
