#!/usr/bin/env python3
"""Prompt-capture hook — Claude Code + Grok `UserPromptSubmit` → Collevity lake.

Shared capture surface for both harnesses (one script, one seam write).

Pure plumbing (DEC-001): reads the hook payload from stdin, appends one entry
to the live lake via the seam's `append_entry`, and gets out of the way. No
LLM, no filtering (DEC-002), no ordering duty beyond stamping an accurate
high-precision local-offset `created_at` (DEC-011/012).

Envelope normalization:
  Claude Code typically sends snake_case (`session_id`, `hook_event_name`, …).
  Grok sends camelCase (`sessionId`, `hookEventName`, …) and already invokes
  this same install via Claude-settings hook compatibility. Both shapes are
  accepted; `source` / `context.kind` reflect the harness.

FAIL-OPEN IS THE PRIME DIRECTIVE (AC4, hook-spec open-Q2 finding):
for Claude `UserPromptSubmit`, exit code 2 BLOCKS AND ERASES the user's prompt,
and any stdout on exit 0 is injected into the conversation. So this script must
— on every path, including its own bugs — exit 0 with empty stdout. The only
failure breadcrumb is a best-effort line in the error sidecar (AC4.3, DEC-009);
a failure of the sidecar write is itself swallowed.

Environment (set explicitly by the installed hook command, spec open-Q4):
  COLLEVITY_LAKE          — path to the live lake JSONL (required in practice;
                            without it the seam falls back to its dev default,
                            which is never what the live install wants).
  COLLEVITY_HOOK_ERRLOG   — optional sidecar path override; defaults to
                            `capture_errors.log` next to this script.
  COLLEVITY_HOOK_SOURCE   — optional override for the entry `source` field
                            (`claude-hook` | `grok-hook`). When unset, inferred
                            from payload key shape / harness env.

Payload keys (tolerant):
  text:   `prompt` | `user_prompt`
  session:`session_id` | `sessionId`
  cwd:    `cwd` (both)
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

_SIDECAR_ENV = "COLLEVITY_HOOK_ERRLOG"
_SOURCE_ENV = "COLLEVITY_HOOK_SOURCE"


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


def _first_str(payload: dict, *keys: str) -> str:
    for k in keys:
        v = payload.get(k)
        if isinstance(v, str) and v:
            return v
    return ""


def _detect_harness(payload: dict) -> str:
    """Return 'grok' | 'claude' for source/kind tagging.

    Prefer explicit env; else payload shape (Grok camelCase sessionId);
    else harness env markers.
    """
    forced = (os.environ.get(_SOURCE_ENV) or "").strip().lower()
    if forced in ("grok-hook", "grok"):
        return "grok"
    if forced in ("claude-hook", "claude"):
        return "claude"
    # Grok envelope (verified live 2026-08-01 via sidecar fail-open breadcrumbs)
    if "sessionId" in payload or payload.get("hookEventName") in (
        "UserPromptSubmit",
        "user_prompt_submit",
        "beforeSubmitPrompt",
    ):
        # hookEventName alone is ambiguous if Claude ever camelCases; sessionId is decisive
        if "sessionId" in payload and "session_id" not in payload:
            return "grok"
    if os.environ.get("GROK_SESSION_ID") or os.environ.get("GROK_HOOK_EVENT"):
        return "grok"
    return "claude"


def _capture() -> None:
    payload = json.load(sys.stdin)
    if not isinstance(payload, dict):
        raise ValueError(f"payload must be a JSON object, got {type(payload).__name__}")

    text = _first_str(payload, "prompt", "user_prompt")
    if not text:
        raise ValueError(f"no prompt text in payload keys {sorted(payload)}")

    session_id = _first_str(payload, "session_id", "sessionId")
    cwd = _first_str(payload, "cwd")
    if not session_id or not cwd:
        raise ValueError(f"missing session_id/cwd in payload keys {sorted(payload)}")

    harness = _detect_harness(payload)
    if harness == "grok":
        source = "grok-hook"
        kind = "grok-session"
    else:
        source = "claude-hook"
        kind = "claude-session"

    # High-precision local-offset stamp (AC2.2, DEC-011): microseconds + the
    # host's current UTC offset, stamped at capture.
    created_at = datetime.now().astimezone().isoformat()

    entry = {
        "text": text,  # verbatim (AC2.1)
        "created_at": created_at,
        "source": source,  # AC2.3
        "author": "user",  # AC2.4
        "context": {  # reserved session shape (AC2.5/2.6, DEC-008)
            "kind": kind,
            "session_id": session_id,
            "cwd": cwd,
        },
    }

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
