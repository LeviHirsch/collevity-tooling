"""argparse entry point (spec AC2; DEC-015 = stdlib argparse, zero deps).

Phase 2 wires only ``add``. The installed ``claude-switch``/``cas`` console name
and its alias are Phase 5 (AC7.3) — there is no ``[project.scripts]`` yet; this
module is invoked via ``python -m cas`` (see ``cas/__main__.py``) or by calling
:func:`main` directly (the tests do the latter). Later phases register their
subparsers here.
"""

from __future__ import annotations

import argparse
from typing import Optional, Sequence

from .add import run_add


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
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "add":
        return run_add(args.label)
    parser.error(f"unknown command: {args.command}")  # argparse exits; unreachable
    return 2
