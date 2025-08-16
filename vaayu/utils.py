from __future__ import annotations

import asyncio
import os
import glob
from dataclasses import dataclass
from typing import Awaitable, Callable, Iterable, List, Optional, Tuple, Type, TypeVar


CHUNK_SIZE = 1024 * 1024  # 1 MiB
SMALL_FILE_BYTES = 256 * 1024  # 256 KiB


def default_concurrency() -> int:
    try:
        cpu = os.cpu_count() or 4
    except Exception:
        cpu = 4
    return max(2, min(32, cpu * 2))


def atomic_temp_name(dest_path: str) -> str:
    return dest_path + ".part"


def is_windows() -> bool:
    return os.name == "nt"


def expand_local_globs(paths: Iterable[str]) -> List[str]:
    """Expand local wildcard patterns while preserving explicit paths order."""
    out: List[str] = []
    for p in paths:
        base = os.path.expanduser(p)
        if any(ch in base for ch in "*?["):
            out.extend(sorted(glob.glob(base, recursive=True)))
        else:
            out.append(base)
    return out


def split_remote(path: str) -> Tuple[str, Optional[str]]:
    """Split user@host:/path into (host, path). If no host part, returns ("", path)."""
    if ":" in path and "@" in path.split(":", 1)[0]:
        user_host, p = path.split(":", 1)
        return user_host, p
    return "", path


T = TypeVar("T")


async def async_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    retries: int = 5,
    base_delay: float = 0.5,
    exc_types: Tuple[Type[BaseException], ...] = (Exception,),
) -> T:
    attempt = 0
    while True:
        try:
            return await fn()
        except exc_types:
            attempt += 1
            if attempt > retries:
                raise
            delay = base_delay * (2 ** (attempt - 1))
            await asyncio.sleep(min(delay, 10.0))


@dataclass
class Stats:
    files: int = 0
    bytes: int = 0
    duration_s: float = 0.0
    retries: int = 0

    def merge(self, other: "Stats") -> None:
        self.files += other.files
        self.bytes += other.bytes
        self.duration_s += other.duration_s
        self.retries += other.retries
