# Collevity Data Lake — `jsonl-schema` part

The canonical **logical entry schema** + the thin **storage seam** (`collevity.lake`)
over an append-dominant JSONL pool — the **Collevity Data Lake**. This is the
keystone every pipeline part reads from and writes to; it keeps feeding
`/checkin`. The core is **Excel-blind** — the schema is designed as if Excel does
not exist. (The future second database, the Collevity Data Strata, will be
`collevity.strata`.)

- **Spec (source of truth):** `spec/spec.md`, `spec/decisions.log` (DEC-001..021).
- **Field contract:** `SCHEMA.md`.

> **Status: Phase 2 implemented** — Excel bridge + legacy migration, on the
> Phase-1 core. The bridge (`collevity/lake/bridges/`) is throwaway transition
> scaffolding; the core stays Excel-blind.

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

## Phase 2 — the Excel bridge (transition scaffolding)

All Excel knowledge lives in `collevity/lake/bridges/` (deletable → AC4.5). The
core never imports `openpyxl`; the bridge imports it lazily, and it's an
**optional** install extra (`pip install -e '.[excel]'`).

```sh
# ongoing sync of the live Dropper into the lake (also ran the initial migration)
export COLLEVITY_LAKE="$HOME/Library/Mobile Documents/com~apple~CloudDocs/00_COLLEVITY/03_TACTIC/_DATA/collevity_lake.jsonl"
python -m collevity.lake.bridges.excel          # idempotent — safe to re-run
```

- **Bridge** (`bridges/excel.py`): reads only col D (`text`) + col E
  (drop-timestamp), ignores col F (`modified`); writes through the seam; keys
  rows in a sidecar (`excel-ingest-state.json`, beside the lake) for idempotent
  re-runs + edit propagation. Runs under `sync_sources` — the sole v1 ingester.
- **tz backfill** (was `bridges/backfill_mdt_tz.py`): one-shot, disposable. The
  bridge stamps every row EDT; the backfill stamped the mid-June Colorado-trip
  rows `-06:00`. Already run against the live lake and **deleted** (git history at
  782aaec).
- **Retire Excel:** delete `collevity/lake/bridges/`. `sync_sources` reverts to a
  zero-work no-op (lazy import → `ImportError` → nothing to sync); core untouched.

The Dropper path defaults to the live iCloud file; override with
`COLLEVITY_DROPPER_XLSM`.
