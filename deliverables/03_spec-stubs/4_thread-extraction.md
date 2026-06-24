# Spec-stub — Thread Extraction / Typing / Routing · op-path slot 4

*DP-1 §3 launch packet. **Scope-level, low spec-readiness** — the fuzzy heart of the upper half. Its `/spec` will likely need a `/scope` pass first. Don't fake spec-readiness.*

## Problem statement
Raw drops arrive untyped. The system must derive structure: **type** a drop (task? job-contact? log? plan?), assign **altitude** (the S3 leveling enabler), and **route** it (into a thread, a project, a downstream action). This is the work the checkin does by hand today — and the part that makes "clean threads" real. It's also the part DP-1's own §0 sweep **hand-ran as a dogfood** (see §4).

## Inputs
- A **corpus** in the new schema (hence op-path slot 4 — needs capture flowing first).
- Schema's `kind`/`type`/`horizon`/`links` fields (thread-aware).
- The observed type vocabulary (S7) + use-case patterns from §0 (E1–E5).

## Outputs
- A typing + routing pass that, given a drop, proposes `type`, `kind` (thing/event), altitude, and `links` (to threads/things), for light human steering.

## "Done" (scope-level — sharpen in its `/scope`)
A new drop gets auto-typed and linked to the right thread/thing with usable accuracy, surfaced for approve/adjust rather than hand-sorted. A recurring drop (E4) collects onto its thread. A cross-context implication (E2 implicit) gets flagged in a background pass.

## What its `/spec` (after `/scope`) must settle
- **Explicit vs implicit extraction (E2):** explicit = clear trigger ("this is a job-contact" → offer UI-filing entry, E1); implicit = a background/"sleep-cycle" pass surfacing cross-thing implications. Two modes — scope both, spec the explicit one first.
- **Typing taxonomy** — shared with schema **`tags`** (multi-valued; one entry → many tags). Who owns the tag vocabulary.
- **Tag-whole-entry vs SEGMENT (Levi 2026-06-23):** since one entry can hold multiple types of info (e.g. a single Dropper drop with sleep+meds+exercise+devos), decide whether ingest **tags the whole entry** with a set, or **segments** it into typed sub-pieces/spans (each separately routable). Likely both — tag in v1, segment when a downstream consumer needs the pieces apart. Scope this explicitly.
- **Routing targets** — what a drop can route *to* (thread, project folder, action offer) and how actions are proposed (E1's "want me to prepare this?" pattern).
- **Dynamic temporal resolution (E3):** "today"/"Saturday" → dated links.
- Accuracy/confidence model + the human-steer loop (async, non-blocking — P4).

## Tagged §0 items
E1 job-contact→action · E2 explicit-vs-implicit · E3 temporal resolution · E4 recurrence · E5 use-case examples (birthdays, "where is home?") · S5 thing-spawning-from-event · P4 async steering.

## Dependencies
Schema (slot 1) **thread-aware**; a corpus from capture (slots 2–3). Feeds the ledger (slot 5).

## Derived direction (from orchestrator)
- **Expect a `/scope` before `/spec`.** This is the least-resolved part; level it honestly.
- Lead with **explicit** extraction (tractable, demoable — the E1 job-contact flow is the canonical example); treat **implicit** as a second, background mode.
- This is where **S3 leveling** actually lives — getting altitude assignment right here is the project's core value. Watch how it interacts with the schema's altitude field (§4).
- Human stays in the loop but is *steering*, not *sorting* — never reintroduce manual sort as the default.
