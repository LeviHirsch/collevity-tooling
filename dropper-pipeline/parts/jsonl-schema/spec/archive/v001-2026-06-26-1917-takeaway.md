# Collevity Entry Store (JSONL Schema) — Takeaway: iteration 1

> Source spec: `../archive/v001-2026-06-26-1917-spec.md` (converged 2026-06-24 at SHA `7c57537`, DEC-020)
> Implementation verified: 2026-06-26 (report: `archive/v001-2026-06-26-1740-verify.md`)
> Verdict: PASS (no accepted gaps — all 28 AC nodes PASS; 39 tests; live migration ran)

## Shipped state `[from-code]`

The keystone store the rest of the Dropper Pipeline reads from and writes to. Append-dominant JSONL pool, Excel-blind core, with the Excel bridge as the sole (temporary) pull ingester.

**Core (Phase 1, Excel-blind):**
- `collevity/lake/schema.py` — the executable field contract: required floor `{id, text, created_at, source, author}` (AC1.1), `created_at` ISO-8601 + explicit-offset enforced (`_check_created_at`, AC1.3), `author=="user"` / non-empty `source` (AC1.4), four absent-when-unused optionals `{context, tags, meta_notes, source_data}` type-checked only when present (AC1.5–1.7), and a **closed top level** that rejects the strata-era exclusions + any unknown key with a pointer to `source_data` (`_EXCLUDED_HINT`, AC1.8).
- `collevity/lake/lake.py` — the storage seam, the only documented access path (AC2.3): `append_entry` mints the canonical UUIDv7 id and rejects caller-supplied ids (AC1.2/AC2.1); `edit_entry` rewrites in place by id with no lineage/history/modified-bump (AC2.2/DEC-006); `read_day` is a pure retrieval returning `[{text, time}]` bucketed by **local-day-of-offset** (AC3.1/AC3.2); `sync_sources` is the pull-ingest boundary with no multi-source registry (AC5.1/AC5.2). Raw JSONL i/o (`_read_all`/`_append_line`/`_rewrite_all`, atomic temp+replace) is private.
- `SCHEMA.md` — the prose contract `schema.py` mirrors (reserved `claude-session` context shape, meta_notes append-only convention, explicit exclusions).
- id minting via `uuid6.uuid7()` (DEC-021) — returns a stdlib `uuid.UUID` that drops natively into a future Postgres `uuid` column.

**Excel bridge (Phase 2, deletable scaffolding):**
- `collevity/lake/bridges/excel.py` — reads **only** cols D (text) and E (drop-timestamp), never col F `modified` (AC4.1); `excel-ingest-state.json` sidecar keys each row by `created_at` ISO string with a `#rowindex` tiebreaker → JSONL id + last-ingested text snapshot (AC4.2); the whole row set is read + key-validated up front so a bad timestamp **fails loud with no partial ingest** (AC4.2); per-run snapshot reconciliation new→append / changed→edit / unchanged→skip (AC4.3); registered as the **single** v1 ingester via one explicit lazy import in `sync_sources`, idempotent within a session, no daemon/cron (AC4.6/AC5.2).
- `collevity/lake/bridges/backfill_mdt_tz.py` — **one-shot, disposable** tz backfill: bridge stamps everything EDT (`-04:00`); this script rewrites exactly the Colorado-round-trip window `[2026-06-15 00:00, 2026-06-17 15:00)` to `-06:00` through the seam, idempotently (AC4.4). To be deleted post-close.
- `collevity/lake/bridges/__init__.py` — deleting the subpackage reverts `sync_sources` to its Phase-1 no-op via the `ImportError` guard, leaving core JSONL + `read_day` untouched (AC4.5, Excel-blind clean-delete).

**Live state (outside the repo, DEC-022):** the real migration ran against `00_COLLEVITY/03_TACTIC/_DATA/collevity_lake.jsonl` — **940 entries, all schema-valid, 933 EDT / 7 MDT**, with `excel-ingest-state.json` beside it. Lake + sidecar are intentionally not committed.

**Tests:** `tests/test_phase1.py` (24, AC-traced) + `tests/test_phase2.py` (15) = 39 passing, isolated from the live lake via `tests/conftest.py`.

## Deviations from spec

### Accepted gaps
None. All ACs PASS.

### Other deviations
- **Module layout restructured mid-iteration.** Phase 1 originally shipped as an `entry_store/` package (`ids.py`/`schema.py`/`store.py`/`sync.py`); commit `676cbc9` collapsed it to the `collevity/lake/` namespace (`lake.py` + `schema.py`) before Phase 2. Behavior unchanged — the 24 Phase-1 tests still pass — but the Phase-1 audit's file refs are stale against current code (re-anchored in the verify report). Not spec-dictated; conventional cleanup.
- **`read_day` returns un-stripped text and a Python list of dicts**, whereas the legacy `read_dropper_day.py` `.strip()`s and prints `[HH:MM] text` stdout lines. Within DEC-013's "format = {text, time}" framing this is consumer-side rendering, not a data-shape deviation — flagged only if a future `/checkin` adapter needs byte-identical stdout (it consumes data, not bytes).

## Discoveries during implementation

- **Open Question 1 resolved as a round-trip, not a move (DEC-024).** The text+timestamp classification pass (DEC-023) over the live Dropper showed the MDT rows are a **7-row mid-June Colorado wedding trip** (Jun 15 08:42 → Jun 17 14:49), not a permanent Mountain→Eastern relocation. Levi's own in-entry tz notes ("the timestamps for 6/15-17 here … are MDT"; "got home … now EDT") pinned the window exactly and bracketed it cleanly (no drops in the travel gaps). The "MDT minority" spec wording is confirmed (7 of 940).
- **Row-count drift is real and not worth chasing.** Success-criterion (c)'s "852 rows" drifted 852→935→940 across the build; reconcile dropped the hard count from the spec rather than keep updating a point-in-time number. Lesson for the seed-template: don't bake live-data counts into acceptance criteria.
- **`read_dropper_day.py` lives in the `/checkin` skill folder, outside this repo** (`~/.claude/skills/checkin/read_dropper_day.py`) — which is why Phase 1 flagged the HH:MM time shape as unconfirmable. It emits time via `dt.strftime('%H:%M')`, so the assumed shape was correct; parity is now confirmed and the `read_day` docstring records it. The cross-repo dependency is worth keeping in mind for the cutover work.
- **The lazy-import + ImportError pattern made AC4.5 (clean-delete) trivially true** — deleting `bridges/` is a zero-edit retire, verified by a test that monkeypatches the bridge to `None`. This is the architectural payoff of DEC-018 moving ingest out of `read_day` into `sync_sources`.

## Key decisions (this iteration)

See `../decisions.log` under the `# Iteration 1` header (DEC-001 … DEC-024). Load-bearing ones:

- **DEC-014** — `created_at` = ISO-8601 + explicit offset, no `tz` field; tz mis-bucketing fixed at the root.
- **DEC-018** — `sync_sources` is the pull-ingest seam; `read_day` is a pure read (superseded DEC-015's read-time piggyback). The decision that made clean-delete and idempotent reads fall out for free.
- **DEC-011** — Excel-blind core: all Excel quirks confined to a throwaway bridge + sidecar with snapshot reconciliation; `modified` never read.
- **DEC-024** — Open Question 1 resolved (Colorado round-trip, 7 MDT rows); enabled the one-shot backfill to be auditable and bounded.
- **DEC-022** — live lake at `03_TACTIC/_DATA/collevity_lake.jsonl` (iCloud-backed, outside the exportable code tree).

## Open for next iteration

- **Delete the spent `bridges/backfill_mdt_tz.py`** — the one-shot has run against the live lake; the AC4.4 audit needed it present, but it is now post-iteration cleanup.
- **Repoint `/checkin` & `read_dropper_day.py` at the JSONL lake** (swap guts xlsm→JSONL, keep CLI/output) — op-path/consumer work, explicitly out of this part's scope (DEC-013). Mind the cross-repo location.
- **Retire Excel** — delete `bridges/` once a native computer-capture surface exists (the clean-delete path is already proven).
- **Deferred (carried, not regressions):** Excel-row deletion detection (DEC-011, single-user, revisit only if it bites); offline-first surface-local id reconciliation (DEC-010 — `sync_sources` names its future home); read-side `source` filter for hook go-live (DEC-013); strata-era field promotions `occurred_at`/`planned_for`/`horizon` (DEC-014).
