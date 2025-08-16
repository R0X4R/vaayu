from __future__ import annotations

from dataclasses import dataclass
import zstandard as zstd


@dataclass
class ZstdConfig:
    level: int = 3
    threads: int = 0


def compress_bytes(data: bytes, *, level: int = 3) -> bytes:
    c = zstd.ZstdCompressor(level=level)
    return c.compress(data)


def decompress_bytes(data: bytes) -> bytes:
    d = zstd.ZstdDecompressor()
    return d.decompress(data)
