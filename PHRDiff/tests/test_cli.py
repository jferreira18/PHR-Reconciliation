from pathlib import Path

from phr_diff.cli import build_parser


def test_cli_default_output_uses_user_downloads():
    args = build_parser().parse_args(["old.pdf", "new.pdf", "--no-open"])
    assert args.output == Path.home() / "Downloads" / "PHR Diff Reports" / "phr_report"
