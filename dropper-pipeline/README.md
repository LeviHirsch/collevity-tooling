# Dropper Pipeline
*Seeded 2026-06-23. Live project thread — accumulates real work + content, not just a launch prompt.*

## What this project is

Build the end-to-end Dropper pipeline — **capture → store → ingest → thread** — to the point where personal capture stays frictionless **and** drops become clean, typed, properly-leveled threads that feed **clean orchestration.** Absorbs the old `Spe-B` (capture→store) as its lower half and adds the thread/ingest layer as its upper half.

Chosen deliberately as the **full umbrella** (not a bounded slice) because the messy, multi-altitude scope is the **test fixture that forces the S3 / A3 instruments to earn their keep** (Levi, 2026-06-23).

## Dual purpose

1. **The work** — stand up and (eventually) build the pipeline.
2. **The framework** — first **joint test of S3 (movement) + A3 (arrangement)**; the run emits notes on how both instruments actually performed. Grows the Collevity framework. (This is the test role the deferred `convergence-block` was meant to play.)

## End-state (two altitudes)

- **Project end-state:** capture→store→ingest→thread working well enough that orchestration is clean — frictionless capture, a queryable store, and drops that become typed, leveled threads.
- **First-session end-state (DP-1 run):** the whole umbrella, **A3∘S3-decomposed into leveled, dispatch-ready spec-stubs + framework notes.** No code built.

## Contents

- `README.md` — this file. Project home.
- `ORCHESTRATION-PROMPT.md` — **DP-1**, the launch prompt = orchestrator. Runs the A3∘S3 process, stands up the parts, dispatches per-part `/spec`. **Read to launch.**
- `PROGRESS.md` — the parts board (parts × state); the orchestrator maintains it.
- `deliverables/` — outputs the run writes (context-assessment, strategy, scope, spec-stubs, S3/A3 notes). *Created by the run — not pre-scaffolded (oversaving guard).*

## Conventions

Follows `foundation-orchestration/README.md` (session-card format, ID convention `DP-N`, inline ambiguity-surfacing, oversaving guard — save artifacts, not construction chatter). Supersedes the earlier `foundation-orchestration/session-prompts/DP-1_*` location.

## Status

Authored 2026-06-23. **Not yet launched.** DP-1 ready to run.

## Related

- [[strategy-scope-spec]] (S3) · A3 note: `../apple-notes-export/0580_A3_Architecture/note.md`
- `../foundation-orchestration/convergence-block-scope.md` (sibling S3 test, deferred)
- [[collevity]] · [[collevity-architecture-inputs]] · [[orchestration-conventions]]
- Framework notes route to `../collevistic-framework-dev/` (IN-FLUX — brainstorming input only; credibility-cascade tagging).
