"""argparse entry point (spec AC2; DEC-015 = stdlib argparse, zero deps).

Phase 2 wires only ``add``. The installed ``claude-switch``/``cas`` console name
and its alias are Phase 5 (AC7.3) — there is no ``[project.scripts]`` yet; this
module is invoked via ``python -m cas`` (see ``cas/__main__.py``) or by calling
:func:`main` directly (the tests do the latter). Later phases register their
subparsers here.
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from .add import run_add
from .run import run_command, split_double_dash


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cas",
        description="claude-account-switcher: concurrent multi-account Claude tooling.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    add_p = sub.add_parser(
        "add",
        help="guided mint: authorize in the browser, capture the oat, bind a label",
    )
    add_p.add_argument(
        "label",
        nargs="?",
        default=None,
        help="label for the slot; defaults to the email local-part (you confirm)",
    )

    run_p = sub.add_parser(
        "run",
        help="run a command with a slot's credential injected for that process only",
        usage="cas run <label> -- <cmd...>",
    )
    run_p.add_argument("label", help="the slot whose credential to inject")
    # The child command is parsed out of the raw argv by split_double_dash in
    # main() — never by argparse — so the child's own flags are passed verbatim.
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    raw = list(sys.argv[1:]) if argv is None else list(argv)
    # Split on the first `--` BEFORE argparse so a child's flags (e.g.
    # `claude -p --foo`) are never interpreted as cas options.
    before, after = split_double_dash(raw)

    parser = build_parser()
    args = parser.parse_args(before)

    if args.command == "add":
        return run_add(args.label)
    if args.command == "run":
        if not after:
            parser.error("run requires a command: cas run <label> -- <cmd...>")
        return run_command(args.label, after)
    parser.error(f"unknown command: {args.command}")  # argparse exits; unreachable
    return 2
