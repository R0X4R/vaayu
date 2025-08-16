from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import asyncssh


@dataclass
class SSHClientConfig:
    host: str
    port: int = 22
    username: Optional[str] = None
    password: Optional[str] = None
    key_path: Optional[str] = None
    known_hosts: Optional[str] = None
    strict_host_key: bool = False
    # Security: strong ciphers
    ciphers: tuple[str, ...] = (
        "chacha20-poly1305@openssh.com",
        "aes256-gcm@openssh.com",
    )


class SSHClient:
    """Async SSH client wrapper using asyncssh with SFTP support."""

    def __init__(self, cfg: SSHClientConfig):
        self.cfg = cfg
        self._conn: Optional[asyncssh.SSHClientConnection] = None
        self._sftp: Optional[asyncssh.SFTPClient] = None

    async def connect(self) -> None:
        known_hosts = None if not self.cfg.strict_host_key else (self.cfg.known_hosts or "~/.ssh/known_hosts")
        client_keys = []
        if self.cfg.key_path:
            client_keys = [self.cfg.key_path]

        self._conn = await asyncssh.connect(
            self.cfg.host,
            port=self.cfg.port,
            username=self.cfg.username,
            password=self.cfg.password,
            client_keys=client_keys or None,
            known_hosts=known_hosts,
            encryption_algs=self.cfg.ciphers,
            compression_algs=(),
        )
        self._sftp = await self._conn.start_sftp_client()

    async def ensure_connected(self) -> None:
        if self._conn is None or self._conn._default_loop is None:
            await self.connect()

    async def close(self) -> None:
        if self._sftp:
            self._sftp.exit()
            self._sftp = None
        if self._conn:
            self._conn.close()
            try:
                await self._conn.wait_closed()
            except Exception:
                pass
            self._conn = None

    @property
    def sftp(self) -> asyncssh.SFTPClient:
        if not self._sftp:
            raise RuntimeError("SFTP client not connected")
        return self._sftp

    async def stat(self, path: str) -> Optional[asyncssh.SFTPName]:
        try:
            return await self.sftp.stat(path)
        except (FileNotFoundError, asyncssh.SFTPNoSuchFile):
            return None

    async def makedirs(self, path: str) -> None:
        # Use POSIX paths; remote servers likely use '/'
        parts = []
        p = path.replace("\\", "/").strip("/")
        cur = ""
        for comp in p.split("/"):
            cur = f"{cur}/{comp}" if cur else f"/{comp}"
            try:
                await self.sftp.mkdir(cur)
            except Exception:
                # Directory may already exist
                pass

    async def open_remote(self, path: str, flags: str = "r") -> asyncssh.SFTPFile:
        return await self.sftp.open(path, flags)

    async def rename(self, src: str, dst: str) -> None:
        await self.sftp.rename(src, dst)

    async def remove(self, path: str) -> None:
        try:
            await self.sftp.remove(path)
        except Exception:
            pass

    async def listdir(self, path: str) -> list[asyncssh.SFTPName]:
        return await self.sftp.listdir(path)
