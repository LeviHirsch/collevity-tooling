"""Prompt-capture hook — Phase 1 ACs, exercised as Claude Code would run it.

Every test invokes `capture_prompt.py` as a real subprocess with the payload on
stdin — the actual `UserPromptSubmit` contract — never by importing it. That is
the only honest way to test AC4 (exit code + stdout discipline).

Env per test: COLLEVITY_LAKE → tmp lake, COLLEVITY_HOOK_ERRLOG → tmp sidecar,
PYTHONPATH → the fork's jsonl-schema (where `collevity` lives).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "hook" / "capture_prompt.py"
FORK_SCHEMA = Path(__file__).resolve().parents[2] / "jsonl-schema"

sys.path.insert(0, str(FORK_SCHEMA))
from collevity.lake import read_day  # noqa: E402
from collevity.lake.schema import validate  # noqa: E402


def run_hook(payload: dict | str, lake: Path, sidecar: Path, **env_over) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "COLLEVITY_LAKE": str(lake),
        "COLLEVITY_HOOK_ERRLOG": str(sidecar),
        "PYTHONPATH": str(FORK_SCHEMA),
    }
    env.update(env_over)
    stdin = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


@pytest.fixture
def lake(tmp_path):
    return tmp_path / "lake.jsonl"


@pytest.fixture
def sidecar(tmp_path):
    return tmp_path / "capture_errors.log"


def payload(**over) -> dict:
    p = {
        "session_id": "sess-abc123",
        "cwd": "/Users/levi/somewhere",
        "hook_event_name": "UserPromptSubmit",
        "prompt": "hello lake",
    }
    p.update(over)
    return p


def read_lake(lake: Path) -> list[dict]:
    if not lake.exists():
        return []
    return [json.loads(l) for l in lake.read_text().splitlines() if l.strip()]


# --- AC1.2 / AC3.1: nominal capture -----------------------------------------

def test_nominal_run_exits_0_silent_and_persists(lake, sidecar):
    before = datetime.now().astimezone()
    res = run_hook(payload(), lake, sidecar)
    after = datetime.now().astimezone()

    assert res.returncode == 0  # AC1.2
    assert res.stdout == ""  # AC4.2 — stdout is injected into the conversation
    entries = read_lake(lake)
    assert len(entries) == 1  # AC3.1 — one line per invocation
    e = entries[0]
    validate(e)  # passes the schema's validate()

    # AC2.1 verbatim text; AC2.3/2.4 source/author; AC2.5 context shape
    assert e["text"] == "hello lake"
    assert e["source"] == "claude-hook"
    assert e["author"] == "user"
    assert e["context"] == {
        "kind": "claude-session",
        "session_id": "sess-abc123",
        "cwd": "/Users/levi/somewhere",
    }
    # AC2.6 — store mints id; nothing else leaks in
    assert set(e) == {"id", "text", "created_at", "source", "author", "context"}

    # AC2.2 — ISO-8601, explicit offset, microsecond precision, stamped now
    assert re.search(r"\.\d{6}[+-]\d{2}:\d{2}$", e["created_at"])
    stamped = datetime.fromisoformat(e["created_at"])
    assert before <= stamped <= after
    assert stamped.utcoffset() == before.utcoffset()  # host's current offset

    assert not sidecar.exists()  # no breadcrumb on success


def test_text_is_verbatim_unicode_and_multiline(lake, sidecar):
    gnarly = "line one\nline two — naïve 한국어 🙂 \"quotes\" \\backslash\t"
    res = run_hook(payload(prompt=gnarly), lake, sidecar)
    assert res.returncode == 0
    assert read_lake(lake)[0]["text"] == gnarly  # AC2.1 — no escaping artifacts


def test_accepts_legacy_user_prompt_key(lake, sidecar):
    """Spec open-Q2 recorded `user_prompt`; current docs say `prompt`. Accept both."""
    p = payload()
    p["user_prompt"] = p.pop("prompt")
    res = run_hook(p, lake, sidecar)
    assert res.returncode == 0
    assert read_lake(lake)[0]["text"] == "hello lake"


def test_surfaces_via_read_day(lake, sidecar):  # AC5.1 (Phase-2 AC, testable now)
    run_hook(payload(prompt="findable"), lake, sidecar)
    today = datetime.now().astimezone().date()
    rows = read_day(today, pool_path=lake)
    assert [r["text"] for r in rows] == ["findable"]


# --- AC4: fail-open on every failure path ------------------------------------

def assert_failopen(res, sidecar, lake):
    assert res.returncode == 0  # never 2 — 2 blocks AND erases the prompt
    assert res.stdout == ""  # never inject into the conversation
    assert read_lake(lake) == []  # nothing (partial) written
    assert sidecar.exists() and len(sidecar.read_text().splitlines()) == 1  # AC4.3


def test_unwritable_lake_is_swallowed_with_breadcrumb(tmp_path, sidecar):
    ro = tmp_path / "ro"
    ro.mkdir()
    lake = ro / "lake.jsonl"
    ro.chmod(0o500)  # read+exec, no write
    try:
        res = run_hook(payload(), lake, sidecar)
    finally:
        ro.chmod(0o700)
    assert_failopen(res, sidecar, lake)


def test_garbage_stdin_is_swallowed(lake, sidecar):
    res = run_hook("this is not json {", lake, sidecar)
    assert_failopen(res, sidecar, lake)


def test_missing_prompt_key_is_swallowed(lake, sidecar):
    p = payload()
    del p["prompt"]
    res = run_hook(p, lake, sidecar)
    assert_failopen(res, sidecar, lake)


def test_missing_session_id_is_swallowed(lake, sidecar):
    res = run_hook(payload(session_id=""), lake, sidecar)
    assert_failopen(res, sidecar, lake)


def test_broken_import_is_swallowed(lake, sidecar):
    """PYTHONPATH without the collevity package → import error → still exit 0."""
    res = run_hook(payload(), lake, sidecar, PYTHONPATH="/nonexistent")
    assert_failopen(res, sidecar, lake)


def test_sidecar_failure_is_itself_swallowed(tmp_path, lake):
    """AC4.3: the breadcrumb is best-effort — an unwritable sidecar must not
    create a second failure mode."""
    res = run_hook(
        "not json either",
        lake,
        tmp_path / "no-such-dir" / "deeper" / "err.log",
    )
    assert res.returncode == 0
    assert res.stdout == ""


def test_stderr_never_carries_a_traceback(lake, sidecar):
    """Belt-and-braces: failures must not spew tracebacks (stderr is shown to
    the user in verbose mode)."""
    res = run_hook("garbage", lake, sidecar)
    assert "Traceback" not in res.stderr
