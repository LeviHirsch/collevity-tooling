# Phase 2 kickoff prompt — paste into a fresh session in this part

> Open a new conversation with cwd = `…/dropper-pipeline/parts/jsonl-schema/`, paste
> everything in the box below, build Phase 2, then return to the orchestrating
> session and run `/spec implement` to audit. Phase-1 baseline is committed at
> `676cbc9`. The venv already has `uuid6` + `openpyxl` installed.

---

```
Implement phase 2 of spec/spec.md ("Excel bridge + legacy migration"). Do not implement other phases. Phase 1 (the collevity.lake schema + storage seam) is already implemented and committed (baseline 676cbc9); build on it, do not re-implement it.

## What this phase delivers
Excel remains a live capture channel during transition — the legacy rows plus ongoing Excel drops/edits ingest idempotently into the JSONL pool via an Excel-blind bridge and sidecar (writing through the seam), with the one-time tz backfill; the bridge is registered as the sole v1 ingester under `sync_sources` (no daemon/cron, idempotent), and is removed cleanly when Excel retires.
This is a dependent phase: it writes/reads only through the Phase-1 seam (`collevity.lake`: append_entry / edit_entry / read_day / sync_sources). The core stays Excel-blind — all Excel-specific code lives in the bridge + sidecar.

## ACs to satisfy (this phase only) — verbatim from spec.md
- AC4.1: A bridge ingests Excel rows into the JSONL pool reading ONLY {text, drop-timestamp (col E)} and explicitly ignoring the `modified` column (recorded ignore-rule protocol). (spec.md:68)
- AC4.2: A persistent sidecar mapping (e.g. excel-ingest-state.json) keys each Excel row (by drop-timestamp, sub-second tiebreaker by row index — col-E timestamp stability across saves assumed under the single-file regime, DEC-016) → the JSONL `id` created + a snapshot of the last-ingested text; the bridge reads/writes the pool THROUGH the storage seam, keyed by that `id` (not raw line-matching). A row lacking a usable timestamp key FAILS LOUDLY — the run aborts with an error naming the offending row, no partial ingest. (spec.md:69)
- AC4.3: Snapshot reconciliation per run: new row → append_entry; text changed vs snapshot → edit_entry on the mapped `id`; unchanged → skip — idempotent re-runs + edit propagation. (spec.md:70)
- AC4.4: After a ONE-TIME tz backfill, every legacy row carries the correct offset: ongoing rows stamped EDT (-04:00); the MDT rows carry -06:00. One-shot — no ongoing tz logic, no source_data timestamp stash. The deliverable is the EDT stamping + backfill machinery; *identifying* which rows were MDT is the resolved input (see Grounding / DEC-023). (spec.md:71)
- AC4.5: Bridge and sidecar are fully self-contained: deleting them leaves the core JSONL + schema untouched, unregisters the bridge from sync_sources, no effect on read_day (Excel-blind verification). (spec.md:72)
- AC4.6: The bridge's ingestion runs UNDER sync_sources, idempotent within a session (duplicate count never grows), NO daemon and NO cron. It is sync_sources's only v1 registered ingester, removed when Excel retires. (spec.md:73)
- AC5.2: v1 implements EXACTLY ONE ingester under sync_sources — the Excel bridge; NO multi-source registry in v1 (designed to admit a 2nd pull source additively later, but not a v1 deliverable). (spec.md:77)

## Constraints — do not regress these (spec.md:12-22, and Phase-1 core)
- Excel-blind core: the schema/seam are designed as if Excel does not exist; ALL Excel behavior lives in the bridge + sidecar (spec.md:18). Do not add Excel awareness to collevity/lake/{schema,lake}.py beyond the single ingester call wired at the marked Phase-2 extension point in lake.py's sync_sources.
- Seam-only writes: the bridge reads/writes the pool ONLY through append_entry/edit_entry (no raw JSONL line-matching) (spec.md:16, AC2.3).
- Offset owned at capture; Excel is the bridge-owned exception: the bridge stamps the Excel channel's offset (legacy via the one-time backfill, ongoing EDT) — the core neither re-derives nor validates it (spec.md:22, DEC-017).
- read_day stays a pure read; sync_sources is the only place ingest happens (DEC-018). The boundary + extension point already exist in collevity/lake/lake.py.
- Do not regress Phase-1: collevity.lake's 24 tests must still pass.

## Out of scope
- Phase 1 is done — do not re-implement the schema or seam (only register the ingester under sync_sources).
- The entity/things vertical store; query engine; the capture surfaces themselves.
- Excel-row deletion detection (explicitly dropped, DEC-011/013).

## Reference
- Full Phase-2 block: spec.md:102-112. Full AC tree: spec.md:44-77. Decisions: spec/decisions.log (read DEC-011, DEC-013, DEC-015, DEC-016, DEC-017, DEC-018, DEC-022, DEC-023 — they govern this phase).

## Grounding (from live-file inspection 2026-06-25 — use this, don't re-derive)
- Live Excel: `/Users/levi/Library/Mobile Documents/com~apple~CloudDocs/00_COLLEVITY/Dropper_excel.xlsm`, sheet `Sheet1`, header in row 1.
- Columns: **D = `Thing` → entry text**; **E = `Timestamp` → drop-timestamp (naive datetime, no tz)**; **F = `modified` → IGNORE (AC4.1)**. Cols A/B/C are empty.
- **935 data rows**, range **2026-05-21 → 2026-06-25**. (The spec says "852" — a stale point-in-time count; the older dropper_05.20 snapshot is only 18 rows, so this file is the full history.) All col-E values are datetime + non-null, so AC4.2's fail-loud guard won't trigger on today's data — implement it anyway.
- **Lake path (DEC-022):** set before running —
  `export COLLEVITY_LAKE="$HOME/Library/Mobile Documents/com~apple~CloudDocs/00_COLLEVITY/03_TACTIC/_DATA/collevity_lake.jsonl"`
- **xlsx reader:** use `openpyxl` (already in the venv). Add it as an OPTIONAL extra in pyproject (`[project.optional-dependencies] excel = ["openpyxl>=3.1"]`) — the bridge is throwaway, keep the core dep-light (supports AC4.5).
- **Open Question 1 resolved mechanism (DEC-023):** identify MDT vs EDT by reading BOTH the entry text AND the timestamp — Levi wrote location/move notes into some entries' text that mostly indicate the period. Do a one-time classification pass over the mid-June move-window rows (text + timestamp) to label each row's offset BEFORE the backfill stamps it. Levi moved Mountain→Eastern mid-June 2026 (confirm date + direction with him at the start). Do NOT assume a clean single date-cutoff.
- **Source tag:** Excel entries use `source: "dropper-excel"` (DEC-007); `author: "user"`.
- **Two spec-drift items to raise via `/spec reconcile` during this session:** (a) "852" → 935; (b) the "MDT minority" wording may be wrong (the MDT share could be ~half, depending on the move date).

## Design decisions — surface, don't decide
The ACs pin WHAT must be true, not HOW. Where the spec is silent — bridge module location (must be cleanly deletable per AC4.5; e.g. a separate `collevity/lake/bridges/excel.py` + the sidecar file vs. some other layout), where the sidecar `excel-ingest-state.json` lives, exactly how the single ingester registers under sync_sources without building a registry (AC5.2 — one explicit call at the marked extension point), the backfill's invocation shape (one-shot script vs. flag), CLI surface — STOP and ask Levi before writing code down that path. A small clarifying question now beats rework at audit.

When done: tell Levi the implementation is ready for audit; he'll re-run `/spec implement` from the orchestrating session. Commit your work or leave it uncommitted — the audit scopes from commits since the last state.yaml change plus uncommitted changes.
```
