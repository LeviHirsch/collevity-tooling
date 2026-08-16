"""Recipient resolution: the address space, and the three calls behind it.

These tests are the executable form of the T6 decisions — no liveness filter,
newest-wins with ambiguity surfaced, and exact-else-nearest-descendant matching.
If one of them starts failing, a decision was changed rather than a bug found.

Run: python3 -m pytest tests/ -q   (stdlib only, no venv needed)
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

MODULE = Path(__file__).resolve().parent.parent / "bin" / "mailman_resolve.py"

_spec = importlib.util.spec_from_file_location("mailman_resolve", MODULE)
mr = importlib.util.module_from_spec(_spec)
# Registered before exec: `@dataclass` looks the defining module up in
# sys.modules, and a path-loaded module that is not there fails to define one.
sys.modules["mailman_resolve"] = mr
_spec.loader.exec_module(mr)

NOW = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)


def rec(session_id: str, cwd, *, minutes_ago: float = 0, kind="claude-session", at=None):
    """One roster line. `minutes_ago` is relative to a fixed NOW."""
    return {
        "session_id": session_id,
        "cwd": str(cwd),
        "kind": kind,
        "event": "startup",
        "registered_at": at
        if at is not None
        else (NOW - timedelta(minutes=minutes_ago)).isoformat(),
    }


# --- matching -------------------------------------------------------------


def test_exact_match_resolves(tmp_path):
    proj = tmp_path / "proj"
    got = mr.resolve(proj, records=[rec("s1", proj)])
    assert got.session_id == "s1"
    assert got.exact
    assert not got.ambiguous


def test_exact_match_shuts_out_descendants(tmp_path):
    """A session sitting exactly at the address wins outright — a newer
    session one level down must not displace it."""
    root = tmp_path / "repo"
    got = mr.resolve(
        root,
        records=[
            rec("at-root", root, minutes_ago=60),
            rec("below", root / "sub", minutes_ago=1),
        ],
    )
    assert got.session_id == "at-root"
    assert [c.session_id for c in got.candidates] == ["at-root"]


def test_descendant_matches_when_nothing_is_exact(tmp_path):
    root = tmp_path / "repo"
    got = mr.resolve(root, records=[rec("below", root / "sub" / "deeper")])
    assert got.session_id == "below"
    assert not got.exact
    assert got.candidates[0].depth == 2


def test_nearest_descendant_beats_a_deeper_newer_one(tmp_path):
    root = tmp_path / "repo"
    got = mr.resolve(
        root,
        records=[
            rec("deep", root / "a" / "b" / "c", minutes_ago=1),
            rec("shallow", root / "a", minutes_ago=90),
        ],
    )
    assert got.session_id == "shallow"
    assert [c.depth for c in got.candidates] == [1, 3]


def test_an_address_below_a_session_does_not_match(tmp_path):
    """The reverse direction was deliberately left out: addressing a subdir
    must not reach a session parked at the parent."""
    root = tmp_path / "repo"
    assert mr.resolve(root / "sub", records=[rec("parent", root)]) is None


def test_sibling_directories_do_not_match(tmp_path):
    assert mr.resolve(tmp_path / "a", records=[rec("s1", tmp_path / "b")]) is None


def test_no_match_returns_none(tmp_path):
    assert mr.resolve(tmp_path / "empty", records=[]) is None


def test_paths_are_normalized_before_comparison(tmp_path):
    """Trailing slashes and `..` are noise, not a different address."""
    proj = tmp_path / "proj"
    proj.mkdir()
    records = [rec("s1", f"{proj}/")]
    assert mr.resolve(f"{proj}/", records=records).session_id == "s1"
    assert mr.resolve(proj / "sub" / "..", records=records).session_id == "s1"


# --- tiebreak and ambiguity ----------------------------------------------


def test_two_sessions_at_one_cwd_pick_newest_and_flag_ambiguity(tmp_path):
    proj = tmp_path / "proj"
    got = mr.resolve(
        proj, records=[rec("older", proj, minutes_ago=30), rec("newer", proj)]
    )
    assert got.session_id == "newer"
    assert got.ambiguous
    assert [c.session_id for c in got.candidates] == ["newer", "older"]


def test_single_match_is_not_ambiguous(tmp_path):
    proj = tmp_path / "proj"
    assert not mr.resolve(proj, records=[rec("s1", proj)]).ambiguous


def test_excluded_session_is_never_the_recipient(tmp_path):
    """A sender addressing its own project directory should reach the other
    session there, not itself."""
    proj = tmp_path / "proj"
    got = mr.resolve(
        proj,
        records=[rec("me", proj), rec("them", proj, minutes_ago=5)],
        exclude="me",
    )
    assert got.session_id == "them"
    assert not got.ambiguous


def test_excluding_the_only_match_resolves_to_nothing(tmp_path):
    proj = tmp_path / "proj"
    assert mr.resolve(proj, records=[rec("me", proj)], exclude="me") is None


# --- roster reduction -----------------------------------------------------


def test_repeated_registrations_collapse_to_one_candidate(tmp_path):
    """SessionStart fires on resume and clear too; that is one session, and
    the newest line is the one that describes it."""
    old = tmp_path / "old"
    new = tmp_path / "new"
    got = mr.resolve(
        new,
        records=[rec("s1", old, minutes_ago=120), rec("s1", new, minutes_ago=2)],
    )
    assert got.session_id == "s1"
    assert len(got.candidates) == 1
    assert got.candidates[0].cwd == mr.normalize(new)


def test_a_stale_registration_is_still_resolvable(tmp_path):
    """No liveness filter — T16 drains queued notes at session start, so a
    dormant session is a valid recipient rather than a black hole."""
    proj = tmp_path / "proj"
    ancient = (NOW - timedelta(days=45)).isoformat()
    got = mr.resolve(proj, records=[rec("s1", proj, at=ancient)])
    assert got.session_id == "s1"


def test_records_missing_session_id_or_cwd_are_skipped(tmp_path):
    proj = tmp_path / "proj"
    records = [
        {"cwd": str(proj), "registered_at": NOW.isoformat()},
        {"session_id": "no-cwd", "registered_at": NOW.isoformat()},
        {"session_id": "", "cwd": str(proj)},
        rec("good", proj),
    ]
    got = mr.resolve(proj, records=records)
    assert [c.session_id for c in got.candidates] == ["good"]


def test_unparseable_timestamp_loses_recency_without_crashing(tmp_path):
    proj = tmp_path / "proj"
    got = mr.resolve(
        proj, records=[rec("broken", proj, at="not a date"), rec("fine", proj)]
    )
    assert [c.session_id for c in got.candidates] == ["fine", "broken"]


def test_a_lone_broken_timestamp_still_resolves(tmp_path):
    proj = tmp_path / "proj"
    assert mr.resolve(proj, records=[rec("s1", proj, at="")]).session_id == "s1"
    assert mr.resolve(proj, records=[rec("s1", proj, at=17)]).session_id == "s1"


# --- reading the roster file ---------------------------------------------


def test_missing_roster_reads_as_empty(tmp_path):
    assert mr.read_roster(tmp_path / "nope.jsonl") == []


def test_torn_lines_are_skipped_not_fatal(tmp_path):
    """The roster lives in a disposable dir; one garbled line must not take
    resolution down with it."""
    proj = tmp_path / "proj"
    roster = tmp_path / "roster.jsonl"
    roster.write_text(
        "\n".join(
            [
                json.dumps(rec("good", proj)),
                "{ half a line",
                "",
                "[1, 2, 3]",
                json.dumps(rec("also-good", proj, minutes_ago=10)),
            ]
        )
        + "\n"
    )
    records = mr.read_roster(roster)
    assert [r["session_id"] for r in records] == ["good", "also-good"]


def test_roster_path_follows_the_cache_env(tmp_path, monkeypatch):
    monkeypatch.setenv("MAILMAN_CACHE", str(tmp_path))
    assert mr.roster_path() == tmp_path / "roster.jsonl"


# --- CLI ------------------------------------------------------------------


def run_cli(args, cache: Path):
    return subprocess.run(
        [sys.executable, str(MODULE), *args],
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "HOME": str(cache), "MAILMAN_CACHE": str(cache)},
        timeout=10,
    )


def test_cli_prints_the_resolved_session_id(tmp_path):
    proj = tmp_path / "proj"
    (tmp_path / "roster.jsonl").write_text(json.dumps(rec("s1", proj)) + "\n")
    r = run_cli([str(proj)], tmp_path)
    assert r.returncode == 0
    assert r.stdout.strip() == "s1"


def test_cli_exits_nonzero_when_nothing_matches(tmp_path):
    (tmp_path / "roster.jsonl").write_text("")
    r = run_cli([str(tmp_path / "proj")], tmp_path)
    assert r.returncode == 1
    assert r.stdout.strip() == ""


def test_cli_json_carries_the_ambiguity_flag(tmp_path):
    proj = tmp_path / "proj"
    (tmp_path / "roster.jsonl").write_text(
        json.dumps(rec("older", proj, minutes_ago=30))
        + "\n"
        + json.dumps(rec("newer", proj))
        + "\n"
    )
    r = run_cli([str(proj), "--json"], tmp_path)
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["session_id"] == "newer"
    assert payload["ambiguous"] is True
    assert len(payload["candidates"]) == 2
