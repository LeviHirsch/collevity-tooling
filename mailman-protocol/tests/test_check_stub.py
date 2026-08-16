"""The safety contract for the mailman check hook.

These tests exist because the failure mode is severe and silent: on Claude
`UserPromptSubmit`, a non-zero exit blocks and erases the prompt the user just
typed, and stray stdout is injected into their conversation. Every case below
feeds the hook something hostile and asserts it still exits 0 with clean stdout.

Run: python3 -m pytest tests/ -q   (stdlib only, no venv needed)
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "bin" / "mailman_check.py"


def run(stdin_text: str, env_extra: dict[str, str] | None = None, sidecar=None):
    """Invoke the hook. The sidecar is always redirected out of the repo —
    a test run must not leave a log file in the working tree."""
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": "/tmp/mailman-test-home",
        "MAILMAN_HOOK_ERRLOG": str(sidecar or "/tmp/mailman-test-sidecar.log"),
    }
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=stdin_text,
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )


CLAUDE = json.dumps(
    {"session_id": "abc-123", "cwd": "/tmp/proj", "prompt": "hello"}
)
GROK = json.dumps(
    {"sessionId": "def-456", "cwd": "/tmp/proj", "hookEventName": "UserPromptSubmit"}
)


def test_claude_envelope_is_silent_and_zero():
    r = run(CLAUDE)
    assert r.returncode == 0
    assert r.stdout == ""


def test_grok_envelope_is_silent_and_zero():
    r = run(GROK)
    assert r.returncode == 0
    assert r.stdout == ""


def test_malformed_json_does_not_block_the_prompt():
    r = run("{not json at all")
    assert r.returncode == 0, "a parse error must never erase the user's prompt"
    assert r.stdout == ""


def test_empty_stdin_does_not_block_the_prompt():
    r = run("")
    assert r.returncode == 0
    assert r.stdout == ""


def test_json_that_is_not_an_object_is_tolerated():
    r = run("[1, 2, 3]")
    assert r.returncode == 0
    assert r.stdout == ""


def test_payload_missing_every_expected_key_is_tolerated():
    r = run(json.dumps({"unexpected": True}))
    assert r.returncode == 0
    assert r.stdout == ""


def test_unwritable_sidecar_is_swallowed():
    """A failing breadcrumb must not become a second way to fail."""
    r = run("{bad", {"MAILMAN_HOOK_ERRLOG": "/proc/nonexistent/nope.log"})
    assert r.returncode == 0
    assert r.stdout == ""


def test_debug_breadcrumb_writes_to_the_sidecar(tmp_path):
    log = tmp_path / "mailman_errors.log"
    r = run(CLAUDE, {"MAILMAN_DEBUG": "1", "MAILMAN_HOOK_ERRLOG": str(log)})
    assert r.returncode == 0
    assert r.stdout == ""
    assert "abc-123" in log.read_text(), "debug run should be verifiable"
