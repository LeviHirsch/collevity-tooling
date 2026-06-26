"""Pull-source ingesters registered under `sync_sources` (Phase 2).

This subpackage is the home for the **temporary, Excel-specific** transition
machinery. The core (`collevity.lake.{schema,lake}`) stays Excel-blind (DEC-011);
ALL Excel knowledge lives here.

v1 holds exactly one ingester — the Excel bridge (`excel.py`, AC4/AC5.2) — plus a
disposable one-shot tz-backfill script (`backfill_mdt_tz.py`, AC4.4). Deleting
this whole subpackage cleanly retires the bridge: `sync_sources` degrades to its
Phase-1 no-op (the wiring imports the bridge lazily and tolerates its absence),
the core JSONL + schema are untouched, and `read_day` is unaffected (AC4.5).
"""
