# DP-1 §2 — Scope (S3 mid, via inner A3)

*Run: DP-1, 2026-06-23. Settles the **schema scope-shape** (the keystone — the calls that unblock other parts), the operative path, and per-part altitude. Field-level schema *spec* is a §3 stub, NOT decided here. Architectural calls below are reasoned defaults flagged **[CONFIRM]** where a real fork exists — made to keep moving per "go as far as you can," not silently settled.*

---

## Inner A3 over the parts

**Assess (parts · deps · open-Qs):**

| Part | Half | Depends on | Core open-Q |
|---|---|---|---|
| JSONL schema (keystone) | store | — | things/events shape; now-horizon; id/version; one-pool-vs-view |
| Mobile shortcut | capture | schema | writes the new store directly? (amb #4) |
| Prompt-capture hook | capture | schema | what to capture from a Claude session; attribution |
| App wrapper | capture | schema | stack: native Swift vs local web (amb #3) |
| Thread extraction/typing/routing | ingest→thread | schema (thread-aware) | explicit vs implicit; typing taxonomy; routing targets |
| Thread ledger | thread | extraction | part of store or derived view? relation to daily-log (amb #5) |

**Aggregate** → two clean clusters + the hinge: **capture writers** (shortcut, hook, wrapper) all *append* to the store; **ingest readers** (extraction, ledger) all *read+enrich* it. The **schema is the hinge** both clusters pivot on. So: settle the schema scope-shape first; everything else is "writes it" or "reads it."

**Assimilate** → the scope shape is **one append-only pool + derived views**, with the schema rich enough to carry the four tensions named in §0. Detail below.

---

## The keystone: JSONL schema scope-shape

Four architectural calls that unblock the other parts. (Field-level spec → §3 stub `schema`.)

### 1. Storage form — **JSONL, one append-only pool** `[SETTLED]`
- Levi's instinct (Dropper row 4: *"use jsonl for the backend datasets"*), reinforced by the local/private posture. Start JSONL; revisit a queryable store (sqlite/embeddings) **only if query speed bites** (amb #1). Vector embeddings (6/23 16:52) noted as a *future query-layer* concern, not a v1 store decision.
- **Append-only** + a `modified`/revision mechanism (the live Excel already has a `modified` column — keep that semantics). Edits don't mutate in place; they append a revision. This gives "plans versioned into histories" (S3, 6/18 17:38) for free.

### 2. `things` vs `events` — **one pool, `kind` discriminator; per-context is a VIEW** `[CONFIRM]`
- **Not** separate stores. A single pool where each record has `kind: thing | event` (amb #2 → answered: one pool).
  - **`event`** = a timestamped occurrence: a drop, a dose, an exercise set, a log line. Most raw Dropper rows are events. Has `occurred_at`.
  - **`thing`** = a persistent entity with identity: a project, person, protocol, habit, task, job-contact. Things are *referenced by* events and *accrue* them. THING-ontology root (col D is literally `Thing`; [[collevity-architecture-inputs]] THING parent: Purpose/Function/Name).
- A raw drop enters as an **event**; ingest may *spawn or link* a thing from it (e.g. "interview today" event → links to the `job-contact` thing). **Per-context subsets (work/health/faith) are queries/views over the one pool, not storage partitions.** Keeps "one substrate," supports cross-context implicit extraction (E2).
- **[CONFIRM]** this is the load-bearing taxonomy call — flag for Levi at the §2 review gate. Default chosen because it preserves single-substrate + matches the existing `Thing` framing.

> **⚠️ Levi pushback (2026-06-23) — `thing|event` may be too broad; reframe toward "entry + facets":**
> Levi: *"everything is an entry, but source matters and context references… event/thing might be too broad."* The correction (held as a strong consideration, to settle at the schema `/spec`):
> - **`entry` is the universal unit.** What varies are **orthogonal facets, each its own field** — don't overload one `kind`. The error is making `thing|event` the *master* discriminator.
> - **Entity-vs-occurrence ("thing-ness") demotes to ONE axis**, not the top type. It still earns its keep for **projection** (ledger leans thing-like; daily-log leans event-like) but isn't the primary cut. Fits THING-ontology: an event *is* a THING that happens to be an occurrence.
> - **Open call for `/spec`:** keep a coarse `kind` for fast projection, OR go straight to a **growable `type`** (task/log/plan/job-contact/prayer/dose…) with thing-ness as a *property*? Orchestrator lean = growable `type` (matches `_TEMPLATE.md` "usage reveals promotion"). **Levi's taxonomy call.**
> - **RESOLVED direction (Levi 2026-06-23): growable type, treated as MULTI-VALUED TAGS** — *"one entry could have multiple types of info."* So `tags: [..]` (a set), not a single `type`. Proven by the raw Dropper: one drop routinely carries sleep+meds+exercise+devos in a single entry. Open downstream Q (extraction, not schema): tag the whole entry vs **segment** it into typed pieces — see stub #4.

> **First-landmark scope (Levi 2026-06-23): v1 captures raw USER entries.** Author ≈ always user in v1; `source` still varies (dropper/mobile/claude-hook); agent-authored entries are deferred/additive. The provenance-chain (call 4) is *scaffolded but not exercised* yet. See `01_strategy.md` → "First landmark."

### 3. Now-horizon — **`horizon: actual | projected` + distinct time fields** `[SETTLED, from Levi]`
- Levi named this precisely (6/18 17:00): a drop is a *plan* **or** a *log of what happened*, and credibility differs. Schema carries:
  - `horizon: actual` (a log/record) vs `projected` (a plan/intent).
  - **Three distinct times:** `created_at` (when dropped) · `occurred_at` (when an `actual` happened) · `planned_for` (when a `projected` is meant to). Don't conflate them — today's single `Timestamp` does, which is the bug behind the MDT/EDT confusion.
- **Timezone (S2, 6/17 + 6/23 15:57):** all times **stored UTC + an explicit `tz` offset** captured at drop time. Fixes the MDT/EDT ambiguity at the root.

### 4. Identity, dedupe, provenance, persistence `[scope-shape only; fields → §3]`
- **Identity:** stable `id` per record (uuid). **Dedupe** on ingest by id (the migration assigns ids to the 852 rows; new writers generate them). Revisions share a lineage id.
- **Three orthogonal origin dimensions (S4 + Levi 2026-06-23) — do NOT collapse:**
  - **`source` / channel** — *through which surface the entry entered:* dropper-excel · mobile-shortcut · claude-hook · wrapper · notebook · … (Levi: "source matters… dropper vs mobile vs Claude prompt"). New first-class field.
  - **`author` / provenance** (S4, 6/23 19:02) — *who contributed:* `user | <agent-id>`, a **chain** for mixed records ("attribution is likely more a chain of citations"). A list, not a scalar.
  - **`context_ref`** — *the originating context:* session id / location / surrounding thread (the "where is home?" class of anchor). A back-pointer, distinct from the ingest-set `links`.
  - Independence is the point: a *user*-authored entry can arrive via *mobile* and reference a *Claude-session* context — three different fields. Field detail → §3.
- **Persistence tier (S6):** a `tier` / `retention` field (e.g. permanent · de-weighted · transient/auto-expire), backing the "not single saved-forever" + triage stance. Scope-shape only.

### Schema scope-shape, in one shape (illustrative, NOT the spec)
```
entry = {                            # "entry" = the universal unit (Levi)
  id, lineage_id,
  text,                              # col D "Thing" — preserved verbatim
  tags: [<growable>],                # MULTI-VALUED (Levi) — one entry, many types: [log, prayer, exercise]…
  entity_axis: thing|event?,         # DEMOTED to one facet (drives projection); maybe a property, not a kind — /spec call
  horizon: actual|projected,
  created_at, occurred_at?, planned_for?, tz,   # UTC + offset
  modified_at, revision,             # append-only versioning
  source,                            # CHANNEL it entered through (dropper/mobile/claude-hook/…)
  author | provenance_chain,         # WHO contributed (user/agent/mixed)
  context_ref,                       # originating context (session/location/thread)
  tier,                              # persistence/retention
  links: [thread_id | thing_id ...]  # set by ingest, not capture
  ...                                # grows by usage, not pre-spec'd
}
```
*(`source` / `author` / `context_ref` are three independent fields — see "three orthogonal origin dimensions" above. `entity_axis` replaces the former master `kind: thing|event`.)*
**Capture writes the top line cheaply (text + times + author); ingest fills the rest.** That division *is* the friction guarantee.

---

## Compatibility constraint (honored)

The migration must keep the **per-day {text, created-ts} read** alive for `/checkin` / `read_dropper_day.py`. Concretely: either (a) a shim that re-emits a day-slice from the JSONL pool, or (b) keep writing the Excel in parallel during transition. **Decision deferred to the schema §3 stub** (it's a spec detail), but the *constraint* is fixed: **no migration lands that breaks checkin.**

## Operative path (optimized forward sequence — not a rigid critical-path)

1. **JSONL schema** (+ migrate the 852 rows + checkin-compat shim) — unblocks everything.
2. **Mobile shortcut** (wedge) — cheapest writer; starts feeding the new store immediately. `[CONFIRM amb #4: yes, writes the same pool day one]`
3. **Prompt-capture hook** — second writer; captures Claude-session drops + attribution.
4. **Thread extraction / typing / routing** — needs a corpus, so follows capture; the heart of the upper half.
5. **Thread ledger** — derived from extraction output.
6. **App wrapper** (Excel replacement) — **deferred to last**: hardest, and shortcut+hook+existing-Excel cover capture in the interim. Don't rabbit-hole (guardrail).

*Reordering rationale vs the provisional board:* wrapper moved 4→6 (expensive, non-blocking); extraction/ledger pulled up since they're the actual payoff once capture flows.

## Per-part altitude + spec-readiness (the S3 leveling — watched for §4)

| Part | Altitude | Spec-readiness | Note |
|---|---|---|---|
| JSONL schema | scope-shape settled here → **spec-ready** | High (post-§2) | field detail is the one clear §3 spec |
| Mobile shortcut | **spec** | High | small, concrete, one open [CONFIRM] |
| Prompt-capture hook | **spec** | Med-High | `ingestion/claude-sessions/` already exists as a seed |
| Thread extraction/typing/routing | **scope** | Low | genuinely fuzzy; explicit-vs-implicit (E2) unscoped |
| Thread ledger | **scope** | Low | derived-view call pending [CONFIRM amb #5] |
| App wrapper | **scope/spec** | Low | stack undecided (amb #3); deferred |

**Leveling observation (→ §4):** the parts did *not* level uniformly. Capture parts dropped cleanly to **spec**; the schema sits at a genuine **scope-shape vs spec** seam (settled shape here, spec the fields later); the thread parts resisted leveling past **scope**. That spread is the S3 instrument doing its job — and the schema's seam is exactly the altitude-tension the prompt flagged to watch.

---
*Next: §3 — one launch packet per part in `03_spec-stubs/`.*
