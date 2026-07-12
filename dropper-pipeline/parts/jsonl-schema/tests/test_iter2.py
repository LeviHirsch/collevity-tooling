"""Iteration 2 — the hook-spec cross-part dependencies D1/D2/D3.

D1 — `read_day` orders sub-minute (hook-spec DEC-013): sort by full parsed
     `created_at`, not the displayed 'HH:MM' string.
D2 — `sync_sources` settles the pool chronologically (hook-spec DEC-012):
     batch-ingested older rows land after newer live-tail appends; settle
     rewrites the file sorted by `created_at` (atomic, no-op when sorted).
D3 — `append_entry` is safe under concurrent writers (hook-spec DEC-015):
     all mutations serialize on an advisory flock sidecar (`<pool>.lock`).
"""

from __future__ import annotations

import json
import multiprocessing
import sys
from pathlib import Path

import pytest

from collevity.lake import append_entry, edit_entry, read_day, sync_sources
from collevity.lake import lake as lake_mod
from collevity.lake.schema import validate


@pytest.fixture
def pool(tmp_path):
    return tmp_path / "entries.jsonl"


def floor(**overrides) -> dict:
    entry = {
        "text": "an entry",
        "created_at": "2026-06-24T12:00:00-04:00",
        "source": "test",
        "author": "user",
    }
    entry.update(overrides)
    return entry


# --- D1: sub-minute read order ----------------------------------------------

def test_read_day_orders_within_same_minute(pool):  # D1
    """Two captures in the same minute must keep true (sub-minute) order."""
    append_entry(
        floor(text="second", created_at="2026-06-24T09:05:42.500000-04:00"),
        pool_path=pool,
    )
    append_entry(
        floor(text="first", created_at="2026-06-24T09:05:03.100000-04:00"),
        pool_path=pool,
    )
    rows = read_day("2026-06-24", pool_path=pool)
    assert [r["text"] for r in rows] == ["first", "second"]
    # Displayed time stays minute-grain (legacy /checkin parity)…
    assert [r["time"] for r in rows] == ["09:05", "09:05"]
    # …full precision is surfaced additively.
    assert rows[0]["created_at"] == "2026-06-24T09:05:03.100000-04:00"


def test_read_day_orders_across_mixed_offsets(pool):  # D1
    """Ordering is by absolute time (aware datetimes), not string compare."""
    # 10:00-04:00 == 14:00Z; 13:30-01:00 == 14:30Z → -04:00 entry is earlier
    # even though '13:30' < '10:00' is false lexically and '-01:00' sorts odd.
    append_entry(
        floor(text="later", created_at="2026-06-24T13:30:00-01:00"), pool_path=pool
    )
    append_entry(
        floor(text="earlier", created_at="2026-06-24T10:00:00-04:00"), pool_path=pool
    )
    rows = read_day("2026-06-24", pool_path=pool)
    assert [r["text"] for r in rows] == ["earlier", "later"]


# --- D2: settle-time chronological compaction --------------------------------

def _raw_created_ats(pool: Path) -> list[str]:
    return [
        json.loads(line)["created_at"]
        for line in pool.read_text().splitlines()
        if line.strip()
    ]


def test_sync_settles_pool_chronologically(pool, monkeypatch):  # D2
    """Simulate the live shape: newer hook appends, then older rows appended
    (as the Excel bridge does on batch sync) → after sync_sources the *file*
    is chronological."""
    monkeypatch.setenv("COLLEVITY_LAKE", str(pool))
    append_entry(floor(created_at="2026-06-24T20:00:00-04:00"), pool_path=pool)
    append_entry(floor(created_at="2026-06-24T08:00:00-04:00"), pool_path=pool)
    append_entry(floor(created_at="2026-06-24T14:00:00-04:00"), pool_path=pool)
    assert _raw_created_ats(pool) != sorted(_raw_created_ats(pool))

    sync_sources()  # no Dropper present (conftest) — settle still runs

    ats = _raw_created_ats(pool)
    assert ats == sorted(ats)
    for line in pool.read_text().splitlines():  # still valid, floor-complete
        validate(json.loads(line))


def test_settle_is_noop_when_already_sorted(pool, monkeypatch):  # D2
    """The common case must not churn the file (no rewrite, no mtime bump)."""
    monkeypatch.setenv("COLLEVITY_LAKE", str(pool))
    append_entry(floor(created_at="2026-06-24T08:00:00-04:00"), pool_path=pool)
    append_entry(floor(created_at="2026-06-24T09:00:00-04:00"), pool_path=pool)

    calls: list[int] = []
    real = lake_mod._rewrite_all
    monkeypatch.setattr(
        lake_mod, "_rewrite_all", lambda *a, **k: (calls.append(1), real(*a, **k))
    )
    sync_sources()
    assert calls == []  # already chronological → zero-work settle


def test_settle_preserves_arrival_order_on_equal_stamps(pool, monkeypatch):  # D2
    monkeypatch.setenv("COLLEVITY_LAKE", str(pool))
    append_entry(floor(text="z-later-arrival", created_at="2026-06-24T09:00:00-04:00"), pool_path=pool)
    append_entry(floor(text="a-even-later", created_at="2026-06-24T09:00:00-04:00"), pool_path=pool)
    append_entry(floor(text="oldest", created_at="2026-06-24T08:00:00-04:00"), pool_path=pool)
    sync_sources()
    texts = [
        json.loads(l)["text"] for l in pool.read_text().splitlines() if l.strip()
    ]
    # Stable sort: the two equal 09:00 stamps keep arrival order.
    assert texts == ["oldest", "z-later-arrival", "a-even-later"]


# --- D3: concurrent-append safety ---------------------------------------------

def _hammer(pool_str: str, worker: int, n: int) -> None:
    """Worker: n appends to the shared pool. Top-level for spawn-picklability."""
    from collevity.lake import append_entry as ae  # re-import in child

    for i in range(n):
        ae(
            {
                "text": f"w{worker}-{i}-" + "x" * 200,  # long enough to tear
                "created_at": "2026-06-24T12:00:00.000001-04:00",
                "source": "test-concurrent",
                "author": "user",
            },
            pool_path=pool_str,
        )


def test_concurrent_appends_lose_and_tear_nothing(pool):  # D3
    procs, per = 6, 20
    ctx = multiprocessing.get_context("spawn")
    workers = [
        ctx.Process(target=_hammer, args=(str(pool), w, per)) for w in range(procs)
    ]
    for p in workers:
        p.start()
    for p in workers:
        p.join(timeout=60)
        assert p.exitcode == 0

    lines = [l for l in pool.read_text().splitlines() if l.strip()]
    assert len(lines) == procs * per  # nothing lost
    seen = set()
    for line in lines:
        entry = json.loads(line)  # nothing torn
        validate(entry)
        seen.add(entry["text"])
    assert len(seen) == procs * per  # every distinct append present


def test_edit_during_concurrent_appends_drops_nothing(pool):  # D3
    """edit_entry holds the lock across read-modify-write, so appends landing
    mid-edit are not lost to the rewrite's os.replace."""
    eid = append_entry(floor(text="target"), pool_path=pool)
    ctx = multiprocessing.get_context("spawn")
    p = ctx.Process(target=_hammer, args=(str(pool), 99, 30))
    p.start()
    for i in range(10):
        edit_entry(eid, {"text": f"target-edit-{i}"}, pool_path=pool)
    p.join(timeout=60)
    assert p.exitcode == 0

    lines = [l for l in pool.read_text().splitlines() if l.strip()]
    assert len(lines) == 1 + 30  # the edited entry + every concurrent append
    texts = {json.loads(l)["text"] for l in lines}
    assert "target-edit-9" in texts


def test_lockfile_is_sidecar_not_pool(pool):  # D3 mechanism
    append_entry(floor(), pool_path=pool)
    lock = pool.with_suffix(pool.suffix + ".lock")
    assert lock.exists()
    # The lockfile is not part of the pool's data: pool holds exactly 1 line.
    assert len(pool.read_text().splitlines()) == 1
