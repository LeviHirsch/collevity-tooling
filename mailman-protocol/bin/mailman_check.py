#!/usr/bin/env python3
"""Mailman scripted check — Claude Code + Grok `UserPromptSubmit`.

**This is the T7 stub.** It occupies the hook slot and proves the slot is safe.
It reads the payload, does nothing with it, and exits. Note reading, injection,
and the receive-rule are T2; this script deliberately does not implement them.

Why a stub ships first: this is the third hook on a *live* prompt path that
already carries `capture_prompt.py` and `sync_lake.py`. Proving a new entry can
sit there without disturbing either is worth doing before any logic exists.

THE SAFETY CONTRACT (inherited from the prompt-capture hook, which verified it):

  On Claude `UserPromptSubmit`, **exit code 2 blocks and ERASES the user's
  prompt**, and any stdout on exit 0 is **injected into the conversation**.

So:
  * This script exits 0 on every path, including its own bugs.
  * The stub writes nothing to stdout, ever.
  * When T2 adds injection, stdout becomes deliberate — but the exit code
    stays 0. "The scripted check can stop the turn" in the design notes means
    *the check does no further work*; it must never mean exit 2. Erasing a
    prompt Levi just typed is not an acceptable failure mode for a note
    delivery system.

Envelope normalization: Claude sends snake_case (`session_id`), Grok sends
camelCase (`sessionId`) and reaches this same install through Claude-settings
hook compatibility. Both are accepted — mailman is Claude<->Grok by decision
(T8), not by accident.

State locations (decided 2026-08-16, see README):
  roster  ~/.collevity/cache/mailman/roster.jsonl   disposable (T13)
  notes   ~/.collevity/mailman/notes.jsonl          durable    (T1)

`cache/` is declared disposable by `~/.collevity/README.md`; presence is
correctly losable, an unread note is not.

Environment:
  MAILMAN_HOME          — durable state dir. Default `~/.collevity/mailman`.
  MAILMAN_CACHE         — disposable state dir.
                          Default `~/.collevity/cache/mailman`.
  MAILMAN_HOOK_ERRLOG   — sidecar path override. Defaults to
                          `mailman_errors.log` next to this script.
  MAILMAN_DEBUG         — set to 1 to breadcrumb every run, so a fresh install
                          can be verified without waiting for a failure.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

_SIDECAR_ENV = "MAILMAN_HOOK_ERRLOG"
_DEBUG_ENV = "MAILMAN_DEBUG"

DEFAULT_HOME = Path.home() / ".collevity" / "mailman"
DEFAULT_CACHE = Path.home() / ".collevity" / "cache" / "mailman"


def home_dir() -> Path:
    """Durable mailman state (notes, read-state). Not under cache/."""
    return Path(os.environ.get("MAILMAN_HOME") or DEFAULT_HOME)


def cache_dir() -> Path:
    """Disposable mailman state (roster). Safe to delete."""
    return Path(os.environ.get("MAILMAN_CACHE") or DEFAULT_CACHE)


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
        pass  # the sidecar must never become a second way to fail


def _first_str(payload: dict, *keys: str) -> str:
    for k in keys:
        v = payload.get(k)
        if isinstance(v, str) and v:
            return v
    return ""


def read_payload() -> dict:
    """Parse the hook envelope from stdin. Raises on anything unexpected."""
    payload = json.load(sys.stdin)
    if not isinstance(payload, dict):
        raise ValueError(f"payload must be a JSON object, got {type(payload).__name__}")
    return payload


def session_of(payload: dict) -> tuple[str, str]:
    """(session_id, cwd) from either envelope shape. Empty strings if absent."""
    return (
        _first_str(payload, "session_id", "sessionId"),
        _first_str(payload, "cwd"),
    )


def _check() -> None:
    payload = read_payload()
    session_id, cwd = session_of(payload)

    # T2 implements the actual check here: read the notes file, find anything
    # addressed to this session, and write it to stdout with the receive-rule.
    # The stub stops at knowing who it is.

    if os.environ.get(_DEBUG_ENV) == "1":
        _breadcrumb(f"stub ran — session={session_id or '?'} cwd={cwd or '?'}")


def main() -> int:
    try:
        _check()
    except Exception as exc:  # noqa: BLE001 — fail-open by contract
        _breadcrumb(f"{type(exc).__name__}: {exc}")
    return 0  # ALWAYS 0 — exit 2 would erase the user's prompt


if __name__ == "__main__":
    sys.exit(main())
