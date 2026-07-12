#!/usr/bin/env python3
"""Prompt-capture hook — Claude Code `UserPromptSubmit` → Collevity lake.

Pure plumbing (DEC-001): reads the hook payload from stdin, appends one entry
to the live lake via the seam's `append_entry`, and gets out of the way. No
LLM, no filtering (DEC-002), no ordering duty beyond stamping an accurate
high-precision local-offset `created_at` (DEC-011/012).

FAIL-OPEN IS THE PRIME DIRECTIVE (AC4, hook-spec open-Q2 finding):
for `UserPromptSubmit`, exit code 2 BLOCKS AND ERASES the user's prompt, and
any stdout on exit 0 is injected into the conversation. So this script must
— on every path, including its own bugs — exit 0 with empty stdout. The only
failure breadcrumb is a best-effort line in the error sidecar (AC4.3, DEC-009);
a failure of the sidecar write is itself swallowed.

Environment (set explicitly by the installed hook command, spec open-Q4):
  COLLEVITY_LAKE          — path to the live lake JSONL (required in practice;
                            without it the seam falls back to its dev default,
                            which is never what the live install wants).
  COLLEVITY_HOOK_ERRLOG   — optional sidecar path override; defaults to
                            `capture_errors.log` next to this script.

Payload keys: current Claude Code docs deliver the prompt text as `prompt`;
the 2026-06-30 spec interview recorded `user_prompt` (open-Q2 says verify at
rollout). The hook accepts either — tolerant reading beats a version gamble,
and the mandatory one-time rollout check (echo raw stdin once) still applies.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

_SIDECAR_ENV = "COLLEVITY_HOOK_ERRLOG"


def _sidecar_path() -> Path:
    env = os.environ.get(_SIDECAR_ENV)
    if env:
        return Path(env)
    return Path(__file__).resolve().parent / "capture_errors.log"


def _breadcrumb(summary: str) -> None:
    """Best-effort one-line diagnostic (AC4.3). Its own failure is swallowed."""
    try:
        stamp = datetime.now().astimezone().isoformat(timespec="seconds")
        with _sidecar_path().open("a", encoding="utf-8") as fh:
            fh.write(f"{stamp} — {summary}\n")
    except Exception:
        pass  # the sidecar must never become a second way to fail (AC4.3)


def _capture() -> None:
    payload = json.load(sys.stdin)

    text = payload.get("prompt", payload.get("user_prompt"))
    if not isinstance(text, str) or not text:
        raise ValueError(f"no prompt text in payload keys {sorted(payload)}")

    # High-precision local-offset stamp (AC2.2, DEC-011): microseconds + the
    # host's current UTC offset, stamped at capture.
    created_at = datetime.now().astimezone().isoformat()

    entry = {
        "text": text,  # verbatim (AC2.1)
        "created_at": created_at,
        "source": "claude-hook",  # AC2.3
        "author": "user",  # AC2.4
        "context": {  # reserved claude-hook shape (AC2.5/2.6, DEC-008)
            "kind": "claude-session",
            "session_id": str(payload.get("session_id") or ""),
            "cwd": str(payload.get("cwd") or ""),
        },
    }
    if not entry["context"]["session_id"] or not entry["context"]["cwd"]:
        raise ValueError(f"missing session_id/cwd in payload keys {sorted(payload)}")

    # Imported inside the guarded path: an import error is a capture failure
    # too (AC4.1) and must not block the prompt.
    from collevity.lake import append_entry

    append_entry(entry)  # lake resolved via COLLEVITY_LAKE; id minted by seam


def main() -> int:
    try:
        _capture()
    except Exception as exc:  # noqa: BLE001 — fail-open by contract (AC4.1)
        _breadcrumb(f"{type(exc).__name__}: {exc}")
    return 0  # ALWAYS 0, ALWAYS silent — never block/erase the prompt (AC4)


if __name__ == "__main__":
    sys.exit(main())
