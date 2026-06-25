# DP-1 §1 — Strategy (S3 top)

*Run: DP-1, 2026-06-23. Strategic altitude only — positioning, the arc, "done enough." No architecture resolved here (that's §2). AI-drafted from Levi's inputs; framework claims in brainstorming voice.*

---

## The problem (why this exists)

**Levi, 6/23 18:20 (verbatim core):** *"I still have to do too much of my context and entry management manually in the Excel. We need to move toward better tracking of things to make this work properly and save me time and effort. Simultaneously, we will develop the thinking and architecture to make Collevity a reality."*

Today's capture is frictionless but **flat and untyped** — an 852-row `Thing` stream with two timestamps and nothing else. Everything that makes a drop *useful* — what kind of thing it is, what altitude it lives at, whether it's a plan or a record, what it connects to — is reconstructed **by hand, every time**, in the checkin and in orchestration. That manual reconstruction is the tax. It doesn't scale (the Dropper is "getting too long," 6/18 17:37), and it's the bottleneck between *capturing* a life and *orchestrating* one.

**The strategic bet:** move the structure-making from manual/per-session into a **standing pipeline** — capture → store → ingest → thread — so that the structure is *derived once, persists, and accrues*. Frictionless capture stays; the typing/leveling/threading becomes the system's job, not Levi's.

## Positioning (where this sits in the broader context)

- **The spine of Collevity, not a feature.** Levi's own decomposition (6/23 16:54): Collevity ≈ orchestrator · dropper · management tools, and "what is the LCD that builds all of them?" This pipeline **is** the dropper-spine + the store every other part reads. Get this right and the orchestrator + management tools have a substrate; get it wrong and they're building on sand.
- **Privacy/locality posture (6/17 14:15):** a personal-files environment — local / on-edge compute — sidesteps HIPAA-class concerns. Strategy constraint: **default to local, single-user, file-based.** (Reinforces the JSONL-first instinct.)
- **Multi-modal capture is the real boundary (P5, [[collevity-architecture-inputs]]):** Dropper text is one surface; notebook, prayer journal, index cards, whiteboard are others. The store must be **capture-surface-agnostic** — ingestion absorbs from many writers, not Dropper-only. (Day-one writers: mobile shortcut + prompt hook + existing Excel; others later.)
- **Async, non-blocking orchestration (P4, 6/18 16:57):** the eventual system shouldn't *block* on user response — abridge with a timeout, queue an approve/disapprove, keep moving (esp. low-stakes protocols). Not built here, but the **store/thread design must not assume synchronous human confirmation** — threads carry a pending/approved state rather than waiting.
- **Vision frame (P6):** "tired of a million apps"; "we're not digital people." The pipeline consolidates scattered capture into one substrate and must not force life into digital rigidity — analog surfaces stay first-class inputs.

## The arc — capture → store → ingest → thread

| Stage | What it does | Parts | Today |
|---|---|---|---|
| **Capture** | frictionless drop, any surface | mobile shortcut · prompt-capture hook · app wrapper | Excel + manual |
| **Store** | one typed, queryable, versioned pool | **JSONL schema (keystone)** | 3 flat columns |
| **Ingest** | derive structure from raw drops | thread extraction / typing / routing | by hand in checkin |
| **Thread** | persistent, navigable lines of meaning | thread ledger | doesn't exist |

The two enablers Levi named map onto this arc: **(a) S3 leveling** = the ingest layer assigning altitude, and **(b) clean threads from the user** = capture shaped so drops *arrive* more thread-ready.

### First landmark (v1 emphasis, Levi 2026-06-23)
**The first guiding landmark is capturing raw USER entries.** Everything else — agent-authored entries, richer multi-author provenance, other capture sources — comes *later* and must be **additive**, not built into v1. Practical consequences:
- v1 `author` ≈ always **user**; the provenance-*chain* machinery (S4) is scaffolded in the schema but not exercised yet.
- **`source` still varies in v1** even with author=user (dropper · mobile · claude-hook) — keep it first-class.
- A drop made *inside* a Claude session (prompt-capture hook) is **still a user entry** (author=user, source=claude-hook) → in scope. Agent-*authored* content is the deferred "more than that."
- This keeps v1 honest to the friction guarantee: optimize for the user dropping raw text cheaply; don't pay for the multi-author case before it's needed.

## "Done enough" (project end-state, strategic altitude)

The pipeline is **done enough** when:
1. **Capture is still frictionless** — a drop is as cheap as today (≤ a few seconds, any surface), and ideally cheaper-to-thread.
2. **The store is typed and queryable** — a drop carries (or gets derived) kind/type, altitude, now-horizon, provenance, identity+version; and the corpus is queryable beyond a per-day scan.
3. **Drops become threads** — recurring/connected drops collect into persistent, typed, leveled threads automatically, surfaced for light human steering — *not* hand-curated.
4. **Orchestration reads clean** — a session can pull "what's live, at what altitude" from threads instead of re-deriving it from raw rows. **This is the payoff: clean orchestration.**
5. **Nothing existing breaks** — checkin/daily-tracking keep working throughout (additive migration).

**Explicitly NOT done-enough criteria** (downstream, confirmed out — §0 M2): reporting/review layer, Apple Health integration, Adam's app, second-brain research. They *consume* this store later; they are not gates on it.

## Strategic risks / what could make this wrong

- **Over-structuring capture.** If typing/leveling leaks back into the *capture* moment, friction returns and the whole premise dies. Discipline: **structure is derived (ingest), not demanded (capture).** The `_TEMPLATE.md` DNA — "core vs extraction is about *how*, not how much" — is the guardrail.
- **Schema premature-concretization.** The schema must expand a lot (Levi, 6/23), but §2 settles only *scope-shape*; over-speccing fields now risks locking the taxonomy before usage reveals it. Discipline: **let usage reveal promotion** (the template's stance), ship a schema that can grow.
- **Thread layer is genuinely fuzzy.** Extraction/typing/routing + ledger are the least-understood parts; expect scope, not spec. Don't fake spec-readiness there.

## Operative-path seed (set for real in §2)

Inherited from `01_STRATEGY/strategy-scope-spec.md` (2026-05-28 scope output): *Dropper→JSONL first, capture hook second, orchestrator only after a corpus exists.* §2 refines this across all six parts.

---
*Next: §2 scope — settle the schema scope-shape (the keystone), set the operative path, level each part.*
