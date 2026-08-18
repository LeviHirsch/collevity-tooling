"""Published session views: what they carry, who may overwrite what, and the
fail-open contract the two hooks that write them must keep.

Run: python3 -m pytest tests/ -q   (stdlib only, no venv needed)
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

BIN = Path(__file__).resolve().parent.parent / "bin"
sys.path.insert(0, str(BIN))

import mailman_view  # noqa: E402

STOP_HOOK = BIN / "mailman_publish.py"
PROMPT_HOOK = BIN / "mailman_check.py"


@pytest.fixture()
def cache(tmp_path, monkeypatch):
    """Redirect view state into a tmp dir — never the real ~/.collevity."""
    monkeypatch.setenv("MAILMAN_CACHE", str(tmp_path / "mailman"))
    for name in ("CLAUDE_SESSION_ID", "GROK_SESSION_ID", "COLLEVITY_HOOK_SOURCE"):
        monkeypatch.delenv(name, raising=False)
    return tmp_path / "mailman"


def run_hook(hook: Path, stdin_text: str, cache_dir: Path, env_extra=None):
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": "/tmp/mailman-test-home",
        "MAILMAN_CACHE": str(cache_dir),
        "MAILMAN_HOOK_ERRLOG": str(cache_dir / "sidecar.log"),
    }
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(hook)],
        input=stdin_text,
        capture_output=True,
        text=True,
        env=env,
    )


# ---------- what a view carries ----------


def test_touch_writes_the_mechanical_fields(cache):
    view = mailman_view.touch("s-1", cwd="/tmp/project", kind="claude-session")
    assert view.session_id == "s-1"
    assert view.cwd == "/tmp/project"
    assert view.kind == "claude-session"
    assert view.updated_at
    # Nothing has been said about the session yet.
    assert not view.described
    assert view.reported_at == ""


def test_report_writes_the_semantic_fields(cache):
    mailman_view.touch("s-1", cwd="/tmp/project", kind="claude-session")
    view = mailman_view.report(
        "s-1", topic="Mailman protocol", recap="Settled addressing", working_on="T18"
    )
    assert view.topic == "Mailman protocol"
    assert view.recap == "Settled addressing"
    assert view.working_on == "T18"
    assert view.reported_at
    assert view.described


def test_report_only_changes_the_fields_it_is_given(cache):
    mailman_view.report("s-1", topic="Mailman", recap="early", working_on="T13")
    view = mailman_view.report("s-1", working_on="T18")
    assert view.working_on == "T18"
    assert view.topic == "Mailman"
    assert view.recap == "early"


def test_report_with_an_empty_string_clears_a_field(cache):
    mailman_view.report("s-1", working_on="T18")
    view = mailman_view.report("s-1", working_on="")
    assert view.working_on == ""


def test_report_needs_at_least_one_field(cache):
    with pytest.raises(mailman_view.ViewError):
        mailman_view.report("s-1")


# ---------- the hooks must never clobber what the session said ----------


def test_touch_preserves_the_semantic_fields(cache):
    mailman_view.report("s-1", topic="Mailman", recap="a recap", working_on="T18")
    view = mailman_view.touch("s-1", cwd="/tmp/project", kind="claude-session")
    assert view.topic == "Mailman"
    assert view.recap == "a recap"
    assert view.working_on == "T18"


def test_touch_moves_updated_at_but_not_reported_at(cache):
    reported = mailman_view.report("s-1", topic="Mailman")
    touched = mailman_view.touch("s-1", cwd="/tmp/project")
    assert touched.reported_at == reported.reported_at
    assert touched.updated_at >= reported.updated_at


def test_touch_keeps_known_cwd_when_the_payload_omits_it(cache):
    mailman_view.touch("s-1", cwd="/tmp/project", kind="claude-session")
    view = mailman_view.touch("s-1")
    assert view.cwd == "/tmp/project"
    assert view.kind == "claude-session"


# ---------- reading ----------


def test_read_view_is_none_before_anything_is_published(cache):
    assert mailman_view.read_view("nobody") is None


def test_read_all_views_is_freshest_first(cache):
    mailman_view.touch("s-old", cwd="/tmp/a")
    mailman_view.touch("s-new", cwd="/tmp/b")
    ids = [v.session_id for v in mailman_view.read_all_views()]
    assert ids[0] == "s-new"
    assert set(ids) == {"s-old", "s-new"}


def test_read_all_views_is_empty_when_nothing_is_published(cache):
    assert mailman_view.read_all_views() == []


def test_a_corrupt_view_is_skipped_not_fatal(cache):
    mailman_view.touch("s-good", cwd="/tmp/a")
    bad = mailman_view.views_dir() / "s-bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert [v.session_id for v in mailman_view.read_all_views()] == ["s-good"]


def test_unknown_fields_in_a_view_are_dropped(cache):
    mailman_view.touch("s-1", cwd="/tmp/a")
    path = mailman_view.view_path("s-1")
    data = json.loads(path.read_text(encoding="utf-8"))
    data["something_new"] = "from a later version"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert mailman_view.read_view("s-1").session_id == "s-1"


def test_an_unparseable_timestamp_reads_as_maximally_stale(cache):
    mailman_view.touch("s-1", cwd="/tmp/a")
    path = mailman_view.view_path("s-1")
    data = json.loads(path.read_text(encoding="utf-8"))
    data["updated_at"] = "not a timestamp"
    path.write_text(json.dumps(data), encoding="utf-8")
    view = mailman_view.read_view("s-1")
    assert mailman_view.age_seconds(view) > 0


def test_age_seconds_grows_with_a_stale_view(cache):
    mailman_view.touch("s-1", cwd="/tmp/a")
    view = mailman_view.read_view("s-1")
    later = datetime.now(timezone.utc) + timedelta(seconds=120)
    assert mailman_view.age_seconds(view, now=later) >= 120


# ---------- a session id must not steer the write ----------


@pytest.mark.parametrize("bad", ["", "../escape", "a/b", ".", ".."])
def test_a_path_like_session_id_is_refused(cache, bad):
    with pytest.raises(mailman_view.ViewError):
        mailman_view.view_path(bad)


# ---------- self-identification ----------


def test_resolve_prefers_an_explicit_session_id(cache, monkeypatch):
    monkeypatch.setenv("CLAUDE_SESSION_ID", "from-env")
    assert mailman_view.resolve_session_id("explicit") == "explicit"


def test_resolve_falls_back_to_the_environment(cache, monkeypatch):
    monkeypatch.setenv("CLAUDE_SESSION_ID", "from-env")
    assert mailman_view.resolve_session_id() == "from-env"


def test_resolve_finds_the_lone_session_in_this_directory(cache, tmp_path):
    here = tmp_path / "project"
    here.mkdir()
    mailman_view.touch("s-1", cwd=str(here))
    assert mailman_view.resolve_session_id(cwd=str(here)) == "s-1"


def test_resolve_refuses_to_guess_between_two_sessions_here(cache, tmp_path):
    here = tmp_path / "project"
    here.mkdir()
    mailman_view.touch("s-1", cwd=str(here))
    mailman_view.touch("s-2", cwd=str(here))
    with pytest.raises(mailman_view.ViewError) as exc:
        mailman_view.resolve_session_id(cwd=str(here))
    assert "s-1" in str(exc.value) and "s-2" in str(exc.value)


def test_resolve_says_so_when_nothing_publishes_here(cache, tmp_path):
    with pytest.raises(mailman_view.ViewError):
        mailman_view.resolve_session_id(cwd=str(tmp_path))


# ---------- the Stop hook ----------


def test_stop_hook_publishes_a_view(cache):
    payload = json.dumps({"session_id": "s-1", "cwd": "/tmp/project"})
    result = run_hook(STOP_HOOK, payload, cache)
    assert result.returncode == 0
    assert result.stdout == ""
    view = json.loads((cache / "views" / "s-1.json").read_text(encoding="utf-8"))
    assert view["cwd"] == "/tmp/project"
    assert view["kind"] == "claude-session"


def test_stop_hook_reads_the_grok_envelope(cache):
    payload = json.dumps({"sessionId": "s-grok", "cwd": "/tmp/project"})
    result = run_hook(STOP_HOOK, payload, cache)
    assert result.returncode == 0
    view = json.loads((cache / "views" / "s-grok.json").read_text(encoding="utf-8"))
    assert view["kind"] == "grok-session"


def test_stop_hook_does_not_clobber_what_the_session_said(cache):
    mailman_view.report("s-1", topic="Mailman", working_on="T18")
    run_hook(STOP_HOOK, json.dumps({"session_id": "s-1", "cwd": "/tmp/p"}), cache)
    view = json.loads((cache / "views" / "s-1.json").read_text(encoding="utf-8"))
    assert view["topic"] == "Mailman"
    assert view["working_on"] == "T18"


@pytest.mark.parametrize(
    "stdin_text",
    ["", "not json at all", "[]", '{"cwd": "/tmp/p"}', '{"session_id": ""}'],
)
def test_stop_hook_exits_zero_and_silent_on_bad_input(cache, stdin_text):
    result = run_hook(STOP_HOOK, stdin_text, cache)
    assert result.returncode == 0
    assert result.stdout == ""


def test_stop_hook_exits_zero_when_the_state_dir_is_unwritable(cache, tmp_path):
    blocked = tmp_path / "blocked"
    blocked.write_text("not a directory", encoding="utf-8")
    result = run_hook(
        STOP_HOOK, json.dumps({"session_id": "s-1", "cwd": "/tmp/p"}), blocked
    )
    assert result.returncode == 0
    assert result.stdout == ""


# ---------- the prompt hook keeps its own contract while doing this ----------


def test_prompt_hook_publishes_a_view(cache):
    payload = json.dumps({"session_id": "s-1", "cwd": "/tmp/project"})
    result = run_hook(PROMPT_HOOK, payload, cache)
    assert result.returncode == 0
    assert result.stdout == ""
    assert (cache / "views" / "s-1.json").exists()


@pytest.mark.parametrize(
    "stdin_text",
    ["", "not json at all", "[]", '{"session_id": "../escape", "cwd": "/tmp/p"}'],
)
def test_prompt_hook_still_exits_zero_and_silent_on_bad_input(cache, stdin_text):
    result = run_hook(PROMPT_HOOK, stdin_text, cache)
    assert result.returncode == 0
    assert result.stdout == ""


def test_a_view_file_with_an_unusable_stem_is_skipped(cache):
    mailman_view.touch("s-good", cwd="/tmp/a")
    # `.json` alone has stem "." — `view_path` refuses it, and scanning the
    # directory must survive that rather than raise mid-listing.
    (mailman_view.views_dir() / ".json").write_text("{}", encoding="utf-8")
    assert [v.session_id for v in mailman_view.read_all_views()] == ["s-good"]
    assert mailman_view.read_view("../escape") is None
