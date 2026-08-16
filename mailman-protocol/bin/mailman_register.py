#!/usr/bin/env python3
"""Mailman session registration — Claude Code + Grok `SessionStart`.

Announces that a session exists: its id, its working directory, and which
harness it is. That roster is what makes a note addressable by *project
directory* rather than by uuid — the T6 decision — without having to infer
liveness from last-prompt-in-the-lake.

Scope: registration only. Delivering notes that queued while a session was away
is T16; resolving a cwd to a recipient is T6. This script writes one line and
stops.

WHERE IT WRITES

  ~/.collevity/cache/mailman/roster.jsonl

Under `cache/` deliberately. `~/.collevity/README.md` declares that dir
disposable — "deleting a tool's dir costs at most one redundant resync" — and
that is exactly right for session presence: a stale roster should be losable and
rebuildable, because every live session re-registers on its next start. Notes
live at `~/.collevity/mailman/` instead, because an unread note is data loss
rather than a resync (T1).

APPEND-ONLY, LATEST-WINS

Sessions start concurrently, so this appends rather than rewrites: a single
short `write()` of one line, which is the same discipline the lake uses. Readers
reduce by `session_id` and take the newest record. `SessionStart` also fires on
resume and clear, so several records per session over time is normal and
expected — not a duplicate to guard against.

Stale entries are not pruned here. The dir is disposable and the reader takes
the newest record; retention is a later concern, not a registration concern.

SAFETY CONTRACT

Same posture as `mailman_check.py`: exit 0 on every path including this
script's own bugs, and write nothing to stdout. Registration has nothing to
inject, and the injection semantics of `SessionStart` are unverified (T14) —
the existing `SessionStart` entry backgrounds itself and discards stdout, so
nothing in this setup has ever proven what reaches context from there.

The hook entry is nonetheless installed in the **foreground**, unlike
`catchup.sh`. Registration alone does not need that; T16 will, and plumbing it
correctly once is cheaper than re-plumbing later.

Environment:
  MAILMAN_CACHE         — disposable state dir.
                          Default `~/.collevity/cache/mailman`.
  MAILMAN_HOOK_ERRLOG   — sidecar path override. Defaults to
                          `mailman_errors.log` next to this script.
  MAILMAN_DEBUG         — set to 1 to breadcrumb every run.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

_SIDECAR_ENV = "MAILMAN_HOOK_ERRLOG"
_DEBUG_ENV = "MAILMAN_DEBUG"
_SOURCE_ENV = "COLLEVITY_HOOK_SOURCE"

DEFAULT_CACHE = Path.home() / ".collevity" / "cache" / "mailman"
ROSTER_NAME = "roster.jsonl"


def cache_dir() -> Path:
    return Path(os.environ.get("MAILMAN_CACHE") or DEFAULT_CACHE)


def roster_path() -> Path:
    return cache_dir() / ROSTER_NAME


def _sidecar_path() -> Path:
    env = os.environ.get(_SIDECAR_ENV)
    if env:
        return Path(env)
    return Path(__file__).resolve().parent / "mailman_errors.log"


def _breadcrumb(summary: str) -> None:
    """Best-effort one-line diagnostic. Its own failure is swallowed."""
    try:
        stamp = datetime.now().astimezone().isoformat(timespec="seconds")
        with _sidecar_path().open("a", encoding="utf-8") as fh:
            fh.write(f"{stamp} — {summary}\n")
    except Exception:
        pass  # never a second way to fail


def _first_str(payload: dict, *keys: str) -> str:
    for k in keys:
        v = payload.get(k)
        if isinstance(v, str) and v:
            return v
    return ""


def detect_harness(payload: dict) -> str:
    """'grok' | 'claude'. Mirrors the prompt-capture hook's detection.

    Grok reaches this install through Claude-settings hook compatibility and
    sends camelCase; `sessionId` without `session_id` is the decisive marker.
    """
    forced = (os.environ.get(_SOURCE_ENV) or "").strip().lower()
    if forced in ("grok-hook", "grok"):
        return "grok"
    if forced in ("claude-hook", "claude"):
        return "claude"
    if "sessionId" in payload and "session_id" not in payload:
        return "grok"
    if os.environ.get("GROK_SESSION_ID") or os.environ.get("GROK_HOOK_EVENT"):
        return "grok"
    return "claude"


def build_record(payload: dict) -> dict:
    """One roster line. Raises when the payload cannot identify a session."""
    session_id = _first_str(payload, "session_id", "sessionId")
    cwd = _first_str(payload, "cwd")
    if not session_id or not cwd:
        raise ValueError(f"missing session_id/cwd in payload keys {sorted(payload)}")

    kind = "grok-session" if detect_harness(payload) == "grok" else "claude-session"
    return {
        "session_id": session_id,
        "cwd": cwd,
        "kind": kind,
        # startup | resume | clear, when the harness says so
        "event": _first_str(payload, "source", "sessionSource"),
        "registered_at": datetime.now().astimezone().isoformat(),
    }


def append_record(record: dict, path: Path | None = None) -> Path:
    """Append one JSON line to the roster, creating the dir if needed."""
    target = path or roster_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False) + "\n"
    # One short append; O_APPEND keeps concurrent session starts from
    # interleaving mid-line.
    with target.open("a", encoding="utf-8") as fh:
        fh.write(line)
    return target


def _register() -> None:
    payload = json.load(sys.stdin)
    if not isinstance(payload, dict):
        raise ValueError(f"payload must be a JSON object, got {type(payload).__name__}")

    record = build_record(payload)
    append_record(record)

    if os.environ.get(_DEBUG_ENV) == "1":
        _breadcrumb(
            f"registered {record['kind']} {record['session_id']} at {record['cwd']}"
        )


def main() -> int:
    try:
        _register()
    except Exception as exc:  # noqa: BLE001 — fail-open by contract
        _breadcrumb(f"{type(exc).__name__}: {exc}")
    return 0  # ALWAYS 0, ALWAYS silent


if __name__ == "__main__":
    sys.exit(main())
