# Spec-stub — JSONL Schema (keystone) · op-path slot 1

*DP-1 §3 launch packet. `/spec`-ready, NOT specced. Field-level schema is what this `/spec` produces; §2 settled only the scope-shape.*

## Problem statement
The store is 3 flat columns (`Thing`/`Timestamp`/`modified`). Every other part reads or writes this store, so its schema is the keystone. It must expand to carry kind/type, altitude, now-horizon, tz-aware time, provenance, identity+versioning, persistence tier, and thread links — **additively**, without breaking frictionless capture or the per-day checkin read.

## Inputs
- §2 schema scope-shape (the four settled calls + illustrative record shape).
- Live substrate: `Dropper_excel.xlsm` (852 rows, cols D/E/F) — the migration source.
- `read_dropper_day.py` + `_TEMPLATE.md` — the compatibility contract.
- DayOne as a **design-research reference** (M1 — external app; study its data structure before locking fields).

## Outputs
- A field-level JSONL record spec (names, types, required-vs-derived, enums for `kind`/`horizon`/`tier`).
- A **migration plan**: assign ids to the 852 rows, map D→`text`, E→`created_at`+`occurred_at`, F→`modified_at`; backfill `tz` (flag the known MDT/EDT spans from §0).
- A **checkin-compat shim**: re-emit a per-day {text, created-ts} slice from JSONL (or parallel-write Excel during transition).

## "Done"
JSONL pool exists, the 852 rows are migrated and round-trip-readable, `read_dropper_day.py` (or its shim) returns identical day-slices, and a new record can be appended by a writer with only the capture-cheap fields.

## What its `/spec` must settle
- Exact field set + required-vs-derived split (the capture/ingest division line).
- **"Entry + facets" vs `kind: thing|event` (Levi pushback, 2026-06-23):** model every record as an **entry** with orthogonal facets; **demote thing/event from master discriminator to one axis (or a property)**. Decide: keep a coarse `kind` for projection, or go straight to a **growable `type`** with thing-ness as a property? (Orchestrator lean: growable `type`.) This is the load-bearing taxonomy call.
- **`tags` taxonomy v1 — MULTI-VALUED, not a single `type` (Levi 2026-06-23):** one entry can carry several ("multiple types of info"). Seed tags from observed drop types (S7: task, recurring-task, job-contact, money, planning-question) + THING sub-classes (S5: triggers/milestones/segments/states/protocols). **Growable — usage reveals promotion, don't over-enumerate.**
- **First-landmark scope (Levi):** v1 = **raw USER entries.** `author` defaults to user; don't build the multi-author/agent-authored path now — scaffold it, defer it. Keep capture cheap.
- **Three orthogonal origin fields — keep distinct (Levi):** `source`/channel (dropper/mobile/claude-hook/wrapper/notebook), `author`/provenance-chain (user/agent/mixed), `context_ref` (originating session/location/thread). Don't collapse source into authorship.
- Revision/versioning mechanics (append + lineage_id).
- The checkin-compat mechanism (shim vs parallel-write).
- Query story: per-day scan now; flag where embeddings/sqlite enter later (amb #1).

## Tagged §0 items
S1 now-horizon · S2 timezone · S3 versioning · S4 provenance · S5 THING/things-vs-events · S6 persistence tiers · S7 drop-types. (Also serves P5 multi-modal: schema is writer-agnostic.)

## Dependencies
None upstream (op-path slot 1). Everything else depends on this.

## Derived direction (from orchestrator)
- Storage = JSONL, append-only, one pool, `kind` discriminator; per-context = views (§2 calls 1–2). **[CONFIRM the one-pool taxonomy with Levi before this `/spec` locks fields.]**
- Times stored UTC + offset; three distinct time fields. Don't repeat the single-timestamp bug.
- **Friction guarantee:** capture writes only top-line fields; ingest fills structure. Hold that line in the field design.
- Local/single-user/file-based posture — don't design for a server.
