from pathlib import Path

from vaayu.verify import sha256_file


def test_sha256_file(tmp_path: Path):
    p = tmp_path / "a.bin"
    data = b"hello" * 1000
    p.write_bytes(data)
    assert sha256_file(str(p)) == sha256_file(str(p))
