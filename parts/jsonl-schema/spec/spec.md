# Collevity Entry Store — JSONL Schema — Specification

> **Template for greenfield projects.** For iterations on an existing spec, the skill uses `spec-iteration.md` instead.
> Status: draft
> Revision: 4
> Last updated: 2026-06-24

## Goal

Define the canonical field-level shape of a Collevity entry and the thin storage seam that enforces it — a thin, **append-dominant**, horizontal time-stream of (v1: user) entries that serves as the keystone every pipeline part reads from and writes to, and keeps feeding `/checkin`. (Append-dominant = append-on-drop, edit-in-place-on-correction; DEC-006.) Retiring the flat 3-column Excel Dropper is the transition *motivation*, not the store's identity: the core store is permanent and Excel-blind; the bridge is scaffolding that gets deleted.

## Constraints

- **Capture-friction guarantee:** the required capture-time floor (defined in AC1.1) must be cheap top-line fields only; AI/ingest fills all structure (DEC-001, DEC-014).
- **`/checkin` parity:** must keep feeding the daily check-in via a `read_day(date)` seam whose output *format* matches `read_dropper_day.py` ({text, time} per day) (DEC-013).
- **Physical store = JSONL for v1, logically portable:** one append-dominant JSONL pool; logical entry shape kept storage-agnostic up the ladder JSONL → SQLite → Postgres/Supabase, accessed only through a thin storage seam (`append_entry` / `edit_entry` / `read_day` / `sync_sources`), never scattered raw file reads or writes (DEC-005).
- **Push where possible, pull where necessary:** native surfaces write directly via `append_entry` (push; no sync). Surfaces holding data externally or offline (Excel now; a future offline mobile cache, DEC-010) are **pull-based** and are brought current through a dedicated **`sync_sources`** coordination op before reads — never inside `read_day`, which stays a pure retrieval. `sync_sources` is a **permanent** seam (pull is a permanent need); its registered ingesters come and go — the Excel bridge is v1's only one, and temporary (DEC-018).
- **Core is Excel-blind:** the schema is designed as if Excel does not exist; all Excel-specific behavior lives in a bridge script plus a sidecar state file, retired by deleting them (DEC-011).
- **Thin-stream principle:** the horizontal stream stays deliberately thin; typing, structure, entities, and revision history accrete in the downstream vertical/strata layer, not on the raw entry (DEC-009).
- **Single-user / local / private.**
- **Time correctness at root:** `created_at` carries an explicit offset so the tz mis-bucketing bug is fixed at the source (DEC-014).
- **Offset correctness is owned at capture, not here:** each capture surface stamps `created_at` with the correct local offset; this part assumes it and neither re-derives nor validates it (AC3.2's bucketing is only as correct as the offset it is handed). **Excel** is the channel that can't self-stamp (naive datetimes), so the bridge owns its offset — the legacy 852 via the one-time backfill (AC4.4), ongoing pre-deprecation drops stamped EDT — until Excel is retired (DEC-017).

## Success criteria

- (a) A drop from each live channel (Excel bridge, and the reserved claude-hook shape) lands as a valid record carrying the required floor (`id`, `text`, `created_at`, `source`, `author`).
- (b) `/checkin` reading JSONL via `read_day` matches Excel-era output for the same day.
- (c) The 852 Excel rows ingest idempotently: re-running the bridge produces no duplicates, and a text edit on an Excel row propagates as an update (not a new entry).
- (d) Local-day bucketing: evening / late-night drops appear on the day they were made (local-day-of-offset), not the next UTC day.

## Out of scope

- The entity / "things" vertical store (derived mart/strata) and any knowledge-graph modeling.
- Revision / lineage history; edits are in-place corrections only (DEC-006).
- `tier` / persistence-retention lifecycle (DEC-009).
- The `kind` / `entity_axis` stream-item discriminator (DEC-003, DEC-004).
- The capture surfaces themselves (mobile shortcut, prompt-capture hook, computer dropper UI, full filing-UX wrapper are separate parts).
- Query engine / embeddings / SQLite engine work.
- `occurred_at` / `planned_for` / `horizon` as dedicated fields (strata-era promotions; `horizon` folds into `tags`) (DEC-014).
- Excel-row deletion detection (single-user, dropped) (DEC-011, DEC-013).
- Cutover timing of `read_dropper_day.py` and any read-side `source` filter (op-path / consumer concerns) (DEC-013).
- Whether to replace Excel at all (an upstream orchestration decision; this part assumes the replace-Excel intent, DEC-007).

## Acceptance criteria (MECE)

> This tree must be **mutually exclusive** (no AC overlaps another) and **collectively exhaustive** (every success criterion traces to at least one AC; every AC traces back to a goal or success criterion). Each leaf must be independently testable.

### AC1. Logical entry schema (the field contract)
- AC1.1. A schema document defines the **required floor** — `id`, `text`, `created_at`, `source`, `author` — and a valid entry is exactly one JSON object carrying all five. (→ goal, success (a))
- AC1.2. `id` is specified as a **UUIDv7** string, minted by the store seam on append (not by the capture surface). *(Implementation note: UUIDv7 is not in the Python stdlib `uuid` module; an external lib such as `uuid6` / `uuid-utils` is a build dependency.)* (→ DEC-010)
- AC1.3. `created_at` is specified as an **ISO-8601 string with explicit offset** (e.g. `2026-06-24T15:42:00-04:00`); no separate `tz` field; IANA zone name deferred. (→ DEC-014, success (d))
- AC1.4. `source` is a simple always-present channel tag; `author` is present and equals `user` in v1. (→ DEC-002, baseline)
- AC1.5. The schema defines the **optional** fields `context`, `tags`, `meta_notes`, `source_data`, each absent-when-unused, and a record missing all of them still validates. (→ DEC-002, DEC-008, DEC-012)
- AC1.6. `context` is specified as an **optional source-shaped object**, with the reserved `claude-session` shape `{kind, session_id, seq, parent_id?}` documented for the `claude-hook` source — **reserved in v1, not validated** (no hook channel exists yet). The schema notes that when the hook channel goes live (part 3), `context` becomes **conditionally required** for `source: claude-hook` entries. (→ DEC-002)
- AC1.7. `tags` is specified as an **optional, free-form, non-authoritative array** of ad-hoc labels (absorbs plan/projected); `meta_notes` as an **optional prose string** carrying a **documented convention** (append-only `ISO-timestamp — free prose`, newest-at-bottom, no-typed-prefix) — a convention, not a validated constraint; `source_data` as an **optional structured-stash object** (schema-on-read, not required to populate in v1). (→ DEC-008, DEC-012)
- AC1.8. The schema document **explicitly excludes** `entity_axis`, `kind`, `lineage_id`/revision, `tier`, `modified`/`updated_at`, `occurred_at`, `planned_for`, and `horizon`-as-field, noting the strata-era promotions. (→ out-of-scope, DEC-003/004/006/009/014)

### AC2. Storage seam (write + edit)
- AC2.1. `append_entry` accepts a floor-bearing entry, mints the UUIDv7 `id`, and appends one line to the JSONL pool. (→ DEC-005, DEC-010, success (a))
- AC2.2. An existing entry can be **edited in place via the seam** (`edit_entry` rewrites the line for a given `id`; no `lineage_id`, no revision history, no `modified` bump). (→ DEC-006)
- AC2.3. The seam (`append_entry` / `edit_entry` / `read_day` / `sync_sources`) is the only documented access path — no scattered raw file reads or writes — keeping the logical schema swappable up the JSONL → SQLite → Postgres ladder (where the physical edit primitive differs: line-rewrite for JSONL, `UPDATE` for Postgres, behind the same logical `edit_entry`). (→ DEC-005, DEC-018)

### AC3. Check-in read seam
- AC3.1. `read_day(date)` reads the unified JSONL and returns `{text, time}` per entry for that day. It is a **pure retrieval** — it performs no ingestion and has no write side-effects; a consumer needing up-to-date data calls `sync_sources()` first (AC5). Parity with `read_dropper_day.py` is **output-format parity** (the `{text, time}`-per-day shape its consumers expect), **not** behavioral replication of its tz mis-bucketing — which AC3.2 corrects at source. `read_day` is v1's **scoped read surface** (a v1 scope limit, not a claim that the seam is read-day-only) — exactly what `/checkin` needs; further read shapes (e.g. `read_week`, `read_by_tag`) are added later as additional seam methods, not by redesigning the seam or store. (→ success (b), DEC-013, DEC-014, DEC-018)
- AC3.2. `read_day` buckets entries by **local-day-of-offset `created_at`** (evening/late-night drops land on their local day, not the next UTC day). (→ success (d), DEC-013)

### AC4. Excel bridge (transition ingest)
- AC4.1. A bridge ingests Excel rows into the JSONL pool reading **only `{text, drop-timestamp (col E)}`** and **explicitly ignoring the `modified` column** (recorded ignore-rule protocol). (→ DEC-011, constraint Excel-blind)
- AC4.2. A sidecar state file (`excel-ingest-state.json`) maps each Excel row (by drop-timestamp, sub-second tiebreaker by row index) → the JSONL `id` created + a snapshot of the last-ingested text; the bridge then reads/writes the pool **through the storage seam, keyed by that `id`** (not raw line-matching). A row lacking a usable timestamp key **fails loudly** rather than mis-mapping silently. (→ DEC-011, DEC-005, success (c))
- AC4.3. Snapshot reconciliation per run: a new row → `append_entry`; text changed vs snapshot → `edit_entry` on the mapped `id`; unchanged → skip — yielding idempotent re-runs and edit propagation. (→ success (c), DEC-011)
- AC4.4. After a **one-time tz backfill**, every legacy row carries the correct offset: ongoing rows stamped EDT (`-04:00`); the MDT minority carries `-06:00`. The backfill is one-shot — no ongoing tz logic, no `source_data` timestamp stash. The Phase-2 deliverable is the EDT stamping + backfill machinery; *identifying* which legacy rows were MDT is the open **input** (Open Question 1), not part of this deliverable. (→ DEC-013, success (c))
- AC4.5. Bridge and sidecar are fully self-contained: deleting them leaves the core JSONL and schema untouched, and unregisters the bridge from `sync_sources` (AC5) with no effect on `read_day` (Excel-blind verification). (→ DEC-011, DEC-018, constraint Excel-blind)
- AC4.6. The Excel bridge's ingestion runs **under `sync_sources`** (AC5), **idempotent within a session** (duplicate count never grows), with **no daemon and no cron**. It is `sync_sources`'s only v1 registered ingester and is removed when Excel is retired (AC4.5). (→ DEC-018, DEC-015, success (c))

### AC5. Source synchronization seam (`sync_sources`)
- AC5.1. `sync_sources()` is the seam op that brings the lake **current from pull-based external capture sources** before a read; native **push** surfaces (which write directly via `append_entry`) require no sync, and `read_day` performs no ingestion. A consumer needing fresh data composes `sync_sources()` then `read_day()` (op-path concern). (→ DEC-018, success (b))
- AC5.2. v1 implements **exactly one** ingester under `sync_sources` — the Excel bridge (AC4). The general multi-source registry / per-source freshness machinery is **deferred**; the `sync_sources` contract is shaped so a second pull source (e.g. a future offline mobile cache, DEC-010) plugs in **additively**, without redesigning the seam. (→ DEC-018, DEC-010)

## Implementation phases

> Ordered phases for building this. **Invariant:** phase N must be implementable to completion without any work from phase N+1 or later — dependencies flow only backward. Every leaf AC appears in exactly one phase.

### Phase 1. Schema + storage seam (the core)
**Delivers:** A documented, validating logical entry schema and a thin `append_entry` / `edit_entry` / `read_day` (pure read) / `sync_sources` (boundary, no ingesters yet) seam over an append-dominant JSONL pool — a core that can be written to and read from with zero knowledge of Excel.
**Unblocks:** Phase 2 (Excel bridge + legacy migration) — every channel and consumer reads/writes through this, and the Excel bridge registers under the `sync_sources` boundary defined here.
- AC1.1
- AC1.2
- AC1.3
- AC1.4
- AC1.5
- AC1.6
- AC1.7
- AC1.8
- AC2.1
- AC2.2
- AC2.3
- AC3.1
- AC3.2
- AC5.1

### Phase 2. Excel bridge + legacy migration
**Delivers:** Excel remains a live capture channel during transition — the 852 legacy rows plus ongoing Excel drops/edits ingest idempotently into the JSONL pool via an Excel-blind bridge and sidecar (writing through the seam), with the one-time tz backfill; the bridge is registered as the sole v1 ingester under `sync_sources` (no daemon/cron, idempotent), and is removed cleanly when Excel retires.
**Depends on:** Phase 1 (the schema + `append_entry`/`edit_entry` seam the bridge writes through, and the `sync_sources` boundary the bridge registers under).
- AC4.1
- AC4.2
- AC4.3
- AC4.4
- AC4.5
- AC4.6
- AC5.2

## Open questions

- **MDT-row identification mechanism** (feeds AC4.4): the mechanism for identifying *which* of the 852 legacy rows were entered during MDT (vs. EDT) is unresolved — a defined approach (date-range heuristic, manual list, or an AI pass over the raw timestamps) is needed before the one-time backfill runs. Kept deferred as a migration-runbook detail; does not block sealing the spec (DEC-013).
- **Excel-row deletion** is an explicitly unhandled gap (a deleted Excel row leaves a lingering JSONL entry); accepted for single-user, revisit only if it bites (DEC-011, DEC-013).
- **Offline-first surface-local id reconciliation** is deferred — v1 only commits "canonical id assigned on append"; the pre-sync identity pattern is revisited when a surface needs it. When it arrives it will be a **pull source registered under `sync_sources`** (AC5.2) — the seam already names its home; the reconciliation logic itself is the deferred part (DEC-010, DEC-018).
- **Read-side `source` filter** to keep hook drops from flooding the daily view is flagged as an op-path/consumer concern for hook go-live, not a schema change (DEC-013).
