# DP-1 — Dropper Pipeline: Orchestration Prompt (A3 ∘ S3 run)

**Layer (orch view):** scope → spec-stubs + orchestration setup (a deliberate A3∘S3 pass; **not a build session**)
**Status:** authored 2026-06-23; revised (red-team) 2026-06-23. Not yet launched.
**Absorbs:** `../foundation-orchestration/session-prompts/Spe-B_dropper-pipeline.md` (capture→store→ingest) as the lower half.
**Project home:** `./README.md` · **Tracker:** `./PROGRESS.md`

---

## Mandate — what this session is *for* (ranked, not co-equal)

1. **PRIMARY — the work.** Take the **full Dropper umbrella** (capture→store→ingest→thread) through A3∘S3 and emit a clean **leveled, dispatch-ready spec-stub decomposition.** This is the deliverable. **Build no code.**
2. **BY-PRODUCT — the framework.** The instruments get tested *by doing #1 well* — A3 in §0/§2, S3 across §1–§3. **§4 just captures, lightly, how they performed.** Do not let framework-noting compete with #1 for the session's energy.
3. **MECHANISM — orchestration.** Stand the project up: tracker + per-part launch packets, ready to dispatch each part's `/spec` later.

**Why the full umbrella (deconflicted):** clean orchestration genuinely *requires the whole capture→thread arc* — capture alone doesn't make threads clean. The umbrella is chosen for the **product**. That it's big enough to stress-test S3/A3 is the **welcome consequence** — the Dropper being primary is precisely what makes it the vehicle for framework development (Levi, 2026-06-23). Sprawl is contained because the session **stops at spec-stubs.**

## The instruments (one-line each; full model in framework-dev)

- **A3 = arrangement** (Assess→Aggregate→Assimilate). Reveals the map of *things*. Used in **§0** (over sources) and **§2** (over parts).
- **S3 = movement** (Strategy→Scope→Spec). Travels the *levels* toward built. Used across **§1–§3**.
- Model + the verb/noun-vs-static/dynamic resolution: `../collevistic-framework-dev/S3-A3-pairing-model.md`. Treat as the **opening hypothesis §4 tests**, not settled law.

## Output contract

- `deliverables/00_context-assessment.md` (§0 map) · `01_strategy.md` · `02_scope.md` (schema scope-shape + operative path) · `03_spec-stubs/` (one per part) · `04_S3-A3-notes.md`.
- `PROGRESS.md` updated. **No code. No built artifacts.** Build itch → log as a thread, move on.
- Session is done only when the **Done-check** (bottom) passes.

---

## §Goal — derive & confirm the end-state *(active first step)*

Don't treat the goal as given. State the known purpose, then **confirm/refine with Levi before §0:**
- *Known purpose:* improve Dropper + session management → **clean orchestration.** Enablers Levi named: **(a) S3 leveling**, **(b) clean threads from user.**
- *Project end-state:* capture frictionless **and** drops → typed, leveled threads feeding clean orchestration.
- *This session's end-state:* the umbrella, A3∘S3-decomposed into leveled, dispatch-ready spec-stubs + light framework notes. **No build.**

## §0 — A3 over the information *(the info-review; also dogfoods the thread-extraction)*

A real Assess→Aggregate→Assimilate pass — and a **hand-run of the thread-extraction the project will automate.** Capture the pain/requirements *lightly* as you go (feeds §4 + the thread stub); don't let meta-observation slow the sweep.

- **ASSESS — bounded sweep.** Mine the **Dropper** for pipeline/Collevity/Dropper-design items (`read_dropper_day.py` / row search — actually read, don't just cite). **Bound it:** relevance-filter to pipeline-relevant items only; **prioritize the known design-dump days (6/17–6/18) + recent**; stop when new days stop yielding pipeline items. Also sweep: substrate (`Dropper_excel.xlsm`, `_TEMPLATE.md` + recent daily logs), strategy (`../foundation-orchestration/convergence-block-scope.md`, memories `[[current-phase]]`/`[[collevity]]`/`[[collevity-architecture-inputs]]`), framework (`01_STRATEGY/strategy-scope-spec.md`, the A3 note, the 2026-06-04 log "threads/insights", and `../collevistic-framework-dev/S3-A3-pairing-model.md`).
- **AGGREGATE — sort every item into THREE buckets** (this is the deconfliction):
  1. **project-level** → strategy/scope;
  2. **part-level** → tagged to a specific part (carries into that part's §3 stub — see §3);
  3. **route-elsewhere / out-of-scope** → not this project (e.g. "Adam's app"); name its real home, drop it from the pipeline.
- **ASSIMILATE** — the coherent working picture + **FOUND / MISSING.** **Surface MISSING to Levi first.** Don't start §1 until resolved (or green-lit).

## §1 — Strategy *(S3 top)*

Position the project: the problem, the capture→store→ingest→thread arc, project-level "done enough." Strategic altitude only — **do not resolve architecture here.** Output: `01_strategy.md`.

## §2 — Scope *(S3 mid, via inner A3)*

Run A3 over the **parts** (mobile shortcut · prompt-capture hook · JSONL schema · app wrapper · thread extraction/typing/routing · thread ledger): Assess parts/deps/open-Qs → Aggregate into clean units → Assimilate the scope.

- **Keystone = the JSONL schema.** In §2, settle only its **scope-shape** — the architectural calls that *unblock other parts*: `things` vs `events` split (taxonomy seed), id/dedupe strategy, one-pool vs per-context, and **actual-vs-projected / now-horizon** (a drop is a plan *or* a log). **The field-level schema *spec* is a §3 stub, not a §2 decision** — don't over-resolve here.
  - ⚠️ **Altitude note (a live S3 test):** where schema-work sits (scope-shape vs spec-detail) is exactly the kind of leveling S3 is meant to adjudicate. **Watch it and record it for §4** — this ambiguity is *data*, not a defect.
- **Compatibility constraint (hard):** the new store must keep feeding the **existing daily-tracking/checkin extraction** (`read_dropper_day.py`, `_TEMPLATE.md`). Do not design a store that breaks the current flow.
- Set the **operative path** (optimized forward sequence — *not* rigid critical-path) — it sets dispatch order even though nothing's built.
- Per part: assign **altitude** + spec-readiness. **This leveling is the S3 test — watch it (§4).** Output: `02_scope.md`.

## §3 — Spec stubs *(S3 bottom — stubs/packets only)*

Per part, emit a **launch packet** in `03_spec-stubs/`: problem statement · inputs/outputs · "done" · what its `/spec` must settle · operative-path slot · dependencies · **the §0 part-level items tagged to it** (close the assess→stub loop) · derived direction from this orchestrator (strategic context + constraints, so the `/spec` runs cold). The **JSONL schema** gets its own field-level spec-stub here, distinct from the §2 scope-shape. **Stop at stubs/packets — `/spec`-ready, not specced, not built.**

## §4 — S3 / A3 framework notes *(by-product — keep light)*

Lightweight capture *as exhaust*, not a separate effort. Note: where S3 layering caught a conflation / forced a decision to the right altitude — or broke; where the **schema altitude-tension** (§2) landed; how A3 performed in **both** uses (§0 sweep + §2 arrangement) and whether the **recursion** clarified or confused; whether the `S3-A3-pairing-model` hypothesis held. Vocabulary stress-tested. **In-flux discipline:** route to `../collevistic-framework-dev/` as brainstorming input; credibility-cascade tag (AI- vs Levi-authored). Output: `04_S3-A3-notes.md`.

## §5 — Orchestration, progress, sizing

- **Tracker:** maintain `./PROGRESS.md` — parts × state (pending → stub-ready → spec'd → built).
- **Session sizing:** §0-sweep + §1 + §2-over-6-parts + §3-×6 + §4 is **a lot for one session.** Natural breakpoints: **(§Goal+§0+§1)** as pass A, **(§2+§3)** as pass B, framework notes folded in. If context tightens, checkpoint to the deliverables files and resume — **do not attempt `/spec` dispatch in the same session.**
- **Launch packets:** each §3 stub runs its `/spec` cold later.
- **Guarded dispatch:** the orchestrator **may launch a part's `/spec`** on Levi's greenlight (`/spec` is spec-altitude — inside the no-build floor). **Implementation/code is out** this round. Default: produce packets + tracker; dispatch only on "go."

## §6 — Guardrails

- **No code built.** Spec-stubs/packets are floor and ceiling. Dispatching `/spec` is allowed; building is not.
- **Don't break the existing daily-tracking/checkin extraction** (the compatibility constraint).
- **Bound the §0 sweep** — relevance filter + stopping rule; don't read the whole Dropper history.
- **Don't rabbit-hole** the app-wrapper (Excel replacement) — scope, stub, move on.
- **Brainstorming voice** on framework claims — Levi's inputs to pull from, not rulings.
- **Surface ambiguities; don't resolve unilaterally.**

## Done-check *(session is complete only when all true)*

- [ ] End-state confirmed with Levi (§Goal).
- [ ] §0 map emitted; MISSING surfaced; every swept item in one of the 3 buckets.
- [ ] `01_strategy.md` + `02_scope.md` written; **schema scope-shape settled**; operative path set; compatibility constraint honored.
- [ ] One **spec-stub per part**, each with: bounded scope, named "done", op-path slot, deps, its tagged §0 part-level items, derived direction.
- [ ] `04_S3-A3-notes.md` captured (light); `PROGRESS.md` updated.
- [ ] **No code built.**

## Ambiguities to resolve at kickoff

1. JSONL vs faster/queryable store (start JSONL; revisit if query speed bites).
2. `things` vs `events` — one pool or per-context subsets?
3. App-wrapper stack — native (Swift, ties to MTD learning) vs lightweight local web?
4. Mobile shortcut writes the same store the wrapper reads, day one?
5. Thread ledger — part of the store or a derived view? Where does it live, and **how does it relate to the existing daily-tracking log** (both hold "what happened" — avoid duplication/conflict)?
