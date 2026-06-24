# Spec-stub — Thread Ledger · op-path slot 5

*DP-1 §3 launch packet. Scope-level. Carries the unresolved amb #5 (ledger location + daily-log relationship).*

## Problem statement
Once drops are typed and routed, threads need a **persistent, navigable home** — a ledger of live lines of meaning (projects, recurring concerns, open loops) that orchestration reads to know "what's live, at what altitude." Without it, threads are recomputed each session and "clean orchestration" never lands.

## Inputs
- Extraction/routing output (slot 4) — typed, linked drops.
- The schema's `links` / `thread_id` mechanics.
- The existing **daily-tracking log** (`03_TACTIC/daily-tracking/`) — which also holds "what happened" (the duplication risk in amb #5).

## Outputs
- A ledger of threads, each with type, altitude, state (open/pending/closed), member drops, and last-touch — navigable and queryable by orchestration.

## "Done" (scope-level)
A session can query "live threads at altitude X" and get a clean answer without re-deriving from raw rows. A thread accrues new drops automatically. No duplication war with the daily-tracking log.

## What its `/scope`→`/spec` must settle
- **[CONFIRM amb #5] Ledger = part of the store, or a derived view?** *Orchestrator recommendation:* a **derived view/projection** over the one pool — NOT a second source of truth. The pool stays canonical; the ledger is a materialized index of `kind:thing` records + their linked events.
- **Relation to the daily-tracking log:** both are *projections of the same pool*, sliced differently — the daily-log is the **day-slice** (time projection), the ledger is the **thread-slice** (entity projection). Framing them as two views of one pool is how the duplication is avoided. Confirm this framing with Levi.
- Thread lifecycle: open → pending → closed; how threads are born (from extraction) and retired.
- Where it physically lives + its read API for orchestration.

## Tagged §0 items
amb #5 (ledger vs daily-log) · S5 things-as-threads · P4 async (pending state, not blocking) · S3/versioning (threads have history).

## Dependencies
Extraction (slot 4). Reads the schema pool (slot 1). Last of the ingest half.

## Derived direction (from orchestrator)
- **Default to derived-view**, single-source-of-truth = the pool. Resist making the ledger a parallel store (that recreates the duplication problem).
- The daily-log and the ledger are **siblings, not rivals** — same pool, different projection axis (time vs thread). Land that framing first; it dissolves amb #5.
- This is the part that most directly delivers "clean orchestration" — keep its read-API oriented to what an orchestration session actually asks.
