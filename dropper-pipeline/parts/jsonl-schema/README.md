# Collevity Data Lake — `jsonl-schema` part

The canonical **logical entry schema** + the thin **storage seam** (`collevity.lake`)
over an append-dominant JSONL pool — the **Collevity Data Lake**. This is the
keystone every pipeline part reads from and writes to; it keeps feeding
`/checkin`. The core is **Excel-blind** — the schema is designed as if Excel does
not exist. (The future second database, the Collevity Data Strata, will be
`collevity.strata`.)

- **Spec (source of truth):** `spec/spec.md`, `spec/decisions.log` (DEC-001..021).
- **Field contract:** `SCHEMA.md`.

> **Status: Phase 1 implemented** — schema + storage seam (the core).
> Phase 2 (Excel bridge + legacy migration) is not built yet.

## The seam (the only access path — AC2.3, DEC-005)

Go through these. Do **not** read or write the JSONL pool directly — the
seam-only rule keeps the logical schema swappable up the JSONL → SQLite →
Postgres ladder.

```python
from collevity.lake import append_entry, edit_entry, read_day, sync_sources

# append-on-drop: caller supplies the floor minus id; the seam mints the id
eid = append_entry({
    "text": "picked up the prescription",
    "created_at": "2026-06-24T15:42:00-04:00",   # ISO-8601 + explicit offset
    "source": "dropper-excel",
    "author": "user",
})

# edit-in-place correction (no revision history)
edit_entry(eid, {"text": "picked up the *new* prescription"})

# pure read for /checkin: {text, time} per entry, bucketed by local day
rows = read_day("2026-06-24")          # -> [{"text": ..., "time": "15:42"}, ...]

# freshness is a consumer contract: compose sync then read
sync_sources(); rows = read_day("2026-06-24")   # no-op sync in Phase 1
```

## Lake location

The lake is **one text file** — one entry per line. Resolution order: explicit
`pool_path=` arg → `COLLEVITY_LAKE` env var → package default
(`data/collevity_lake.jsonl` next to this part). The default is dev-only; a real
deployment points `COLLEVITY_LAKE` at a stable path **outside the code tree**
(the data outlives the code). Because all access goes through the seam, moving
the lake later is `mv` + one env change — no dependent code to adjust.

## Develop / test

```sh
python3 -m venv .venv
./.venv/bin/pip install -e '.[dev]'
./.venv/bin/pytest          # AC-traced Phase-1 tests
```

UUIDv7 ids come from the `uuid6` library (not in the stdlib; DEC-021).

## What Phase 1 does NOT include

The Excel bridge, sidecar, legacy tz backfill, and the registered `sync_sources`
ingester are **Phase 2** (`spec/spec.md` → Implementation phases). `sync_sources`
here is the boundary only — no ingesters registered.
