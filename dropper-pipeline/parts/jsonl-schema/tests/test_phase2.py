"""Phase 2 acceptance tests — Excel bridge + legacy migration (AC4, AC5.2).

Each test names the AC it exercises. Fixtures build throwaway .xlsx workbooks
(openpyxl reads by content, not extension) so nothing touches the live Dropper.
Run: `pytest` from the part root with `.[dev]` installed (pulls openpyxl).
"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime

import openpyxl
import pytest

from collevity.lake import append_entry, read_day, sync_sources
from collevity.lake.bridges import excel
from collevity.lake.bridges.backfill_mdt_tz import backfill


# --- fixtures ---------------------------------------------------------------

def make_dropper(path, rows):
    """Write a Dropper-shaped workbook: empty A/B/C, D=Thing, E=Timestamp, F=modified.

    `rows` = list of (text, timestamp, modified). `modified` is junk the bridge
    must never read (AC4.1).
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append([None, None, None, "Thing", "Timestamp", "modified"])
    for text, ts, modified in rows:
        ws.append([None, None, None, text, ts, modified])
    wb.save(path)
    return path


@pytest.fixture
def paths(tmp_path):
    return {
        "xlsm": tmp_path / "Dropper.xlsx",
        "pool": tmp_path / "lake.jsonl",
        "sidecar": tmp_path / "excel-ingest-state.json",
    }


def run_ingest(paths):
    return excel.ingest(
        xlsm_path=paths["xlsm"], sidecar_path=paths["sidecar"], pool_path=paths["pool"]
    )


def pool_records(paths):
    if not paths["pool"].exists():
        return []
    text = paths["pool"].read_text().strip()
    return [json.loads(l) for l in text.splitlines()] if text else []


# --- AC4.1: reads only {text, drop-timestamp}, ignores `modified` -----------

def test_bridge_reads_text_and_timestamp_ignores_modified(paths):  # AC4.1
    make_dropper(paths["xlsm"], [
        ("picked up prescription", datetime(2026, 6, 24, 15, 42, 0), "JUNK-MODIFIED"),
    ])
    run_ingest(paths)
    (rec,) = pool_records(paths)
    assert rec["text"] == "picked up prescription"
    assert rec["created_at"] == "2026-06-24T15:42:00-04:00"   # col E + EDT
    assert rec["source"] == "dropper-excel" and rec["author"] == "user"
    assert "modified" not in rec                               # col F never read


def test_modified_column_change_does_not_reingest(paths):  # AC4.1 (ignore-rule)
    make_dropper(paths["xlsm"], [("a", datetime(2026, 6, 24, 9, 0, 0), "v1")])
    run_ingest(paths)
    # Only col F changes — bridge must not see it ⇒ no edit, no new line.
    make_dropper(paths["xlsm"], [("a", datetime(2026, 6, 24, 9, 0, 0), "v2-CHANGED")])
    assert run_ingest(paths) == 0
    assert len(pool_records(paths)) == 1


# --- AC4.2: sidecar identity + seam-keyed writes + fail-loud ----------------

def test_sidecar_maps_rows_to_minted_ids_and_snapshots(paths):  # AC4.2
    make_dropper(paths["xlsm"], [("hello", datetime(2026, 6, 24, 10, 0, 0), None)])
    run_ingest(paths)
    state = json.loads(paths["sidecar"].read_text())
    (key, val), = state.items()
    assert key == "2026-06-24T10:00:00"          # keyed by drop-timestamp
    assert val["text"] == "hello"                # text snapshot stored
    assert uuid.UUID(val["id"]).version == 7      # → the seam-minted JSONL id
    assert pool_records(paths)[0]["id"] == val["id"]


def test_missing_timestamp_fails_loudly_no_partial_ingest(paths):  # AC4.2
    make_dropper(paths["xlsm"], [
        ("good row", datetime(2026, 6, 24, 8, 0, 0), None),
        ("bad row", "not-a-datetime", None),
    ])
    with pytest.raises(ValueError, match="row 3 has no usable drop-timestamp"):
        run_ingest(paths)
    assert pool_records(paths) == []              # aborted before ANY write
    assert not paths["sidecar"].exists()


def test_subsecond_collision_uses_row_index_tiebreaker(paths):  # AC4.2, DEC-016
    ts = datetime(2026, 6, 24, 12, 0, 0)
    make_dropper(paths["xlsm"], [("first", ts, None), ("second", ts, None)])
    assert run_ingest(paths) == 2
    keys = set(json.loads(paths["sidecar"].read_text()))
    assert keys == {"2026-06-24T12:00:00#2", "2026-06-24T12:00:00#3"}


# --- AC4.3: snapshot reconciliation (append / edit / skip) ------------------

def test_new_row_appends(paths):  # AC4.3
    make_dropper(paths["xlsm"], [("one", datetime(2026, 6, 24, 9, 0, 0), None)])
    assert run_ingest(paths) == 1
    assert len(pool_records(paths)) == 1


def test_changed_text_edits_in_place_same_id(paths):  # AC4.3, success (c)
    make_dropper(paths["xlsm"], [("typo", datetime(2026, 6, 24, 9, 0, 0), None)])
    run_ingest(paths)
    first_id = pool_records(paths)[0]["id"]
    make_dropper(paths["xlsm"], [("fixed", datetime(2026, 6, 24, 9, 0, 0), None)])
    assert run_ingest(paths) == 1
    recs = pool_records(paths)
    assert len(recs) == 1                          # edited, not appended
    assert recs[0]["text"] == "fixed" and recs[0]["id"] == first_id


def test_unchanged_rerun_is_idempotent(paths):  # AC4.3, AC4.6, success (c)
    make_dropper(paths["xlsm"], [
        ("a", datetime(2026, 6, 24, 9, 0, 0), None),
        ("b", datetime(2026, 6, 24, 10, 0, 0), None),
    ])
    assert run_ingest(paths) == 2
    assert run_ingest(paths) == 0                  # nothing new → no work
    assert run_ingest(paths) == 0
    assert len(pool_records(paths)) == 2           # duplicate count never grows


# --- AC4.4: one-time MDT tz backfill ----------------------------------------

def test_backfill_stamps_only_colorado_rows_mdt(paths):  # AC4.4
    rows = [
        ("home airport (outbound)", datetime(2026, 6, 13, 9, 30, 0), None),   # EDT
        ("colorado wedding morning", datetime(2026, 6, 15, 8, 42, 40), None), # MDT
        ("colorado, jun17 afternoon", datetime(2026, 6, 17, 14, 49, 23), None), # MDT
        ("back home, now EDT", datetime(2026, 6, 17, 21, 1, 14), None),       # EDT
        ("ongoing drop", datetime(2026, 6, 24, 12, 0, 0), None),              # EDT
    ]
    make_dropper(paths["xlsm"], rows)
    run_ingest(paths)
    # Before backfill: bridge is tz-dumb — everything EDT.
    assert all(r["created_at"].endswith("-04:00") for r in pool_records(paths))

    changed = backfill(sidecar_path=paths["sidecar"], pool_path=paths["pool"])
    assert changed == 2                            # exactly the two CO rows

    by_text = {r["text"]: r["created_at"] for r in pool_records(paths)}
    assert by_text["colorado wedding morning"] == "2026-06-15T08:42:40-06:00"
    assert by_text["colorado, jun17 afternoon"] == "2026-06-17T14:49:23-06:00"
    assert by_text["home airport (outbound)"].endswith("-04:00")
    assert by_text["back home, now EDT"].endswith("-04:00")
    assert by_text["ongoing drop"].endswith("-04:00")


def test_backfill_is_idempotent(paths):  # AC4.4
    make_dropper(paths["xlsm"], [("co", datetime(2026, 6, 16, 10, 0, 0), None)])
    run_ingest(paths)
    assert backfill(sidecar_path=paths["sidecar"], pool_path=paths["pool"]) == 1
    again = backfill(sidecar_path=paths["sidecar"], pool_path=paths["pool"])
    assert again == 1                              # re-sets same value, harmless
    assert pool_records(paths)[0]["created_at"] == "2026-06-16T10:00:00-06:00"


def test_backfill_survives_a_later_text_edit(paths):  # AC4.4 + AC4.3 interaction
    make_dropper(paths["xlsm"], [("co typo", datetime(2026, 6, 16, 10, 0, 0), None)])
    run_ingest(paths)
    backfill(sidecar_path=paths["sidecar"], pool_path=paths["pool"])
    # Bridge edits only `text` on a change ⇒ the -06:00 offset is preserved.
    make_dropper(paths["xlsm"], [("co fixed", datetime(2026, 6, 16, 10, 0, 0), None)])
    run_ingest(paths)
    rec = pool_records(paths)[0]
    assert rec["text"] == "co fixed"
    assert rec["created_at"] == "2026-06-16T10:00:00-06:00"


# --- AC4.5: self-contained / clean-delete -----------------------------------

def test_deleting_bridge_reverts_sync_to_noop_core_intact(paths, monkeypatch):  # AC4.5
    # A native push entry already in the lake (no Excel involved).
    append_entry(
        {"text": "pushed", "created_at": "2026-06-24T08:00:00-04:00",
         "source": "claude-hook", "author": "user"},
        pool_path=paths["pool"],
    )
    # Simulate `bridges/` having been deleted: its import now fails.
    monkeypatch.setitem(sys.modules, "collevity.lake.bridges.excel", None)
    result = sync_sources()
    assert (result.sources_synced, result.entries_ingested) == (0, 0)
    # Core JSONL + read_day untouched by the bridge's absence.
    assert read_day("2026-06-24", pool_path=paths["pool"]) == [
        {"text": "pushed", "time": "08:00"}
    ]


# --- AC4.6 / AC5.2: runs under sync_sources, single ingester, no registry ---

def test_sync_sources_runs_the_one_bridge(paths, monkeypatch):  # AC4.6, AC5.2
    make_dropper(paths["xlsm"], [("drop", datetime(2026, 6, 24, 10, 0, 0), None)])
    monkeypatch.setenv("COLLEVITY_DROPPER_XLSM", str(paths["xlsm"]))
    monkeypatch.setenv("COLLEVITY_LAKE", str(paths["pool"]))
    # Sidecar defaults beside the lake.
    result = sync_sources()
    assert (result.sources_synced, result.entries_ingested) == (1, 1)
    # Composition the one v1 consumer uses (AC5.1): sync then pure read.
    assert read_day("2026-06-24", pool_path=paths["pool"]) == [
        {"text": "drop", "time": "10:00"}
    ]


def test_sync_idempotent_within_session(paths, monkeypatch):  # AC4.6
    make_dropper(paths["xlsm"], [("d", datetime(2026, 6, 24, 10, 0, 0), None)])
    monkeypatch.setenv("COLLEVITY_DROPPER_XLSM", str(paths["xlsm"]))
    monkeypatch.setenv("COLLEVITY_LAKE", str(paths["pool"]))
    assert sync_sources().entries_ingested == 1
    assert sync_sources().entries_ingested == 0    # duplicate count never grows
    assert sync_sources().sources_synced == 1      # still exactly one source


def test_no_dropper_present_is_zero_work(paths):  # AC5.2 (no source → noop)
    # conftest points COLLEVITY_DROPPER_XLSM at a nonexistent file.
    result = sync_sources()
    assert (result.sources_synced, result.entries_ingested) == (0, 0)
