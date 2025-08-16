from __future__ import annotations

import time
from typing import Iterable

from watchdog.events import FileSystemEventHandler


class _EventBatcher(FileSystemEventHandler):
    def __init__(self, on_batch, debounce_s: float = 0.5):
        self.on_batch = on_batch
        self.debounce_s = debounce_s
        self._last = 0.0
        self._paths = set()

    def on_any_event(self, event):
        if event.is_directory:
            return
        self._paths.add(event.src_path)
        now = time.time()
        if now - self._last > self.debounce_s:
            self._last = now
            self.on_batch(sorted(self._paths))
            self._paths.clear()


async def watch_and_send(client, local_paths: Iterable[str], remote_dir: str, opts) -> None:
    # Minimal placeholder; actual implementation lives in the original package
    # and is invoked via cli where needed. This stub keeps API compatibility.
    pass
