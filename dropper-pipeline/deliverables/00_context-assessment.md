# DP-1 §0 — Context Assessment (A3 over the information)

*Run: DP-1, 2026-06-23. A3 = Assess → Aggregate → Assimilate, run over the source material. Also a hand-run of the thread-extraction the project will automate (dogfood). Brainstorming-voice; AI-aggregated from Levi's inputs.*

---

## ASSESS — what was swept (bounded)

**Stopping rule applied:** relevance-filter to pipeline-relevant items; prioritized the 6/17–6/18 design-dump days + recent; stopped when 6/19–6/21 stopped yielding pipeline items (they did — 0–5 entries, none pipeline-relevant).

- **Dropper** (`read_dropper_day.py` over 6/17, 6/18, 6/22, 6/23 fully; 6/19–6/21 filtered). Actually read, not cited.
- **Substrate:** `Dropper_excel.xlsm` (inspected directly — see below), `_TEMPLATE.md`, recent daily logs.
- **Strategy:** `convergence-block-scope.md`, memories [[current-phase]] / [[collevity]] / [[collevity-architecture-inputs]], [[dropper-pipeline]].
- **Framework:** `01_STRATEGY/strategy-scope-spec.md` (S3 canonical), `S3-A3-pairing-model.md` (the §4 hypothesis).

### Substrate ground-truth (the most load-bearing finding)
The live Dropper is **3 columns, 852 rows, one flat untyped pool:**

| Col | Header | Meaning |
|---|---|---|
| D | **`Thing`** | the captured text — already named with the THING-ontology root |
| E | `Timestamp` | created time (Excel serial; **no timezone** — MDT/EDT ambiguity is real, see items) |
| F | `modified` | last-edit time — **crude edit-after-fact / versioning already exists** |

**Implication:** typing, leveling, and threading do **not** exist at capture today. They must be *derived* (the ingest→thread layer), layered on top **without breaking flat frictionless capture or the per-day read** the checkin depends on. This is the whole shape of the project in one table.

### Compatibility constraint (hard, confirmed)
`read_dropper_day.py` filters rows by `E`'s date and emits `D` text per day → feeds `/checkin`. Any new store must keep yielding **{text, created-timestamp}** per day. The `_TEMPLATE.md` already encodes the design DNA: **core metrics = hand-entered capture; extraction targets = derived from the stream; presence-only; value+comment, no taxonomy yet; "anything can be promoted to core."** The pipeline is the automation of that "derived from the stream" half.

---

## AGGREGATE — every swept item sorted into 3 buckets

### Bucket 1 — PROJECT-LEVEL (→ strategy / scope)
- **P1. The core problem (Levi, 6/23 18:20):** "too much manual context/entry management in the Excel… move toward better tracking of *things*… simultaneously develop the architecture to make Collevity real." → this *is* §1 strategy.
- **P2. Local/private deployment posture (6/17 14:15):** value of Collevity in a personal-files env — local / on-edge compute to avoid HIPAA etc. → strategy constraint (privacy/locality).
- **P3. Collevity decomposed into core parts (6/23 16:54):** orchestrator · dropper · management tools · "what is the LCD that builds all of them?" → strategy framing; the pipeline is the dropper+ingest spine.
- **P4. Async / non-blocking orchestration (6/18 16:57):** "user response needed" can be abridged with a timeout, queued as approve/disapprove, without holding up the program (e.g. sleep protocols). → strategy behavior; tag also to routing.
- **P5. Capture across modalities ([[collevity-architecture-inputs]]):** Dropper, notebook, prayer journal, index cards, whiteboard — ingestion should absorb from each, not require Dropper-only. → strategy scope-edge; capture part.
- **P6. Vision one-liners:** "tired of a million apps"; "we're not digital people." → strategy/vision framing only.

### Bucket 2 — PART-LEVEL (→ tagged to a part, carries into that part's §3 stub)

**→ JSONL schema (keystone):**
- **S1. Now-horizon tension (6/18 17:00):** a drop is a *plan* OR a *log of what happened* — "actual vs projected" — credibility differs. **Keystone scope-shape call.**
- **S2. Timezone (6/17 14:49, 21:01; 6/23 15:57):** timestamps were MDT vs EDT; "setup dropper to do UTC + flag current timezone." → schema: store UTC + tz.
- **S3. Versioning / plans-into-histories (6/18 17:38; the live `modified` col):** "plans updated such that they're versioned into histories." → schema: identity + revision history.
- **S4. Attribution / provenance (6/23 19:02):** AI vs user vs which agent — "a chain of citations" when a thing has both user + agentic contributions. → schema: provenance field.
- **S5. THING parent ontology ([[collevity-architecture-inputs]]; col D literally `Thing`):** THING root with Purpose/Function/Name; sub-classes (triggers/milestones/segments/states/protocols). → schema: `things` vs `events` taxonomy seed.
- **S6. Persistence tiers / triage ([[collevity-architecture-inputs]]):** not single saved-forever; tiers + a "worth-promoting?" filter; Dropper "getting too long, needs cutting/filtering" (6/18 17:37). → schema/store: persistence-tier field + archival.
- **S7. Drop *types* observed in the wild (6/22):** task, recurring-task, job-contact, money, planning-question — real type vocabulary to seed the taxonomy.

**→ Thread extraction / typing / routing:**
- **E1. Job-contact recognition → action offer (6/18 17:41):** system flags "this is a job contact," offers to prep a UI-filing entry. → the canonical extraction→routing example.
- **E2. Explicit vs implicit extraction (6/23 18:06):** explicit = clearly triggers project/db add; implicit = a background/sleep-cycle pass that finds cross-implications for *other* things. → two-mode extraction.
- **E3. Dynamic temporal reference resolution (6/22 14:59):** an extractor that resolves "today"/"Saturday" to dated links dynamically. → extraction capability.
- **E4. Recurrence (6/22 15:00):** recurring tasks (clean bathroom). → type + extraction.
- **E5. Use-case examples (6/17):** birthdays, "where is home?" — date-anchored / entity reference cases. → extraction test cases.

**→ App wrapper (Excel replacement):**
- **A1. File-dropper app w/ filing UX (6/18 17:44):** drop → offer to attach posting/email, rename to convention, move to location, optionally launch a file-organizer agent.
- **A2. Edit-after-the-fact UI ([[collevity-architecture-inputs]]; `modified` col already exists):** panel above the raw store to edit past entries. Tension flagged: does editing violate "log = truth"?

**→ Mobile shortcut / prompt-capture hook:** (no new §0 items beyond "writes the same store" — see ambiguities #4.)

### Bucket 3 — ROUTE-ELSEWHERE / OUT-OF-SCOPE (named home, dropped from pipeline)
- **X1. Adam's app (6/18 17:32; 6/23 16:33):** review/advise/maybe-dev. → its own thread/project. **Not this pipeline.**
- **X2. Daily-tracking metric design (6/17 21:44):** anxiety as a separate metric; acuity/focus merge. → `_TEMPLATE.md` core-metrics design, not the pipeline.
- **X3. Output-side reporting & review protocols ([[collevity-architecture-inputs]]):** weekly-report-from-data; day/week/month/year review protocols; habit-promotion/retire mechanism. → a **reporting/review layer** (downstream consumer of the store), distinct from capture→thread. *Depends on this pipeline but isn't a part of it.*
- **X4. Apple Health integration ([[collevity-architecture-inputs]]):** auto-derived vs manual field category. → future store-source category; **parked** (don't widen DP-1).
- **X5. Numerical-scale drift / normalization:** → future analytics, not the pipeline.
- **X6. Second-brain research (6/23 16:27):** research existing tools, "segment so Collevity uses independent thinking." → a research thread (reference), not a build part.
- **X7. A3/S3 conceptual statements (6/23 18:59, 19:28):** → routed to `04_S3-A3-notes.md` (framework bucket), not the product.

---

## ASSIMILATE — the coherent working picture

**One picture:** Today there's a frictionless flat capture (Dropper = untyped `Thing` stream) and a hand-run derivation (checkin reads the day, a human + AI infer structure). The pipeline's job is to **make the derivation a real layer** — typed, leveled, threaded — *without* taxing capture and *without* breaking the per-day read. The **JSONL schema is the hinge**: it's where capture's flatness meets the structure the upper half needs. Every part either writes that store (capture: shortcut, hook, wrapper) or reads/enriches it (ingest: extraction→typing→routing→ledger).

**The keystone tension, named:** the schema must hold a thing that may be a **plan or a log** (now-horizon, S1), may be **revised over time** (S3/`modified`), may be **contributed by user or agent** (S4/attribution), and may be **a thing or an event** (S5/THING). Settling the *scope-shape* of these in §2 unblocks every other part; the *field-level spec* is a §3 stub.

### FOUND (sufficient to proceed)
Problem statement, substrate ground-truth, compatibility contract, the full part list, design DNA (`_TEMPLATE.md`), operative-path seed (strategy-scope-spec: *JSONL first → capture hook → orchestrator after corpus*), the framework hypothesis. **All six parts have enough §0 material to stub.**

### MISSING / ELSEWHERE (surface before §1)
- **M1 (ELSEWHERE, non-blocking):** DayOne data-structure reference lives in an external app, not the filesystem — can't sweep it. Note as a §3 design-research item for the schema stub, not a blocker.
- **M2 (RESOLVED — Levi, 2026-06-23):** all four Bucket-3 clusters (reporting/review X3, Apple Health X4, Adam's app X1, second-brain research X6) confirmed **OUT** of DP-1's parts — downstream consumers / separate threads. Part list unchanged: schema · mobile shortcut · prompt-capture hook · app wrapper · extraction/typing/routing · thread ledger.
- **M3 (needs Levi — the keystone scope-shape inputs):** the kickoff ambiguities (#1–#5) are genuinely §2 decisions, but #2 (one pool vs per-context) and #5 (ledger vs daily-log relationship) shape the schema scope-shape. Flagged for §2, surfaced now so they don't ambush the leveling.

**No part is blocked by missing *data*.** The only true gates are Levi's routing/scope confirmations (M2/M3) — judgment calls, not lookups.
