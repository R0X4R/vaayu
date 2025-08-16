from __future__ import annotations

import asyncio
import os
import time
import fnmatch
from dataclasses import dataclass
from typing import List, Optional, Tuple

from rich.progress import Progress, BarColumn, TimeRemainingColumn, TransferSpeedColumn, TextColumn

from .ssh_client import SSHClient
from .utils import CHUNK_SIZE, atomic_temp_name, default_concurrency, Stats
from .verify import sha256_file


@dataclass
class TransferOptions:
    parallel: Optional[int] = None
    retries: int = 5
    backoff: float = 0.5
    compress: bool = False
    zstd_level: int = 3
    zstd_threads: int = 0
    verify: bool = True
    preserve_mtime: bool = True


class TransferManager:
    def __init__(self, progress: Optional[Progress] = None):
        self.progress = progress

    async def _progress_task(self):
        if self.progress:
            return self.progress
        return Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("{task.percentage:>3.0f}%"),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            transient=True,
        )

    async def send_local_to_remote(
        self,
        client: SSHClient,
        local_paths: List[str],
        remote_dir: str,
        opts: TransferOptions,
    ) -> Stats:
        await client.ensure_connected()
        parallel = opts.parallel or default_concurrency()

        files: List[Tuple[str, str]] = []
        for p in local_paths:
            p = os.path.expanduser(p)
            if os.path.isdir(p):
                for root, _, fnames in os.walk(p):
                    for fn in fnames:
                        src = os.path.join(root, fn)
                        rel = os.path.relpath(src, p)
                        dst = os.path.join(remote_dir, os.path.basename(p), rel)
                        files.append((src, dst))
            else:
                dst = os.path.join(remote_dir, os.path.basename(p))
                files.append((p, dst))
        semaphore = asyncio.Semaphore(parallel)

        stats = Stats()

        async def _upload_one(src_dst: Tuple[str, str]):
            src, dst = src_dst
            attempt = 0
            while True:
                attempt += 1
                try:
                    await client.makedirs(os.path.dirname(dst))
                    tmp = atomic_temp_name(dst)
                    # resume support: check remote temp size
                    rstat = await client.stat(tmp)
                    offset = rstat.size if rstat else 0
                    total = os.path.getsize(src)
                    t = None
                    if self.progress:
                        t = self.progress.add_task(f"upload {os.path.basename(src)}", total=total)
                    mode = "r+b" if offset > 0 else "wb"
                    async with await client.open_remote(tmp, mode) as rf:
                        with open(src, "rb", buffering=0) as lf:
                            if offset:
                                await rf.seek(offset)
                                lf.seek(offset)
                                if t:
                                    self.progress.advance(t, offset)
                            while True:
                                data = lf.read(CHUNK_SIZE)
                                if not data:
                                    break
                                await rf.write(data)
                                if t:
                                    self.progress.advance(t, len(data))
                    if t:
                        self.progress.update(t, completed=total)
                    if opts.verify:
                        # compute local hash and remote hash via exec
                        local_hash = sha256_file(src)
                        remote_hash = await self._remote_sha256(client, tmp)
                        if local_hash != remote_hash:
                            raise RuntimeError(f"hash mismatch for {src}")
                    await client.rename(tmp, dst)
                    stats.files += 1
                    stats.bytes += total
                    if attempt > 1:
                        stats.retries += attempt - 1
                    return
                except Exception:
                    if attempt > opts.retries:
                        raise
                    await asyncio.sleep(min(opts.backoff * (2 ** (attempt - 1)), 10.0))

        tasks = []
        for pair in files:
            await semaphore.acquire()
            tasks.append(asyncio.create_task(self._with_sem(semaphore, _upload_one, pair)))
        t0 = time.perf_counter()
        for t in tasks:
            await t
        stats.duration_s += time.perf_counter() - t0
        return stats

    async def get_remote_to_local(
        self,
        client: SSHClient,
        remote_paths: List[str],
        local_dir: str,
        opts: TransferOptions,
    ) -> Stats:
        await client.ensure_connected()
        parallel = opts.parallel or default_concurrency()

        files: List[Tuple[str, str]] = []

        async def _walk_remote(base: str, rel: str = ""):
            base_norm = base.rstrip("/") or "/"
            st = await client.stat(base_norm)
            if st and (st.permissions & 0o040000):
                # directory
                for entry in await client.listdir(base_norm):
                    await _walk_remote(f"{base_norm}/{entry.filename}", f"{rel}/{entry.filename}" if rel else entry.filename)
            else:
                dst = os.path.join(local_dir, rel or os.path.basename(base_norm))
                files.append((base_norm, dst))

        # Expand wildcards by listing parent dir and filtering
        async def _expand_remote(path: str) -> List[str]:
            if any(ch in path for ch in "*?["):
                parent = path.rsplit("/", 1)[0] if "/" in path else "."
                patt = path[len(parent) + 1 :] if parent != "." else path
                entries = await client.listdir(parent)
                return [f"{parent.rstrip('/')}/{e.filename}" for e in entries if fnmatch.fnmatch(e.filename, patt)]
            return [path]

        for r in remote_paths:
            for rr in await _expand_remote(r):
                await _walk_remote(rr)

        semaphore = asyncio.Semaphore(parallel)

        stats = Stats()

        async def _download_one(src_dst: Tuple[str, str]):
            src, dst = src_dst
            attempt = 0
            tmp = atomic_temp_name(dst)
            os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
            while True:
                attempt += 1
                try:
                    # resume
                    offset = os.path.getsize(tmp) if os.path.exists(tmp) else 0
                    async with await client.open_remote(src, "rb") as rf:
                        with open(tmp, "ab" if offset else "wb", buffering=0) as lf:
                            if offset:
                                await rf.seek(offset)
                            while True:
                                data = await rf.read(CHUNK_SIZE)
                                if not data:
                                    break
                                lf.write(data)
                    if opts.verify:
                        remote_hash = await self._remote_sha256(client, src)
                        local_hash = sha256_file(tmp)
                        if remote_hash != local_hash:
                            raise RuntimeError(f"hash mismatch for {src}")
                    os.replace(tmp, dst)
                    stats.files += 1
                    try:
                        # get size cheaply
                        sz = os.path.getsize(dst)
                        stats.bytes += sz
                    except Exception:
                        pass
                    if attempt > 1:
                        stats.retries += attempt - 1
                    return
                except Exception:
                    if attempt > opts.retries:
                        raise
                    await asyncio.sleep(min(opts.backoff * (2 ** (attempt - 1)), 10.0))

        tasks = []
        for pair in files:
            await semaphore.acquire()
            tasks.append(asyncio.create_task(self._with_sem(semaphore, _download_one, pair)))
        t0 = time.perf_counter()
        for t in tasks:
            await t
        stats.duration_s += time.perf_counter() - t0
        return stats

    async def relay_remote_to_remote(
        self,
        src_client: SSHClient,
        dst_client: SSHClient,
        pairs: List[Tuple[str, str]],
        opts: TransferOptions,
    ) -> Stats:
        await src_client.ensure_connected()
        await dst_client.ensure_connected()
        parallel = opts.parallel or default_concurrency()
        semaphore = asyncio.Semaphore(parallel)
        stats = Stats()

        async def _relay_one(src: str, dst: str):
            attempt = 0
            while True:
                attempt += 1
                try:
                    await dst_client.makedirs(os.path.dirname(dst))
                    tmp = atomic_temp_name(dst)
                    # resume
                    rstat = await dst_client.stat(tmp)
                    offset = rstat.size if rstat else 0
                    async with await src_client.open_remote(src, "rb") as rf:
                        async with await dst_client.open_remote(tmp, "r+b" if offset else "wb") as wf:
                            if offset:
                                await rf.seek(offset)
                                await wf.seek(offset)
                            while True:
                                data = await rf.read(CHUNK_SIZE)
                                if not data:
                                    break
                                await wf.write(data)
                    if opts.verify:
                        sh_src = await self._remote_sha256(src_client, src)
                        sh_dst = await self._remote_sha256(dst_client, tmp)
                        if sh_src != sh_dst:
                            raise RuntimeError(f"hash mismatch for {src}")
                    await dst_client.rename(tmp, dst)
                    stats.files += 1
                    try:
                        sz = (await dst_client.stat(dst)).size  # type: ignore[union-attr]
                        stats.bytes += int(sz or 0)
                    except Exception:
                        pass
                    if attempt > 1:
                        stats.retries += attempt - 1
                    return
                except Exception:
                    if attempt > opts.retries:
                        raise
                    await asyncio.sleep(min(opts.backoff * (2 ** (attempt - 1)), 10.0))

        tasks = []
        for src, dst in pairs:
            await semaphore.acquire()
            tasks.append(asyncio.create_task(self._with_sem(semaphore, _relay_one, src, dst)))
        t0 = time.perf_counter()
        for t in tasks:
            await t
        stats.duration_s += time.perf_counter() - t0
        return stats

    async def _with_sem(self, sem: asyncio.Semaphore, fn, *args):
        try:
            return await fn(*args)
        finally:
            sem.release()

    async def _remote_sha256(self, client: SSHClient, path: str) -> str:
        """Compute SHA-256 on remote with multiple fallbacks: sha256sum, shasum, python3/python."""
        await client.ensure_connected()

        def _esc(p: str) -> str:
            # Simple POSIX single-quote escape: ' -> '\''
            return p.replace("'", "'\\''")

        async def _try(cmd: str) -> tuple[bool, str]:
            res = await client._conn.run(cmd, check=False)  # type: ignore[attr-defined]
            raw = res.stdout
            if isinstance(raw, bytes):
                out = raw.decode("utf-8", "ignore")
            else:
                out = str(raw) if raw is not None else ""
            ok = res.exit_status == 0 and bool(out)
            return bool(ok), out.strip()

        pe = _esc(path)
        # 1) sha256sum
        ok, out = await _try(f"sha256sum -- '{pe}'")
        if ok:
            return out.split()[0]
        # 2) shasum -a 256
        ok, out = await _try(f"shasum -a 256 -- '{pe}'")
        if ok:
            return out.split()[0]
        # 3) python3 -c
        py_code = (
            "import hashlib;"
            f"f=open(r'''{path}''','rb');"
            "h=hashlib.sha256();"
            "b=f.read(1048576);"
            "while b: h.update(b); b=f.read(1048576);"
            "print(h.hexdigest())"
        )
        ok, out = await _try(f"python3 -c '{py_code}'")
        if ok:
            return out
        # 4) python -c
        ok, out = await _try(f"python -c '{py_code}'")
        if ok:
            return out
        raise RuntimeError("Unable to compute remote SHA-256: no suitable tool available on remote host")
