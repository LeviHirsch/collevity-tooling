# Spec-stub — Mobile Shortcut (capture wedge) · op-path slot 2

*DP-1 §3 launch packet. Spec-ready, small, concrete.*

## Problem statement
Capture must be frictionless from the phone (where much life happens). Today that's typing into Excel — clumsy on mobile. A shortcut should drop text into the **new store** in seconds, from anywhere.

## Inputs
- The JSONL schema (slot 1) — specifically the capture-cheap field set + where the pool lives (iCloud path).
- iOS Shortcuts / Share-sheet as the delivery mechanism.

## Outputs
- An iOS Shortcut that takes text (typed or shared/dictated) and appends one capture-cheap record to the pool, stamped `created_at` + `tz` + `author: user`.

## "Done"
From the phone, a drop reaches the pool in ≤ a few seconds, offline-tolerant (queues if iCloud not synced), and appears in the next checkin day-slice.

## What its `/spec` must settle
- Append mechanism to an iCloud-resident JSONL (direct write vs a tiny relay) — concurrency with other writers.
- Capture affordances: text, dictation, share-sheet from other apps; optional quick `type`/`horizon` tap **without adding friction** (default untyped).
- Offline/queue behavior + dedupe on sync (ties to schema `id`).

## Tagged §0 items
P5 multi-modal capture (this is the phone surface). Indirectly E3/E5 (date-anchored use cases) — but typing/extraction is the ingest layer's job, not the shortcut's.

## Dependencies
Schema (slot 1). Op-path slot 2 — first writer to exercise the new store.

## Derived direction (from orchestrator)
- **Stay a wedge.** Cheapest possible capture; do NOT pull typing/leveling into the shortcut (friction guarantee). A drop may arrive fully untyped; ingest handles the rest.
- **[CONFIRM amb #4]** default = yes, writes the *same* pool the wrapper will read, day one (single store, multiple writers). Confirm before spec.
- Stamp `tz` at capture so the MDT/EDT class of bug can't recur.
