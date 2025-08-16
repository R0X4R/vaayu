from vaayu.cli import build_parser


def test_cli_has_subcommands():
    p = build_parser()
    help_text = p.format_help()
    assert "send" in help_text and "get" in help_text and "relay" in help_text


def test_cli_parse_send_minimal():
    p = build_parser()
    ns = p.parse_args(["send", "user@host", "/dest", "file.txt"])
    assert ns.cmd == "send"
    assert ns.target == "user@host"
    assert ns.dest == "/dest"
    assert ns.paths == ["file.txt"]
