"""The `list` command: slot-registry display (spec AC4).

Prints one aligned row per stored label — label, bound email, and the oat's age
in human-readable units (AC4.1) — and marks which label (if any) matches the
*current interactive login* (AC4.2). The active marker is an arrow in a
two-column left gutter so the active vs inactive distinction is unambiguous in a
plain terminal with no flag or pipe (AC4.3).

The active-login match is the ONE sanctioned ``claude auth status`` call against
the **default** config dir (AC4.2): the interactive (non-oat) path returns an
``email`` field, which we match against stored records. This is NOT a scripted
email lookup against an oat slot — the oat is ``user:inference`` scope only and
returns no email (DEC-001), so ``list`` never queries a slot for it. The probe
runs with ``CLAUDE_CONFIG_DIR`` and ``CLAUDE_CODE_OAUTH_TOKEN`` stripped from the
child env so it always measures the genuine default-dir interactive session.

Parsing is deliberately tolerant and never raises (mirrors
:func:`cas.setup_token.parse_auth_status`): a missing binary, a logged-out
session, or unparseable output all degrade to "no match", which appends the
"no active interactive login matched" note rather than failing the command.
"""

from __future__ import annotations

import datetime
import os
import re
import subprocess
from typing import Callable, Optional

from . import setup_token
from .io import ConsoleIO, IO
from .store import Record, Store

#: Gutter shown to the left of every row: the active row gets the arrow.
_GUTTER_ACTIVE = "→ "
_GUTTER_PLAIN = "  "

#: A column gap of two spaces between fields.
_GAP = "  "

# An explicit ``email`` field is preferred; a bare address is the fallback. Both
# are matched case-insensitively and normalized to lowercase for comparison.
_EMAIL_BODY = r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"
_EMAIL_FIELD_RE = re.compile(r'"?email"?\s*[:=]\s*"?(' + _EMAIL_BODY + r")", re.IGNORECASE)
_EMAIL_ANY_RE = re.compile(_EMAIL_BODY)


def _today() -> datetime.date:
    return datetime.date.today()


# --- pure helpers (unit-tested directly) -----------------------------------

def humanize_age(mint_date: str, today: datetime.date) -> str:
    """Render the oat's age from ``mint_date`` (ISO date) in days (AC4.1).

    Returns ``"today"`` for a same-day (or clock-skewed future) mint, ``"1 day"``
    singular, ``"N days"`` otherwise, and ``"unknown"`` for an unparseable date —
    so a malformed record still renders a row rather than crashing ``list``.
    """
    try:
        minted = datetime.date.fromisoformat(mint_date)
    except (ValueError, TypeError):
        return "unknown"
    days = (today - minted).days
    if days <= 0:
        return "today"
    if days == 1:
        return "1 day"
    return f"{days} days"


def parse_login_email(stdout: str, stderr: str) -> Optional[str]:
    """Extract the interactive login's email from ``auth status`` output (AC4.2).

    Prefers an explicit ``email`` field; falls back to the first bare address.
    Returns a lowercased address, or ``None`` if none is present. Tolerant of
    JSON or human formatting; never raises.
    """
    text = f"{stdout}\n{stderr}"
    m = _EMAIL_FIELD_RE.search(text)
    if m:
        return m.group(1).lower()
    m = _EMAIL_ANY_RE.search(text)
    return m.group(0).lower() if m else None


def format_listing(
    records: dict[str, Record],
    active_labels: set[str],
    today: datetime.date,
) -> str:
    """Render the aligned table (AC4.1/4.3). Assumes a non-empty ``records``."""
    rows = [
        (label, records[label].email, humanize_age(records[label].mint_date, today))
        for label in sorted(records)
    ]
    w_label = max(len("LABEL"), *(len(r[0]) for r in rows))
    w_email = max(len("EMAIL"), *(len(r[1]) for r in rows))

    lines = [
        _GUTTER_PLAIN
        + "LABEL".ljust(w_label)
        + _GAP
        + "EMAIL".ljust(w_email)
        + _GAP
        + "AGE"
    ]
    for label, email, age in rows:
        gutter = _GUTTER_ACTIVE if label in active_labels else _GUTTER_PLAIN
        lines.append(gutter + label.ljust(w_label) + _GAP + email.ljust(w_email) + _GAP + age)
    return "\n".join(lines)


# --- the live default-dir probe (mocked in tests) --------------------------

def default_login_email(claude_bin: Optional[str] = None) -> Optional[str]:
    """Run ``claude auth status`` against the default config dir; return its email.

    AC4.2: strips ``CLAUDE_CONFIG_DIR`` and ``CLAUDE_CODE_OAUTH_TOKEN`` from the
    child env so the probe always reflects the genuine default-dir interactive
    login (never a slot's oat). Returns ``None`` (never raises) on a missing
    binary, timeout, logged-out session, or unparseable output.
    """
    claude_bin = claude_bin if claude_bin is not None else setup_token.CLAUDE_BIN
    env = dict(os.environ)
    env.pop("CLAUDE_CONFIG_DIR", None)
    env.pop("CLAUDE_CODE_OAUTH_TOKEN", None)
    try:
        proc = subprocess.run(
            [claude_bin, "auth", "status"],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    return parse_login_email(proc.stdout, proc.stderr)


# --- the command -----------------------------------------------------------

def run_list(
    *,
    store: Optional[Store] = None,
    io: Optional[IO] = None,
    login_email: Optional[Callable[[], Optional[str]]] = None,
    today: Optional[Callable[[], datetime.date]] = None,
) -> int:
    """Print the slot registry. Returns 0 always (display is never an error)."""
    store = store if store is not None else Store()
    io = io if io is not None else ConsoleIO()
    login_email = login_email if login_email is not None else default_login_email
    today = today if today is not None else _today

    records = store.all()
    if not records:
        io.info("no slots yet — run 'cas add' to create one.")
        return 0

    # AC4.2 — the one sanctioned default-dir probe; degrade to no match.
    current = login_email()
    current_norm = current.strip().lower() if current else None
    active_labels = (
        {label for label, rec in records.items() if rec.email.strip().lower() == current_norm}
        if current_norm
        else set()
    )

    io.info(format_listing(records, active_labels, today()))
    if not active_labels:
        io.info("")
        io.info("(no active interactive login matched)")
    return 0
