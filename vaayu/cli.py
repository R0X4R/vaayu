from __future__ import annotations

import argparse
import asyncio
from typing import List, Optional

from rich.console import Console
from rich.progress import Progress

from .ssh_client import SSHClient, SSHClientConfig
from .transfer import TransferManager, TransferOptions
from .watch import watch_and_send
from .utils import default_concurrency, expand_local_globs

console = Console()


class VaayuHelpFormatter(argparse.HelpFormatter):

    def __init__(self, prog):
        super().__init__(prog, max_help_position=30, width=120)

    def format_help(self):
        help_text = f"""Usage:
  {self._prog} [flags] {{send,get,relay}} ...

Flags:
CONNECTION:
  -u, -username string     SSH username for authentication
  -p, -port int           SSH port number (default: 22)
  -P, -password string    SSH password for authentication
  -i, -identity string    path to private key file (PEM/ed25519)
  -k, -verify-host-key    enable strict host key verification

TRANSFER:
  -j, -parallel int       number of concurrent transfers (default: auto)
  -r, -retries int        maximum retries per file (default: 5)
  -b, -backoff float      initial backoff seconds for retries (default: 0.5)
  -n, -no-verify          skip SHA-256 hash verification

COMPRESSION:
  -c, -compress           enable zstd compression
  -z, -zstd-level int     zstd compression level 1-22 (default: 3)

OUTPUT:
  -h, -help, -help        show this help message and exit
  -W, -watch              watch mode for continuous sync (send only)

COMMANDS:
  send                    transfer files from local to remote (local → remote)
  get                     transfer files from remote to local (remote → local)
  relay                   transfer files between remote hosts (remote → remote)

Examples:
  vaayu send -u alice -i ~/.ssh/id_ed25519 alice@server.com /backup *.log
  vaayu get -u bob -p 2222 bob@host.com ./downloads /var/log/*.txt
  vaayu relay -u admin server1 server2 /data/file.db /backup/file.db
  vaayu send -u user -j 8 -c -z 6 user@host /remote ./large_files/*

For more information about a specific command:
  vaayu send --help
  vaayu get --help
  vaayu relay --help
"""
        return help_text


def _parse_ssh_target(target: str) -> SSHClientConfig:
    if "@" in target:
        user, host = target.split("@", 1)
    else:
        user, host = None, target
    return SSHClientConfig(host=host, username=user)


def _fmt_bytes(n: int) -> str:
    value = float(n)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024 or unit == "TB":
            return (f"{int(value)} {unit}" if unit == "B" else f"{value:.1f} {unit}")
        value /= 1024.0
    return f"{value:.1f} PB"


def _fmt_rate(bytes_: int, seconds: float) -> str:
    if seconds <= 0:
        return "-"
    return f"{_fmt_bytes(int(bytes_ / seconds))}/s"


async def cmd_send(args: argparse.Namespace) -> None:
    cfg = _parse_ssh_target(args.target)
    cfg.port = args.port
    cfg.username = args.username or cfg.username
    cfg.password = args.password
    cfg.key_path = args.identity
    cfg.strict_host_key = args.verify_host_key
    client = SSHClient(cfg)

    paths = expand_local_globs(args.paths)
    tm = TransferManager()
    opts = TransferOptions(
        parallel=args.parallel or default_concurrency(),
        retries=args.retries,
        backoff=args.backoff,
        compress=args.compress,
        zstd_level=args.zstd_level,
        verify=not args.no_verify,
    )
    if args.watch:
        with Progress() as progress:
            tm.progress = progress
            await watch_and_send(client, paths, args.dest, opts)
    else:
        with Progress() as progress:
            tm.progress = progress
            stats = await tm.send_local_to_remote(client, paths, args.dest, opts)
        console.print(
            f"Transferred {stats.files} files, {_fmt_bytes(stats.bytes)} in {stats.duration_s:.2f}s"
            f" [{_fmt_rate(stats.bytes, stats.duration_s)}], retries={stats.retries}",
            style="green",
        )
    await client.close()


async def cmd_get(args: argparse.Namespace) -> None:
    cfg = _parse_ssh_target(args.target)
    cfg.port = args.port
    cfg.username = args.username or cfg.username
    cfg.password = args.password
    cfg.key_path = args.identity
    cfg.strict_host_key = args.verify_host_key
    client = SSHClient(cfg)

    tm = TransferManager()
    opts = TransferOptions(
        parallel=args.parallel or default_concurrency(),
        retries=args.retries,
        backoff=args.backoff,
        compress=args.compress,
        zstd_level=args.zstd_level,
        verify=not args.no_verify,
    )
    with Progress() as progress:
        tm.progress = progress
        stats = await tm.get_remote_to_local(client, args.paths, args.dest, opts)
    console.print(
        f"Transferred {stats.files} files, {_fmt_bytes(stats.bytes)} in {stats.duration_s:.2f}s"
        f" [{_fmt_rate(stats.bytes, stats.duration_s)}], retries={stats.retries}",
        style="green",
    )
    await client.close()


async def cmd_relay(args: argparse.Namespace) -> None:
    src_cfg = _parse_ssh_target(args.src)
    dst_cfg = _parse_ssh_target(args.dst)
    for c in (src_cfg, dst_cfg):
        c.port = args.port
        c.username = args.username or c.username
        c.password = args.password
        c.key_path = args.identity
        c.strict_host_key = args.verify_host_key
    src_client, dst_client = SSHClient(src_cfg), SSHClient(dst_cfg)

    pairs = [(s, d) for s, d in zip(args.src_paths, args.dst_paths)]

    tm = TransferManager()
    opts = TransferOptions(
        parallel=args.parallel or default_concurrency(),
        retries=args.retries,
        backoff=args.backoff,
        compress=args.compress,
        zstd_level=args.zstd_level,
        verify=not args.no_verify,
    )
    with Progress() as progress:
        tm.progress = progress
        stats = await tm.relay_remote_to_remote(src_client, dst_client, pairs, opts)
    console.print(
        f"Transferred {stats.files} files, {_fmt_bytes(stats.bytes)} in {stats.duration_s:.2f}s"
        f" [{_fmt_rate(stats.bytes, stats.duration_s)}], retries={stats.retries}",
        style="green",
    )
    await src_client.close()
    await dst_client.close()


def build_parser() -> argparse.ArgumentParser:
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("-u", "--username", type=str, default=None, help=argparse.SUPPRESS)
    parent.add_argument("-p", "--port", type=int, default=22, help=argparse.SUPPRESS)
    parent.add_argument("-P", "--password", type=str, default=None, help=argparse.SUPPRESS)
    parent.add_argument("-i", "--identity", type=str, default=None, help=argparse.SUPPRESS)
    parent.add_argument("-k", "--verify-host-key", action="store_true", help=argparse.SUPPRESS)
    parent.add_argument("-j", "--parallel", type=int, default=None, help=argparse.SUPPRESS)
    parent.add_argument("-r", "--retries", type=int, default=5, help=argparse.SUPPRESS)
    parent.add_argument("-b", "--backoff", type=float, default=0.5, help=argparse.SUPPRESS)
    parent.add_argument("-n", "--no-verify", action="store_true", help=argparse.SUPPRESS)
    parent.add_argument("-c", "--compress", action="store_true", help=argparse.SUPPRESS)
    parent.add_argument("-z", "--zstd-level", type=int, default=3, help=argparse.SUPPRESS)

    p = argparse.ArgumentParser(
        prog="vaayu",
        description="Secure parallel resumable SSH transfer",
        formatter_class=VaayuHelpFormatter,
        add_help=False,
    )

    p.add_argument("-h", "--help", "-help", action="store_const", const=True, help=argparse.SUPPRESS)

    sub = p.add_subparsers(dest="cmd", required=True, help=argparse.SUPPRESS)

    sp = sub.add_parser("send", help=argparse.SUPPRESS, add_help=False, parents=[parent])
    sp.add_argument("target", help="user@host")
    sp.add_argument("dest", help="remote directory")
    sp.add_argument("paths", nargs="+", help="local files/dirs or globs")
    sp.add_argument("-W", "--watch", action="store_true", help=argparse.SUPPRESS)
    sp.add_argument("--help", action="store_const", const=True, help=argparse.SUPPRESS)
    sp.set_defaults(func=cmd_send)

    gp = sub.add_parser("get", help=argparse.SUPPRESS, add_help=False, parents=[parent])
    gp.add_argument("target", help="user@host")
    gp.add_argument("dest", help="local directory")
    gp.add_argument("paths", nargs="+", help="remote files/dirs")
    gp.add_argument("--help", action="store_const", const=True, help=argparse.SUPPRESS)
    gp.set_defaults(func=cmd_get)

    rp = sub.add_parser("relay", help=argparse.SUPPRESS, add_help=False, parents=[parent])
    rp.add_argument("src", help="src user@host")
    rp.add_argument("dst", help="dst user@host")
    rp.add_argument("src_paths", nargs="+")
    rp.add_argument("dst_paths", nargs="+")
    rp.add_argument("--help", action="store_const", const=True, help=argparse.SUPPRESS)
    rp.set_defaults(func=cmd_relay)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()

    if argv is None:
        import sys
        argv = sys.argv[1:]

    if len(argv) == 0 or (any(arg in ['-h', '--help', '-help'] for arg in argv) and len(argv) == 1):
        formatter = VaayuHelpFormatter("vaayu")
        print(formatter.format_help())
        return 0

    if len(argv) >= 2 and argv[1] in ['--help', '-h', '-help']:
        cmd = argv[0]
        if cmd == "send":
            print("""Usage:
  vaayu send [flags] <user@host> <remote_dir> <local_paths...>

Arguments:
  user@host           SSH target (user@hostname)
  remote_dir          destination directory on remote host
  local_paths         local files, directories, or glob patterns

Flags:
  -W, -watch          watch local paths for changes and auto-sync
  --help              show this help message

Examples:
  vaayu send -u alice alice@server.com /backup *.log
  vaayu send -u bob -i ~/.ssh/id_rsa bob@host.com /data ./files/
  vaayu send -u user -W -j 4 user@host.com /sync ./watched_folder/
""")
        elif cmd == "get":
            print("""Usage:
  vaayu get [flags] <user@host> <local_dir> <remote_paths...>

Arguments:
  user@host           SSH target (user@hostname)
  local_dir           destination directory on local machine
  remote_paths        remote files, directories, or patterns

Flags:
  --help              show this help message

Examples:
  vaayu get -u alice alice@server.com ./downloads /var/log/*.txt
  vaayu get -u bob -p 2222 bob@host.com ./backup /data/important/
""")
        elif cmd == "relay":
            print("""Usage:
  vaayu relay [flags] <src_user@host> <dst_user@host> <src_paths...> <dst_paths...>

Arguments:
  src_user@host       source SSH target
  dst_user@host       destination SSH target
  src_paths           source file paths on source host
  dst_paths           destination file paths on destination host

Flags:
  --help              show this help message

Examples:
  vaayu relay -u admin server1 server2 /data/file.db /backup/file.db
  vaayu relay -u user host1 host2 /logs/*.txt /archive/
""")
        return 0

    args = parser.parse_args(argv)

    if hasattr(args, 'help') and args.help:
        formatter = VaayuHelpFormatter("vaayu")
        print(formatter.format_help())
        return 0

    try:
        asyncio.run(args.func(args))
    except KeyboardInterrupt:
        console.print("Interrupted", style="yellow")
        return 130
    return 0
