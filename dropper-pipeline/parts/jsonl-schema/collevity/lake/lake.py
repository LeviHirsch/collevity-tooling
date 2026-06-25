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

import json
import os
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
    pool.parent.mkdir(parents=True, exist_ok=True)
    with pool.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _rewrite_all(pool: Path, entries: list[dict]) -> None:
    """Atomically rewrite the whole pool (temp file + os.replace).

    O(n) per edit — cheap and correct at single-user scale (DEC-011). Atomic
    replace avoids a torn file if the write is interrupted (a small mitigation
    for the iCloud/multi-surface edit window flagged in DEC-006).
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

    _append_line(_resolve_pool(pool_path), record)
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

    NOTE: format parity target is `read_dropper_day.py` ({text, time} per day),
    which is not present in this repo. 'HH:MM' is the assumed shape; confirm
    against that script at /spec verify and adjust here (single source of truth).
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
    """
    target = day if isinstance(day, date_cls) else date_cls.fromisoformat(day)

    rows = [
        {"text": e["text"], "time": _local_time_hm(e["created_at"])}
        for e in _read_all(_resolve_pool(pool_path))
        if _local_day(e["created_at"]) == target
    ]
    rows.sort(key=lambda r: r["time"])
    return rows


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


def sync_sources() -> SyncResult:
    """Bring pull-based sources current. No-op in Phase 1 (no ingesters yet).

    The boundary exists so consumers can already write the
    `sync_sources(); read_day()` composition (DEC-019) — it simply has nothing
    to pull until the Excel bridge registers under it in Phase 2.
    """
    # --- Phase 2 extension point -------------------------------------------
    # The single v1 ingester (the Excel bridge, AC4/AC5.2) runs here. No
    # registry — one explicit call. Until then there is nothing to sync.
    # -----------------------------------------------------------------------
    return SyncResult(sources_synced=0, entries_ingested=0)
