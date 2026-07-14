# Dropper Pipeline — Progress Board
*Maintained by the DP-1 orchestrator. State: pending → stub-ready → spec'd → built.*

> Post-DP-1 snapshot (2026-06-23). A3∘S3 pass complete through §4. All parts now **stub-ready** (launch packets written). Altitudes/op-path set for real by the run. Next state = `spec'd` (run each `/spec`).

| Part | Half | Altitude (final) | State | Op-path order | Depends on | Stub |
|---|---|---|---|---|---|---|
| **JSONL schema** (keystone) | store | built | **built** ✅ (iter 1 closed 06-26; **iter 2 merged 07-11**: D1/D2/D3) | 1 | — | `deliverables/03_spec-stubs/1_jsonl-schema.md` |
| **Mobile shortcut** (wedge) | capture | spec | **stub-ready** | 2 | schema | `…/2_mobile-shortcut.md` |
| **Prompt-capture hook** | capture | built | **built + LIVE** ✅ (spec converged Rev 5 07-13 @ df51ed6; installed in `~/.claude/settings.json` + verified live — AC1–AC5 all green) | 3 | schema + D1–D3 ✅ | `…/3_prompt-capture-hook.md` → `parts/prompt-capture-hook/spec/` |
| **Minimal computer dropper + editable table view** *(new, DEC-007)* | capture/store | spec | **stub-ready** (split from wrapper; pulled forward; spike at `spikes/computer-dropper/`) | 4 | schema | `…/7_minimal-computer-dropper.md` |
| **Thread extraction/typing/routing** | ingest→thread | scope (needs `/scope` before `/spec`) | **stub-ready** | 5 | schema (thread-aware) + corpus | `…/4_thread-extraction.md` |
| **Thread ledger** | thread | scope | **stub-ready** | 6 | extraction | `…/5_thread-ledger.md` |
| **App wrapper** (full filing UX — hard) | capture | scope/spec | **stub-ready** (deferred last; Excel retires only after new part 4) | 7 | schema (+ extraction for filing UX) | `…/6_app-wrapper.md` |

> **Op-path change from provisional:** app wrapper moved 4→6 (expensive, non-blocking — shortcut+hook+Excel cover capture meanwhile); extraction+ledger pulled up to 4–5 (the actual payoff once capture flows).
> **Op-path change 07-11 (DEC-007 absorbed):** minimal computer dropper + editable view split from the wrapper and pulled forward to slot 4; extraction/ledger/wrapper shift to 5/6/7. Excel stays a transition capture channel until the new part 4 lands.

## Notes
- Keystone = **JSONL schema**; both halves (capture/store + ingest/thread) depend on it. Sequence it first.
- **Schema is a major expansion, not a port (Levi, 2026-06-23).** Today's store is 3 flat columns (`Thing`/`Timestamp`/`modified`); the new schema must grow far past that — type, level/altitude, now-horizon (plan vs log), tz-aware time, provenance/attribution, identity+versioning, persistence tier, thread links. §2 settles the *scope-shape* of that expansion; §3 specs the fields. The expansion is **additive** — it must still emit {text, created-ts}/day for checkin.
- The thread-layer parts are the fuzzier upper half — expect more scope, less spec-readiness.
- Op-path is **operative path** (optimized forward line), not a rigid dependency chain — reorder as the run finds better.

## Run log
- **2026-06-23 — DP-1 launched (this session).**
  - **§Goal — DONE.** End-state confirmed with Levi: stand up the Dropper pipeline (or move decisively toward it); clean orchestration is the downstream payoff. Checkpointed run + persistence requested.
  - **§0 — DONE.** Bounded Dropper sweep (6/17, 6/18, 6/22, 6/23 full; 6/19–6/21 dry → stopping rule met) + substrate + strategy + framework. Wrote `deliverables/00_context-assessment.md`: every item in 1 of 3 buckets (project / part / route-elsewhere); FOUND vs MISSING.
    - **Key finding:** live Dropper = 3 cols (`Thing`/`Timestamp`/`modified`), 852 rows, flat untyped pool. Typing/leveling/threading must be *derived*. **Schema needs major expansion (Levi confirmed).** Compatibility contract = keep yielding {text, created-ts}/day for checkin (expansion stays additive).
    - **M2 RESOLVED (Levi):** all 4 out-of-scope clusters confirmed OUT (reporting/review, Apple Health, Adam's app, second-brain research). Part list unchanged (6 parts). M3 ambiguities (#2 one-pool-vs-per-context, #5 ledger-vs-daily-log) deferred to §2 where they belong.
  - **§1 — DONE.** `deliverables/01_strategy.md`: problem (P1 manual-Excel tax), positioning (local/private, Collevity-spine, multi-modal, async), capture→store→ingest→thread arc, "done enough" (5 criteria), risks. Strategic altitude held — no architecture.
  - **§2 — DONE.** `deliverables/02_scope.md`: **schema scope-shape settled** — JSONL one append-only pool; `kind: thing|event` discriminator (per-context = views); now-horizon `actual|projected` + 3 time fields (UTC+tz); id/dedupe/provenance-chain/persistence-tier as scope-shape. Operative path set (1 schema → 2 shortcut → 3 hook → 4 extraction → 5 ledger → 6 wrapper). Compatibility constraint honored (additive migration + checkin shim).
  - **§3 — DONE.** Six launch packets in `deliverables/03_spec-stubs/` (1–6), each with problem/inputs/outputs/done/what-`/spec`-settles/tagged-§0-items/deps/derived-direction.
  - **§4 — DONE.** `deliverables/04_S3-A3-notes.md` (light): hypothesis mostly held; schema scope/spec seam = headline S3 win; A3 ran at 2 scales; §0 dogfood specced stub #4.
  - **CHECKPOINT — full A3∘S3 pass complete (§Goal→§5).** Stopped before any `/spec` dispatch (per session sizing: don't dispatch in the same session).
  - **SCHEMA DIRECTION (Levi-steered 2026-06-23, folded into §2 + schema stub):** model = **`entry` + orthogonal facets**; thing/event **demoted** to one axis (`entity_axis`), not master `kind`. Type = **multi-valued `tags`** (one entry, many types of info). Three distinct origin fields: `source`/channel · `author`/provenance · `context_ref`. **First landmark = raw USER entries** (author≈user in v1; agent-authored deferred/additive; source still varies).
  - **STILL-OPEN DECISIONS for Levi:** amb #4 shortcut writes same pool day-one · amb #5 ledger = derived view + sibling-to-daily-log framing · amb #3 app-wrapper stack (Swift vs local web) · extraction: tag-whole-entry vs segment (stub #4).
  - **NEXT (resume here):** Levi reviews deliverables + resolves the 4 open decisions → then **guarded dispatch**: run `/spec` for op-path slot 1 (JSONL schema) on greenlight. Slots 2–3 follow; slot 4 likely needs `/scope` first. **No build until specs exist.**
- **2026-06-23 (later) — JSONL SCHEMA `/spec` IN PROGRESS** (`parts/jsonl-schema/spec/`, greenfield, per-part folder, no git). Interview underway; decisions in `parts/jsonl-schema/spec/decisions.log` (DEC-001..007). Spec-process model confirmed: per-part `/spec`, gated by altitude, schema first (umbrella strategy/scope already = the pipeline-level spec). Iterative, not concurrent (interview is human-bottlenecked). Refinements from the interview that **amend earlier deliverables**:
  - **`entity_axis` DROPPED** (DEC-003/004): this part = the **horizontal time-stream (data lake)** only; the entity/"things" store is a **separate future vertical DB** (strata/mart on the lake) — out of scope. No `kind`/`entity_axis` field in v1 (deferred; `source`/`tags` distinguish future system events). *Supersedes §2's `entity_axis` facet.*
  - **Edits = in-place corrections, no revision/lineage** (DEC-006): "append-only" relaxed → append-on-drop, edit-in-place. *Supersedes §2's "append-only pool" + versioning-as-scope-shape.*
  - **Storage** (DEC-005): JSONL v1, logical schema kept storage-agnostic; ladder JSONL→SQLite→Postgres/Supabase preserved via a thin storage seam. JSONL doesn't lock out Supabase (Postgres JSONB).
  - **⚠ GAP + OP-PATH CHANGE (DEC-007, CONFIRMED by Levi):** today's Excel does 3 jobs (computer capture · whole-stream view · edit-older); op-path only restored them at the *last* part. **Fix:** keep Excel as a transition capture channel (`source: dropper-excel`, Excel→JSONL ingest), and **pull a minimal "computer dropper + editable table view over JSONL" forward** (right after schema+mobile), split from the full filing-UX wrapper (stays last). **Proposed new/re-sequenced part — add to the board.** Revised migration order: schema → (Excel ingested) → mobile → minimal computer dropper+view → retire Excel → … → full wrapper last.
  - **⏸ PAUSED 2026-06-23 evening — interview ~90% done.** All conceptual forks resolved (DEC-001..009); thin-stream principle adopted. Remaining: lock mechanical #1–#4 (id/dedupe, checkin-compat read_day, tz, horizon/times — agreed in substance, pending Levi's explicit "lock it"), then clarity gate, then `/spec seed` (fresh session).
    - **▶ RESUME COMMAND:** say **"continue the JSONL schema spec interview"** (or "resume DP-1 schema"). A fresh session: read this PROGRESS → `parts/jsonl-schema/spec/state.yaml` (phase `interviewing`) + the session file's **"⏸ PAUSED — resume checkpoint"** + `decisions.log` (DEC-001..009) → pick up at "Lock #1–#4." Do NOT restart the interview; resume it.
- **2026-06-26 — JSONL SCHEMA BUILT + LIVE → part 1 DONE.** `/spec` iteration 1 closed (greenfield, `parts/jsonl-schema/`): Phase 1 (schema + `append_entry`/`edit_entry`/`read_day`/`sync_sources` storage seam over append-dominant JSONL) + Phase 2 (Excel-blind bridge + sidecar + one-shot tz backfill). Audited + verified: **28/28 ACs PASS, 36 tests green**. Live migration run → `03_TACTIC/_DATA/collevity_lake.jsonl` (945 entries, outside the repo per DEC-022). Dropper↔lake seam validated end-to-end against live data (append / in-place edit / idempotent skip). `/checkin`'s `read_dropper_day.py` **repointed Excel→JSONL lake** — composes `sync_sources()`→`read_day()` itself (DEC-019), output format unchanged, day-filtering preserved. Spent backfill deleted (recoverable at git 782aaec). Decisions DEC-001..025 in `parts/jsonl-schema/spec/decisions.log`; takeaway in `…/spec/takeaway.md`.
    - **Keystone done → unblocks the rest.** Next op-path slots: **part 2 (mobile shortcut)** + **part 3 (prompt-capture hook)** — both capture surfaces that push directly via `append_entry` (no bridge). Each is its own `/spec`. Excel retirement waits on part 6 (native computer-capture surface). Which part is next = Levi's orchestration call.
- **2026-06-29 → 07-01 — HOOK SPEC (part 3) interview + revise + review 2.**
  `parts/prompt-capture-hook/spec/`: greenfield interview (06-29), revision 2
  per review 1 (DEC-009..015, 06-30), review panel 2 (07-01, archived, **not
  yet folded** — headline open call: AC4.3 error-sidecar keep/demote/cut).
  `phase: in-review`. Cross-part deps on part 1 identified: D1 read_day
  sub-minute order · D2 settle compaction · D3 concurrent-append safety.
  A 07-01 `/spec revise` session (saved 07-11, SPP `2026-07-11-1412_prompt-capture-hook-revise`)
  stopped mid-Turn-2; no spec changes committed — decisions D3/AC4.3 left open.
- **2026-07-11 — COLLEVITY FULL PASS (fork build) → RECONCILED + MERGED same day.**
  Workspace `02_CONTENT/collevity-full-pass_2026-07-11/` (class GENERATED; strategy
  docs there = unratified input). Under the isolate-as-fork directive, the pass
  built part-1 **iteration 2 (D1/D2/D3)** and **hook Phase 1** in a fork, tested
  against a live-lake COPY (1068 entries, rehearsal passed). Reconciliation
  (evening session): concurrent revise-session made **no spec changes** (decisions.log
  still ends DEC-015; spec_sha 418e29f unchanged; fork built against same revision) →
  **no drift; fork merged into this tree**: `lake.py` + tests (44/44 green in live
  tree) and `parts/prompt-capture-hook/{hook,tests,INSTALL.md}` (11/11 green).
  **D1/D2/D3 are now LANDED** — the SPP's open D3 sequencing question (A/B/C) is
  dissolved: safety lives in part-1 `append_entry`/`edit_entry` via `_pool_lock`
  flock sidecar, per DEC-015's direction. Record as a DEC when the hook spec
  converges. **Install fact:** part-1 venv does NOT have `collevity` importable —
  hook command must set PYTHONPATH (INSTALL.md). Tests must run from inside the
  part dir (`python -m pytest` cwd-on-path).
  **NEXT:** (1) Levi: git commit sweep (explicit paths — pre-existing dirty state
  first, then iter-2, then hook part; never `git add -A`), (2) resume `/spec revise`
  on hook spec — AC4.3 is the one open judgment (code as merged implements KEEP;
  cutting = delete `_breadcrumb` + 1 test), then converge, (3) guarded install per
  INSTALL.md — Levi's explicit go flips capture LIVE, (4) then part 2 (mobile
  shortcut) `/spec` (pre-spec finding: direct pool-write violates seam/id rules →
  inbox+bridge; see full-pass `07_mobile-shortcut-prespec.md`) or new part 4 stub.
- **2026-07-13 — HOOK (part 3) CONVERGED + INSTALLED + LIVE → part 3 DONE.**
  One session: `/spec check` (Rev 3 was structural → Levi chose rigor) → **three
  review→revise passes**. Pass 1 found a real gap — "never delay" untested against a
  *stall* (synchronous hook); fixed with an explicit **`timeout: 10`** on the hook
  entry (DEC-018; verified via Claude Code docs that a non-2 exit / signal-kill is
  non-blocking). Pass 2 found that fix's **torn-write-on-SIGKILL residual** (part-1's
  `_read_all` raises on a corrupt line) → accepted as low-probability (DEC-021), real
  hardening (reader tolerance / crash-safe append) **deferred to part-1** as
  `deferred.md` D-001 — not gating install. Pass 3 **clean on all three personas** →
  **converged at df51ed6** (DEC-022, human-judged). Also logged DEC-019 (live hook vs
  transcript-mining), DEC-020 (rejected review cuts). **Installed** the
  `UserPromptSubmit` entry in `~/.claude/settings.json` (Levi's explicit go; clean add,
  timeout 10, PYTHONPATH set). **Verified LIVE:** hook hot-loaded same-session and
  captured real cross-session prompts (global scope working — DEC-005/014); a fresh
  headless `claude -p` session captured a marker verbatim (user input only — **no system
  prompt**, per Levi's intent), correct on every field, `validate()` PASS, `read_day`
  surfaces it; fail-open drill (read-only lake path) → exit 0, empty stdout, one
  breadcrumb line, live lake untouched. **AC1–AC5 all green live.**
  **Remaining (formal spec closure):** `/spec verify` + `/spec close` on the hook spec
  (produce takeaway) — mechanical. One synthetic `HOOK-ROLLOUT-TEST` entry sits in the
  live lake (clearly marked; triage-droppable or removable on request).
  **NEXT part:** part 2 (mobile shortcut) `/spec`, or new part 4 (minimal computer
  dropper); part-1 iteration 3 candidate ACs = D-001 (crash-safe read/append) +
  id-bearing read (computer-dropper spike).
