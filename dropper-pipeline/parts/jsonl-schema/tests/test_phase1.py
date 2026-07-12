"""Phase 1 acceptance tests — schema + storage seam (the core).

Each test names the AC it exercises. Run: `pytest` from the part root with the
dev extra installed (`pip install -e '.[dev]'`).
"""

from __future__ import annotations

import json
import uuid
from datetime import date

import pytest

from collevity.lake import (
    SchemaError,
    append_entry,
    edit_entry,
    read_day,
    sync_sources,
    validate,
)


def floor(**overrides) -> dict:
    """A floor-bearing entry WITHOUT id (append mints it)."""
    base = {
        "text": "picked up the prescription",
        "created_at": "2026-06-24T15:42:00-04:00",
        "source": "dropper-excel",
        "author": "user",
    }
    base.update(overrides)
    return base


@pytest.fixture
def pool(tmp_path):
    return tmp_path / "entries.jsonl"


# --- AC1: logical entry schema --------------------------------------------

def test_floor_only_entry_validates(pool):  # AC1.1, AC1.5
    """The five floor fields alone make a valid entry; no optionals needed."""
    eid = append_entry(floor(), pool_path=pool)
    record = json.loads(pool.read_text().strip())
    assert set(record) == {"id", "text", "created_at", "source", "author"}
    assert record["id"] == eid


def test_missing_floor_field_rejected(pool):  # AC1.1
    incomplete = {"id": "x", "text": "x",
                  "created_at": "2026-06-24T15:42:00-04:00", "author": "user"}  # no source
    with pytest.raises(SchemaError, match="missing required floor"):
        validate(incomplete)


def test_id_is_uuidv7(pool):  # AC1.2, DEC-010
    eid = append_entry(floor(), pool_path=pool)
    parsed = uuid.UUID(eid)
    assert parsed.version == 7


def test_id_is_store_minted_not_surface(pool):  # AC1.2
    """Supplying an id is an error — the seam mints it."""
    with pytest.raises(ValueError, match="do not supply 'id'"):
        append_entry(floor(id="surface-minted"), pool_path=pool)


def test_created_at_requires_explicit_offset(pool):  # AC1.3, DEC-014
    with pytest.raises(SchemaError, match="explicit offset"):
        validate(floor(id="x", created_at="2026-06-24T15:42:00"))  # naive → rejected


def test_created_at_must_be_iso(pool):  # AC1.3
    with pytest.raises(SchemaError, match="not valid ISO-8601"):
        validate(floor(id="x", created_at="last tuesday"))


def test_author_must_be_user_in_v1(pool):  # AC1.4
    with pytest.raises(SchemaError, match="author must be 'user'"):
        validate(floor(id="x", author="claude"))


def test_optional_fields_validate_when_present(pool):  # AC1.5, AC1.7
    entry = floor(
        tags=["idea", "collevity"],
        meta_notes="2026-06-25T09:00:00-04:00 — revisit later",
        source_data={"raw": {"col": "value"}},
        context={"kind": "claude-session", "session_id": "s", "seq": 1},
    )
    eid = append_entry(entry, pool_path=pool)
    record = json.loads(pool.read_text().strip())
    assert record["tags"] == ["idea", "collevity"]
    assert record["id"] == eid


def test_optional_field_wrong_type_rejected(pool):  # AC1.5/1.7
    with pytest.raises(SchemaError, match="tags must be list"):
        validate(floor(id="x", tags="not-a-list"))


def test_context_shape_not_validated_in_v1(pool):  # AC1.6
    """`context` is reserved-not-validated: any object passes in v1."""
    validate(floor(id="x", context={"anything": "goes", "no": "shape check"}))


def test_excluded_field_rejected_with_pointer(pool):  # AC1.8
    for excluded in ("kind", "entity_axis", "lineage_id", "tier",
                     "modified", "occurred_at", "planned_for", "horizon"):
        with pytest.raises(SchemaError, match="explicitly excluded"):
            validate(floor(id="x", **{excluded: "whatever"}))


def test_unknown_field_rejected(pool):  # AC1.8 (closed top level)
    with pytest.raises(SchemaError, match="unknown top-level field"):
        validate(floor(id="x", surprise="value"))


# --- AC2: storage seam (write + edit) -------------------------------------

def test_append_writes_one_line(pool):  # AC2.1
    append_entry(floor(), pool_path=pool)
    append_entry(floor(text="second"), pool_path=pool)
    assert len(pool.read_text().strip().splitlines()) == 2


def test_edit_in_place_rewrites_line_no_history(pool):  # AC2.2, DEC-006
    eid = append_entry(floor(text="typo"), pool_path=pool)
    updated = edit_entry(eid, {"text": "fixed"}, pool_path=pool)
    assert updated["text"] == "fixed"
    lines = pool.read_text().strip().splitlines()
    assert len(lines) == 1  # rewritten in place, not appended
    record = json.loads(lines[0])
    assert record["id"] == eid
    assert "modified" not in record and "lineage_id" not in record


def test_edit_unknown_id_raises(pool):  # AC2.2
    append_entry(floor(), pool_path=pool)
    with pytest.raises(KeyError):
        edit_entry("no-such-id", {"text": "x"}, pool_path=pool)


def test_edit_cannot_change_id(pool):  # AC2.2
    eid = append_entry(floor(), pool_path=pool)
    with pytest.raises(ValueError, match="cannot change an entry's id"):
        edit_entry(eid, {"id": "different"}, pool_path=pool)


# --- AC3: check-in read seam ----------------------------------------------

def test_read_day_returns_text_time_shape(pool):  # AC3.1, D1
    append_entry(floor(text="morning", created_at="2026-06-24T09:05:00-04:00"), pool_path=pool)
    rows = read_day("2026-06-24", pool_path=pool)
    # {text, time} contract intact; created_at passthrough is additive (D1).
    assert rows == [
        {"text": "morning", "time": "09:05", "created_at": "2026-06-24T09:05:00-04:00"}
    ]


def test_read_day_sorted_by_time(pool):  # AC3.1
    append_entry(floor(text="late", created_at="2026-06-24T22:00:00-04:00"), pool_path=pool)
    append_entry(floor(text="early", created_at="2026-06-24T07:00:00-04:00"), pool_path=pool)
    rows = read_day("2026-06-24", pool_path=pool)
    assert [r["text"] for r in rows] == ["early", "late"]


def test_read_day_is_pure_no_side_effects(pool):  # AC3.1, DEC-018
    append_entry(floor(), pool_path=pool)
    before = pool.read_text()
    read_day("2026-06-24", pool_path=pool)
    read_day("2026-06-24", pool_path=pool)
    assert pool.read_text() == before  # read never writes


def test_read_day_accepts_date_object(pool):  # AC3.1
    append_entry(floor(created_at="2026-06-24T15:42:00-04:00"), pool_path=pool)
    assert len(read_day(date(2026, 6, 24), pool_path=pool)) == 1


def test_late_night_drop_buckets_local_not_utc(pool):  # AC3.2, success (d)
    """23:30 -04:00 == 03:30Z next day. It must land on the LOCAL day (24th)."""
    append_entry(floor(text="late night", created_at="2026-06-24T23:30:00-04:00"), pool_path=pool)
    assert len(read_day("2026-06-24", pool_path=pool)) == 1   # local day: present
    assert len(read_day("2026-06-25", pool_path=pool)) == 0   # next UTC day: absent


def test_read_day_empty_pool(pool):  # AC3.1
    assert read_day("2026-06-24", pool_path=pool) == []


# --- AC5: sync_sources boundary -------------------------------------------

def test_sync_sources_is_zero_work_noop_in_phase1(pool):  # AC5.1
    result = sync_sources()
    assert (result.sources_synced, result.entries_ingested) == (0, 0)


def test_sync_then_read_composition(pool):  # AC5.1, DEC-019
    """The consumer composition works even with no ingesters registered."""
    append_entry(floor(text="drop", created_at="2026-06-24T10:00:00-04:00"), pool_path=pool)
    sync_sources()
    rows = read_day("2026-06-24", pool_path=pool)
    assert [(r["text"], r["time"]) for r in rows] == [("drop", "10:00")]
