# Spec-stub — Prompt-Capture Hook · op-path slot 3

*DP-1 §3 launch packet. Spec-ready (med-high); `ingestion/claude-sessions/` already exists as a seed.*

## Problem statement
A lot of Levi's real thinking happens *in Claude sessions* (this one included). Today those drops live only in the conversation or get hand-promoted. A hook should capture session-side drops into the same store, with correct **attribution** (user vs which agent).

## Inputs
- The JSONL schema (slot 1) — esp. the provenance/attribution shape (S4).
- `ingestion/claude-sessions/` (existing folder) + the session-save / SPP convention (`/session-save`).
- The distinction between a *drop* (worth storing) and ordinary conversation turns (triage — [[collevity-architecture-inputs]] persistence-triage).

## Outputs
- A hook/mechanism that, during or at the close of a session, writes selected drops to the pool with `author`/`provenance_chain` set (user, the agent, or a mix), `created_at` + `tz`.

## "Done"
A session can emit a drop to the pool with correct attribution, and a mixed user+AI contribution records a provenance *chain*, not a single author.

## What its `/spec` must settle
- Trigger: explicit ("drop this") vs automatic-with-triage vs at session-save. Likely all three; spec the default.
- The **triage filter** — what's worth promoting (persistence-triage insight: don't save low-value pull-only sessions).
- Attribution capture: how the chain is built when both user and agent contributed (S4 "chain of citations").
- Relationship to the existing SPP/session-save bundle — does this *replace*, *feed*, or *sit beside* it?

## Tagged §0 items
S4 attribution/provenance (primary) · persistence-triage ([[collevity-architecture-inputs]]) · P4 async (a queued drop shouldn't block the session).

## Dependencies
Schema (slot 1). Op-path slot 3. Pairs with `/session-save` (don't duplicate it).

## Derived direction (from orchestrator)
- Attribution is the reason this part is distinct from the mobile shortcut — make provenance first-class here.
- Respect triage: not every turn is a drop. Default to explicit + light triage, not save-everything.
- Don't block the session waiting on confirmation (async posture).
