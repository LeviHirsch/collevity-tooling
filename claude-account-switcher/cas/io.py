"""Interactive prompt surface for the `add` flow (spec AC2.3, AC2.6, AC2.8).

The flow never calls ``input``/``print`` directly: it goes through an :class:`IO`
so the Phase 2 tests can drive the retype-confirm, profile pick, and collision
loop with scripted answers and capture every line shown to the user.
``ConsoleIO`` is the real terminal binding (DEC-015: argparse/stdlib, zero deps).
"""

from __future__ import annotations

import sys
from typing import Optional, Sequence


class IO:
    """Abstract prompt/echo surface. Subclass to bind to a terminal or a test."""

    def info(self, msg: str = "") -> None:  # normal output (stdout)
        raise NotImplementedError

    def warn(self, msg: str) -> None:  # non-fatal notice (stderr)
        raise NotImplementedError

    def error(self, msg: str) -> None:  # fatal notice (stderr)
        raise NotImplementedError

    def prompt(self, msg: str) -> str:  # free-text line of input
        raise NotImplementedError

    def confirm(self, msg: str) -> bool:  # an explicit yes/no keystroke
        raise NotImplementedError

    def choose(self, msg: str, options: Sequence[str]) -> Optional[int]:
        """Pick one of ``options`` (return its index) or decline (return ``None``)."""
        raise NotImplementedError


class ConsoleIO(IO):
    """Real terminal binding over stdlib ``input``/``print``."""

    def info(self, msg: str = "") -> None:
        print(msg)

    def warn(self, msg: str) -> None:
        print(f"warning: {msg}", file=sys.stderr)

    def error(self, msg: str) -> None:
        print(f"error: {msg}", file=sys.stderr)

    def prompt(self, msg: str) -> str:
        return input(msg)

    def confirm(self, msg: str) -> bool:
        # AC2.6 "explicit confirmation keystroke": default is No, so a stray
        # Enter never writes a record.
        ans = input(f"{msg} [y/N] ").strip().lower()
        return ans in ("y", "yes")

    def choose(self, msg: str, options: Sequence[str]) -> Optional[int]:
        print(msg)
        for i, opt in enumerate(options, 1):
            print(f"  {i}) {opt}")
        print("  0) none / I'll open it myself")
        while True:
            raw = input("Select [0]: ").strip() or "0"
            if raw == "0":
                return None
            if raw.isdigit() and 1 <= int(raw) <= len(options):
                return int(raw) - 1
            print("invalid selection; try again")
