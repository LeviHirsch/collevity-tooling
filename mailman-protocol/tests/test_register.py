"""Session registration: the record it writes, and the contract it keeps.

Run: python3 -m pytest tests/ -q   (stdlib only, no venv needed)
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "bin" / "mailman_register.py"


def run(stdin_text: str, cache: Path, env_extra: dict[str, str] | None = None):
    """Invoke the hook with state redirected into a tmp dir — never the
    real ~/.collevity, and never the repo working tree."""
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": "/tmp/mailman-test-home",
        "MAILMAN_CACHE": str(cache),
        "MAILMAN_HOOK_ERRLOG": str(cache / "sidecar.log"),
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


def roster(cache: Path) -> list[dict]:
    p = cache / "roster.jsonl"
    if not p.exists():
        return []
    return [json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()]


CLAUDE = json.dumps(
    {"session_id": "abc-123", "cwd": "/tmp/proj", "source": "startup"}
)
GROK = json.dumps({"sessionId": "def-456", "cwd": "/tmp/other"})


def test_claude_session_is_registered(tmp_path):
    r = run(CLAUDE, tmp_path)
    assert r.returncode == 0
    assert r.stdout == ""
    rows = roster(tmp_path)
    assert len(rows) == 1
    assert rows[0]["session_id"] == "abc-123"
    assert rows[0]["cwd"] == "/tmp/proj"
    assert rows[0]["kind"] == "claude-session"
    assert rows[0]["event"] == "startup"
    assert rows[0]["registered_at"]


def test_grok_camelcase_is_detected(tmp_path):
    run(GROK, tmp_path)
    rows = roster(tmp_path)
    assert rows[0]["kind"] == "grok-session"
    assert rows[0]["session_id"] == "def-456"


def test_roster_dir_is_created_when_absent(tmp_path):
    nested = tmp_path / "does" / "not" / "exist"
    r = run(CLAUDE, nested)
    assert r.returncode == 0
    assert (nested / "roster.jsonl").exists()


def test_repeated_starts_append_rather_than_replace(tmp_path):
    """SessionStart fires on resume and clear too — several records per
    session is expected, and readers take the newest."""
    run(CLAUDE, tmp_path)
    run(json.dumps({"session_id": "abc-123", "cwd": "/tmp/proj", "source": "resume"}),
        tmp_path)
    rows = roster(tmp_path)
    assert len(rows) == 2
    assert [r["event"] for r in rows] == ["startup", "resume"]


def test_two_sessions_coexist(tmp_path):
    run(CLAUDE, tmp_path)
    run(GROK, tmp_path)
    rows = roster(tmp_path)
    assert {r["session_id"] for r in rows} == {"abc-123", "def-456"}


def test_every_line_is_valid_json(tmp_path):
    for _ in range(5):
        run(CLAUDE, tmp_path)
    raw = (tmp_path / "roster.jsonl").read_text().splitlines()
    assert len(raw) == 5
    for line in raw:
        json.loads(line)  # raises if a concurrent-style append corrupted a line


def test_malformed_payload_writes_nothing_and_exits_zero(tmp_path):
    r = run("{not json", tmp_path)
    assert r.returncode == 0
    assert r.stdout == ""
    assert roster(tmp_path) == []


def test_payload_without_session_id_is_tolerated(tmp_path):
    r = run(json.dumps({"cwd": "/tmp/proj"}), tmp_path)
    assert r.returncode == 0
    assert r.stdout == ""
    assert roster(tmp_path) == [], "an unidentifiable session must not be recorded"


def test_unwritable_roster_does_not_raise(tmp_path):
    r = run(CLAUDE, Path("/proc/nonexistent/nope"))
    assert r.returncode == 0
    assert r.stdout == ""


def test_debug_breadcrumb_is_verifiable(tmp_path):
    r = run(CLAUDE, tmp_path, {"MAILMAN_DEBUG": "1"})
    assert r.returncode == 0
    assert "abc-123" in (tmp_path / "sidecar.log").read_text()
