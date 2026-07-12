"""The Collevity Data Lake — storage seam over the append-dominant JSONL pool.

This module IS the seam (AC2.3, DEC-005): `append_entry` / `edit_entry` /
`read_day` / `sync_sources` are the *only* documented way to touch the lake.
Nothing else reads or writes the JSONL file directly — that rule keeps the
logical schema swappable up the JSONL → SQLite → Postgres ladder (the physical
edit primitive differs — line-rewrite here, `UPDATE` on Postgres — behind the
same logical `edit_entry`). The seam-only rule is a convention verified by code
review/grep, not runtime-enforced in v1 (AC2.3).

Physical model: append-dominant JSONL (DEC-005, DEC-006):
  - append-on-drop → one new line (`append_entry`)
  - edit-in-place  → rewrite the matching line, no revision history (`edit_entry`)

The lake (the data) is one text file — one entry per line. The default location
is dev-only; a real deployment sets COLLEVITY_LAKE to a stable path outside the
code tree (the data outlives the code).
"""

from __future__ import annotations

import fcntl
import json
import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date as date_cls, datetime
from pathlib import Path

import uuid6

from .schema import validate

# --- id minting (AC1.2, DEC-010, DEC-021) ----------------------------------
# UUIDv7 is not in the stdlib `uuid` module (slated for 3.14). `uuid6.uuid7()`
# returns a stdlib `uuid.UUID`, so the value drops natively into a future
# Postgres `uuid` column. This is the ONLY place ids are minted; surfaces never
# mint the canonical id.

def _mint_id() -> str:
    """Return a fresh UUIDv7 as a canonical string (AC1.2)."""
    return str(uuid6.uuid7())


# --- pool location ----------------------------------------------------------
# Resolution order: explicit arg → COLLEVITY_LAKE env var → package default.
# The default keeps the lake next to this part for dev; a real deployment points
# COLLEVITY_LAKE at a stable path *outside* the code tree.
_ENV_VAR = "COLLEVITY_LAKE"
_DEFAULT_POOL = Path(__file__).resolve().parents[2] / "data" / "collevity_lake.jsonl"


def _resolve_pool(pool_path: str | os.PathLike | None) -> Path:
    if pool_path is not None:
        return Path(pool_path)
    env = os.environ.get(_ENV_VAR)
    return Path(env) if env else _DEFAULT_POOL


# --- writer lock (D3, hook-spec DEC-015) ------------------------------------
# Global hook scope makes concurrent writers realistic (two Claude Code sessions
# appending at once). A plain `open("a")` + single write is *usually* atomic on
# local APFS, but that guarantee is informal and weakens under iCloud (DEC-022).
# All mutation paths therefore serialize on one advisory flock. The lock target
# is a stable sidecar file (`<pool>.lock`), NOT the pool itself — `_rewrite_all`
# swaps the pool's inode via os.replace, which would silently orphan a lock held
# on the old inode. Advisory = only seam writers honor it; readers stay lock-free
# (os.replace keeps reads torn-free, matching today's behavior).

@contextmanager
def _pool_lock(pool: Path):
    """Hold an exclusive advisory lock for one mutation (append/rewrite)."""
    pool.parent.mkdir(parents=True, exist_ok=True)
    lockfile = pool.with_suffix(pool.suffix + ".lock")
    with lockfile.open("a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


# --- low-level JSONL i/o (private; the seam funcs are the public surface) ---

def _read_all(pool: Path) -> list[dict]:
    if not pool.exists():
        return []
    entries: list[dict] = []
    with pool.open("r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                entries.append(json.loads(raw))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{pool}:{lineno}: corrupt JSONL line: {exc}") from exc
    return entries


def _append_line(pool: Path, entry: dict) -> None:
    # Unlocked primitive — callers hold `_pool_lock` (locking here would
    # deadlock callers that already hold it: flock treats a second fd on the
    # same file as an independent, conflicting lock).
    pool.parent.mkdir(parents=True, exist_ok=True)
    with pool.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _rewrite_all(pool: Path, entries: list[dict]) -> None:
    """Atomically rewrite the whole pool (temp file + os.replace).

    O(n) per edit — cheap and correct at single-user scale (DEC-011). Atomic
    replace avoids a torn file if the write is interrupted (a small mitigation
    for the iCloud/multi-surface edit window flagged in DEC-006).

    Unlocked primitive — callers hold `_pool_lock` across their whole
    read-modify-write, otherwise a concurrent append lands on the old inode
    between `_read_all` and `os.replace` and is silently lost (D3).
    """
    pool.parent.mkdir(parents=True, exist_ok=True)
    tmp = pool.with_suffix(pool.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    os.replace(tmp, pool)


# --- the seam: write + edit (AC2) ------------------------------------------

def append_entry(entry: dict, pool_path: str | os.PathLike | None = None) -> str:
    """Append a floor-bearing entry; mint and return its canonical id (AC2.1).

    The caller supplies `text`, `created_at`, `source`, `author` (+ any optional
    fields) but NOT `id` — the id is minted here (AC1.2, DEC-010). Passing an
    `id` is an error: capture surfaces must not mint the canonical id.
    """
    if not isinstance(entry, dict):
        raise TypeError(f"entry must be a dict, got {type(entry).__name__}")
    if "id" in entry:
        raise ValueError(
            "do not supply 'id'; it is minted by the lake seam on append (AC1.2, DEC-010)"
        )

    record = dict(entry)  # copy — don't mutate the caller's dict
    record["id"] = _mint_id()
    validate(record)  # enforce the full field contract before it touches disk

    pool = _resolve_pool(pool_path)
    with _pool_lock(pool):  # serialize concurrent capture surfaces (D3)
        _append_line(pool, record)
    return record["id"]


def edit_entry(
    entry_id: str,
    changes: dict,
    pool_path: str | os.PathLike | None = None,
) -> dict:
    """Edit an existing entry in place by id (AC2.2).

    Applies `changes` (a partial field map) onto the entry with `entry_id` and
    rewrites that line. **In-place correction only**: no lineage_id, no revision
    history, no `modified`/`updated_at` bump (DEC-006). The `id` itself cannot be
    changed. Raises KeyError if no entry has that id.
    """
    if "id" in changes and changes["id"] != entry_id:
        raise ValueError("cannot change an entry's id")

    pool = _resolve_pool(pool_path)
    # Lock across the whole read-modify-write: a concurrent append between
    # _read_all and _rewrite_all would otherwise be silently dropped (D3).
    with _pool_lock(pool):
        entries = _read_all(pool)

        found = False
        for i, entry in enumerate(entries):
            if entry.get("id") == entry_id:
                updated = {**entry, **changes, "id": entry_id}
                validate(updated)
                entries[i] = updated
                found = True
                break
        if not found:
            raise KeyError(f"no entry with id {entry_id!r}")

        _rewrite_all(pool, entries)
    return entries[i]


# --- the seam: check-in read (AC3) -----------------------------------------

def _local_day(created_at: str) -> date_cls:
    """The local-day-of-offset for a `created_at` string (AC3.2).

    `datetime.fromisoformat` keeps the parsed value in its own offset; `.date()`
    is therefore the local wall-clock day, NOT the UTC day — so an evening drop
    stamped `-04:00` lands on its own day, not the next UTC day (success (d)).
    """
    return datetime.fromisoformat(created_at).date()


def _local_time_hm(created_at: str) -> str:
    """Local wall-clock time as 'HH:MM' for the read_day output (AC3.1).

    Parity confirmed (DEC-013, /spec verify iteration 1): the legacy reader
    `~/.claude/skills/checkin/read_dropper_day.py:62` emits each entry's time via
    `dt.strftime('%H:%M')` — identical to the shape here. (The script lives in the
    /checkin skill folder, outside this repo, which is why earlier passes could
    not see it.) read_day surfaces the same {text, time} fields the old reader did.
    """
    return datetime.fromisoformat(created_at).strftime("%H:%M")


def read_day(
    day: str | date_cls,
    pool_path: str | os.PathLike | None = None,
) -> list[dict]:
    """Return ``[{"text", "time"}, ...]`` for entries made on `day` (AC3.1).

    A **pure retrieval**: no ingestion, no write side-effects (DEC-018). A
    consumer needing current data composes `sync_sources()` then `read_day()` —
    `read_day` makes no freshness guarantee (DEC-019). Entries are bucketed by
    **local-day-of-offset** `created_at` (AC3.2) and returned sorted by time.

    `day` may be a `datetime.date` or an ISO date string ('YYYY-MM-DD').

    Ordering is **sub-minute** (D1, hook-spec DEC-013): rows sort by the full
    parsed `created_at` (aware datetimes — correct even across mixed offsets),
    not by the displayed 'HH:MM' string, so two hook captures inside the same
    minute keep their true order. The surfaced `time` stays 'HH:MM' (legacy
    /checkin parity, DEC-013 verify); full precision is surfaced additively via
    each row's `created_at` passthrough.
    """
    target = day if isinstance(day, date_cls) else date_cls.fromisoformat(day)

    matches = [
        e
        for e in _read_all(_resolve_pool(pool_path))
        if _local_day(e["created_at"]) == target
    ]
    matches.sort(key=lambda e: datetime.fromisoformat(e["created_at"]))
    return [
        {
            "text": e["text"],
            "time": _local_time_hm(e["created_at"]),
            "created_at": e["created_at"],
        }
        for e in matches
    ]


# --- the seam: pull-ingest boundary (AC5.1, DEC-018) -----------------------
# `sync_sources()` brings the lake current from PULL-based external capture
# sources before a read. Native PUSH surfaces (writing directly via
# `append_entry`) need no sync. Pull-based capture is a permanent design need, so
# this seam is permanent — but its registered ingesters come and go.
#
# Freshness is a consumer-composition contract (DEC-019): `read_day` makes no
# standalone freshness guarantee, so a consumer composes `sync_sources()` then
# `read_day()`. Staleness is neither surfaced nor enforced here.
#
# PHASE 1 SCOPE: boundary only — NO ingesters registered yet, so this is a
# well-defined no-op reporting zero work. The Excel bridge (Phase 2 / AC4–AC5.2)
# becomes the single v1 ingester; it is wired in at the marked extension point
# below. Per DEC-018/AC5.2 there is deliberately NO multi-source registry in v1.


@dataclass(frozen=True)
class SyncResult:
    """Outcome of a `sync_sources` run."""

    sources_synced: int
    entries_ingested: int


def _compact_chronological(pool: Path) -> bool:
    """Settle-time compaction (D2, hook-spec DEC-012): sort the pool by
    `created_at` if it is out of order. Returns True iff a rewrite happened.

    Live push surfaces (the prompt-capture hook) append in arrival order; the
    Excel bridge batch-appends older-timestamped rows on sync — so between
    settles the physical file is not chronological. `created_at` stays the
    chronological source of truth; this just realigns the file with it so only
    the transient live tail (appends since the last settle) is ever unsorted.
    No-op (no rewrite, no mtime churn) when already sorted — the common case.
    Sort is stable, so exact-tie stamps keep their arrival order.
    """
    with _pool_lock(pool):  # settle is a read-modify-write (D3)
        entries = _read_all(pool)
        keys = [datetime.fromisoformat(e["created_at"]) for e in entries]
        if keys == sorted(keys):
            return False
        entries.sort(key=lambda e: datetime.fromisoformat(e["created_at"]))
        _rewrite_all(pool, entries)
        return True


def sync_sources() -> SyncResult:
    """Bring pull-based sources current.

    v1 has exactly one registered ingester — the Excel bridge (AC4/AC5.2). There
    is deliberately NO multi-source registry (DEC-018): the bridge is wired in by
    one explicit, lazy import below. The import tolerates the bridge being absent,
    so deleting `bridges/` retires the ingester and reverts this to a zero-work
    no-op with no edit here (AC4.5 clean-delete). `read_day` stays a pure read;
    this op is the only place ingest happens (DEC-018).
    """
    # --- Phase 2 extension point -------------------------------------------
    # The single v1 ingester (the Excel bridge, AC4/AC5.2). One explicit call,
    # no registry. Lazy import keeps the core Excel-blind and makes the bridge
    # cleanly deletable: ImportError → nothing to sync (back to the Phase-1 no-op).
    try:
        from .bridges import excel
    except ImportError:
        return SyncResult(sources_synced=0, entries_ingested=0)
    # -----------------------------------------------------------------------
    if not excel.source_present():
        # Bridge registered, but no Dropper to pull → zero ingest work; still
        # settle (live-tail appends may be unsorted even with nothing to pull).
        _compact_chronological(_resolve_pool(None))
        return SyncResult(sources_synced=0, entries_ingested=0)
    ingested = excel.ingest()
    # Settle (D2): batch-ingested older rows land after newer live-tail appends;
    # restore physical chronological order before the consumer's read.
    _compact_chronological(_resolve_pool(None))
    return SyncResult(sources_synced=1, entries_ingested=ingested)
