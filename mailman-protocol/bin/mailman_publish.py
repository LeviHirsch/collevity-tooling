#!/usr/bin/env python3
"""Mailman view refresh on turn end — Claude Code + Grok `Stop`.

Refreshes this session's published view when an agent turn finishes (T18).
`mailman_check.py` already does the same on `UserPromptSubmit`; this covers the
gap that trigger leaves. A session in a long autonomous run never submits a
prompt, so without a `Stop` entry its view would not move until the next one.
That is last activity, not liveness — an idle open session is still alive.

WHY THIS DOES NOT WAIT ON T14

T14 is a spike on what *injection* each hook event supports — whether stdout
from `Stop` reaches model context, and whether blocking there loops. This hook
injects nothing. It writes a file and exits, so the unverified path is not on
its route.

SAFETY CONTRACT

Same posture as the other installed hooks: exit 0 on every path including this
script's own bugs, and write nothing to stdout. On `Stop` a non-zero exit is
read as blocking the turn, which is not something a view refresh may ever do.

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

# Imported defensively: an ImportError at module level would escape `main()`'s
# handler and exit non-zero. A missing view module costs a stale view, never a
# blocked turn.
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import mailman_view  # noqa: E402 — needs the path above; hooks run from anywhere
except Exception:  # noqa: BLE001 — fail-open by contract
    mailman_view = None

_SIDECAR_ENV = "MAILMAN_HOOK_ERRLOG"
_DEBUG_ENV = "MAILMAN_DEBUG"


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


def _publish() -> None:
    payload = json.load(sys.stdin)
    if not isinstance(payload, dict):
        raise ValueError(f"payload must be a JSON object, got {type(payload).__name__}")

    session_id = _first_str(payload, "session_id", "sessionId")
    cwd = _first_str(payload, "cwd")
    if not session_id:
        raise ValueError(f"missing session_id in payload keys {sorted(payload)}")
    if mailman_view is None:
        raise RuntimeError("mailman_view unavailable")

    # Mechanical fields only. topic/recap/working_on belong to the session's
    # own agent and must survive every refresh.
    mailman_view.touch(session_id, cwd=cwd, kind=mailman_view.harness_kind(payload))

    if os.environ.get(_DEBUG_ENV) == "1":
        _breadcrumb(f"published view for {session_id} at {cwd or '?'}")


def main() -> int:
    try:
        _publish()
    except Exception as exc:  # noqa: BLE001 — fail-open by contract
        _breadcrumb(f"{type(exc).__name__}: {exc}")
    return 0  # ALWAYS 0, ALWAYS silent


if __name__ == "__main__":
    sys.exit(main())
