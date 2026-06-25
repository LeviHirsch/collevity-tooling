# Spec-stub — App Wrapper (Excel replacement) · op-path slot 6

*DP-1 §3 launch packet. **Scope/spec, low readiness, deferred to last.** Stack decision (amb #3) open. Guardrail: do NOT rabbit-hole — scope, stub, move on.*

## Problem statement
The Excel is the current capture+view surface and it's the manual-management bottleneck (the core problem, P1). The eventual replacement is a real app: drop, view, **edit-after-the-fact** (A2), and a **filing UX** (A1) — drop a job-contact → offer to attach posting/email, rename to convention, move to location, maybe launch a file-organizer agent. This is the biggest, hardest part; it's deferred because the shortcut + hook + existing Excel cover capture in the interim.

## Inputs
- The JSONL schema (slot 1) — the wrapper reads/writes the same pool.
- Extraction/routing (slot 4) — the filing UX surfaces its action offers.
- The live `modified` column — edit-after-fact already half-exists in the data model.

## Outputs
- An app (stack TBD) that reads the pool, presents drops, supports post-hoc edit, and offers filing actions on typed drops.

## "Done" (scope-level)
The wrapper can fully replace day-to-day Excel use: drop, browse, edit a past entry, and act on a routed drop — without breaking the pool's single-source-of-truth or checkin.

## What its `/scope`→`/spec` must settle
- **[amb #3] Stack:** native Swift (ties to Levi's MTD/Swift learning thread; iOS-native capture) vs lightweight local web (faster, cross-device, matches local/private posture). **Orchestrator leaning:** local web for v1 speed unless the Swift-learning payoff is wanted — but this is genuinely Levi's call; surface it.
- **Edit-after-fact + "log = truth" tension (A2):** does editing a past drop rewrite or append-a-revision? (Schema is append-only → revision; reconcile the UX with that.)
- **Filing UX scope (A1):** how much of the rename/move/organize flow is in v1 vs a later file-organizer-agent integration. Bound it hard.

## Tagged §0 items
A1 filing UX · A2 edit-after-fact UI · P1 (the Excel-bottleneck this retires) · P5 (one more capture/view surface).

## Dependencies
Schema (slot 1); ideally extraction (slot 4) for the filing UX. Op-path slot 6 (last).

## Derived direction (from orchestrator)
- **Deferred for a reason** — capture is covered meanwhile; don't let this expand and eat the project (explicit guardrail).
- Append-revision, not in-place mutation, to stay consistent with the schema and preserve "plans versioned into histories."
- Bound the filing UX to a thin v1; the full file-organizer-agent is a later integration, not this stub.
