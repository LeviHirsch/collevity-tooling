"""The `use` command: sequential interactive switch (spec AC5).

A whole-environment interactive switch is a reauth, not a token swap (DEC-004):
``use <label>`` invokes ``claude auth login --email <stored-email>`` (the
``--email`` flag is verified in active use — DEC-010) and the user completes the
reauth natively in the browser. The tool's only side effect is whatever
``claude auth login`` writes — it never touches ``~/.claude.json`` or any
Keychain entry directly (AC5.2).

Before handing off, the tool echoes the intended ``label (email)`` and a one-line
reminder to verify that account on the consent page. The ``--email`` flag only
*prefills* the address; the browser/Chrome profile may still be logged into a
different account, so the consent-page check (as at ``add`` time, AC2.3) remains
the authority on which account is actually authorized.
"""

from __future__ import annotations

import subprocess
from typing import Callable, Optional, Sequence

from . import setup_token
from .io import ConsoleIO, IO
from .run import normalize_exit_code
from .store import Store

#: Exit code when the label is unknown (AC5.3 — fails before any auth subcommand).
NO_SUCH_LABEL = 2

#: Exit code when the claude binary itself cannot be launched.
COMMAND_NOT_FOUND = 127

# A launcher runs the auth-login argv and returns its raw exit code (may be
# negative if signal-killed — normalized by the caller). The real one inherits
# the terminal so the native reauth flow is fully interactive; tests mock it.
Launcher = Callable[[Sequence[str]], int]


def _real_login(cmd: Sequence[str]) -> int:
    """Run ``cmd`` inheriting this process's stdio (interactive reauth)."""
    return subprocess.run(list(cmd)).returncode


def run_use(
    label: str,
    *,
    store: Optional[Store] = None,
    io: Optional[IO] = None,
    launcher: Optional[Launcher] = None,
    claude_bin: Optional[str] = None,
) -> int:
    """Switch the interactive login to ``label`` via reauth. Returns an exit code.

    AC5.3: an unknown label fails here, before any auth subcommand runs, with a
    clear error listing the available labels.
    """
    store = store if store is not None else Store()
    io = io if io is not None else ConsoleIO()
    launcher = launcher if launcher is not None else _real_login
    claude_bin = claude_bin if claude_bin is not None else setup_token.CLAUDE_BIN

    # AC5.3 — resolve the label BEFORE invoking any auth subcommand.
    record = store.read(label)
    if record is None:
        labels = store.labels()
        if labels:
            io.error(
                f"no slot named {label!r}. Available labels: {', '.join(labels)}"
            )
        else:
            io.error(
                f"no slot named {label!r}. No slots exist yet — run 'cas add' first."
            )
        return NO_SUCH_LABEL

    # Echo the intended identity + the consent-page right-account reminder. Goes
    # to stderr so it never mingles with anything the auth flow writes to stdout.
    io.notice(f"switching to {label} ({record.email})")
    io.notice(
        f"on the consent page, confirm it shows {record.email} before approving — "
        "the browser may be logged into a different account."
    )

    # AC5.1 — the reauth-based whole-environment switch. AC5.2: the only side
    # effect is whatever 'claude auth login' itself writes; cas mutates nothing.
    cmd = [claude_bin, "auth", "login", "--email", record.email]
    try:
        returncode = launcher(cmd)
    except FileNotFoundError:
        io.error(f"could not launch '{claude_bin} auth login': command not found")
        return COMMAND_NOT_FOUND

    return normalize_exit_code(returncode)
