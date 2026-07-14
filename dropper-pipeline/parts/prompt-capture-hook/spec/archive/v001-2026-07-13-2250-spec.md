# Prompt-Capture Hook — Specification

> Status: draft
> Revision: 5
> Last updated: 2026-07-13

## Open questions

1. **RESOLVED (2026-06-30).** The `context` shape mismatch is fixed at the source: part-1 `SCHEMA.md` now lists `cwd` in the reserved `claude-hook` context shape, with `kind` / `session_id` / `cwd` as the v1 required keys. The earlier `seq` / `parent_id` placeholders were **dropped** (DEC-008) — both are derivable from `created_at` ordering under a `session_id`, so linkage belongs to the strata layer, not the raw entry. The reserved shape is exactly `{ kind, session_id, cwd }` and the hook writes `{ kind: "claude-session", session_id, cwd }`.

2. **RESOLVED via Claude Code hook docs (2026-06-30).** `UserPromptSubmit` delivers on stdin: `user_prompt` (the prompt text), `session_id`, and `cwd` — mapping directly to the entry's `text`, `context.session_id`, and `context.cwd`. **Caveat:** the text field is `user_prompt` (not `prompt`); on first install the implementer should echo the raw stdin payload once to confirm key names against the running Claude Code version before trusting them (the shipped script accepts both keys). This is a one-time rollout check, not a standing regression guard. **Critical fail-open finding (folded into AC4):** for `UserPromptSubmit`, **exit code 2 BLOCKS and erases the prompt**, and any stdout on an exit-0 run is injected into the conversation as context. So the hook must exit 0 with empty stdout on **both** success and failure — never exit 2, never print to stdout.

3. **RESOLVED by implementation (2026-07-11).** Language = Python; stable path = `dropper-pipeline/parts/prompt-capture-hook/hook/capture_prompt.py` in the collevity-tooling repo (merged, commit 606d1c4).

4. **RESOLVED by implementation (2026-07-11).** The settings.json command sets its whole environment explicitly: interpreter = the part-1 `.venv` python, `PYTHONPATH` = the jsonl-schema part dir (**mandatory** — the venv does not have `collevity` importable), `COLLEVITY_LAKE` = the live lake path. Full snippet + rollout check + rollback: `../INSTALL.md`.

---

## Cross-part dependencies — ALL LANDED (part-1 iteration 2, 2026-07-11, commit 078c698)

> These were required by this spec but owned by **part 1 (jsonl-schema)**. They shipped in part-1 iteration 2; the mechanism lives in part-1's code and decisions, not here (this spec only names what it depended on). DEC-016.

- **D1 — sub-minute `read_day` ordering (DEC-013)** — landed. Same-minute captures now order correctly on read. (This retired the DEC-003 consequence "part 3 requires no change to part 1's `read_day`"; DEC-003's *source-filtering* half still stands — `read_day` does not skip `claude-hook` entries.)
- **D2 — settle-time chronological compaction in `sync_sources` (DEC-012)** — landed. The pool file is chronological after each sync; only the transient live tail (appends since last sync) is arrival-ordered, and read-time sort covers it.
- **D3 — concurrent-append safety (DEC-015)** — landed. All lake mutations serialize on an advisory lock; verified under a multi-process append hammer. Residual accepted risk: iCloud **multi-machine** concurrent use can still produce conflict-copy files — a sync concern, not line corruption (DEC-016).

---

## Goal

Install a global Claude Code `UserPromptSubmit` hook that appends every user prompt to the Collevity live lake via `append_entry` — deterministic, fail-open, no LLM in the path.

## Constraints

- **Fail-open / non-blocking:** a lake-write failure must never delay or block prompt submission; the Claude Code session continues normally regardless of write outcome.
- **Zero field-contract change:** writes only fields already accepted by the live lake (`text`, `created_at`, `source`, `author`, `context`); does not mint `id`; leaves `source_data` unpopulated.
- **Global scope (DEC-005 / DEC-014):** installed in `~/.claude/settings.json` so it fires in every Claude Code session — **including non-Collevity, client, and personal work**. This breadth is a knowingly accepted tradeoff (revisit when the workspace migration completes). Narrowing scope later stops *future* over-capture but does **not** retroactively remove already-captured entries (DEC-014).
- **Canonical `created_at` statement (DEC-011):** the hook stamps `created_at` at capture as ISO-8601 with an explicit local UTC offset **and sub-second (microsecond) precision** (e.g., `2026-06-30T14:05:00.123456-04:00`). Offset *correctness* is inherited from part-1 DEC-017 — owned at capture, neither re-derived nor validated here (the hook validates format, not that the host clock is right). All other sections cross-reference this statement.
- **Chronological order is a read/settle concern, not an append concern (DEC-012):** the hook appends in arrival order and makes **no** attempt to order the lake file; ordering is recovered by read-time sort and settle-time compaction (see Cross-part dependencies — landed).
- **No SDK / LLM call in the path:** the hook is pure plumbing (DEC-001).
- **Accepted risks (owned limitations):**
  - **Capture loss can be traceless (DEC-017):** if the lake write fails *and* the best-effort sidecar breadcrumb also fails, the capture vanishes with zero trace. Fail-open is the prioritized guarantee; observability of loss is best-effort only.
  - **iCloud multi-machine concurrency (DEC-016):** conflict-copy files remain possible if two machines append while offline from each other; single-machine concurrency is locked (D3).
  - **A same-machine stall delays, it does not block (DEC-018):** the hook writes *synchronously*, so a stalled append (iCloud materialization or D3 lock contention) can delay — not fail — submission. The hook adds no internal watchdog (Claude Code's job, not this thin writer — DEC-015); the installed entry's explicit `timeout` (AC1.1) bounds the wait. On timeout Claude Code kills the command; a non-2 exit (incl. signal-kill) is non-blocking, so the prompt proceeds and only that one capture is lost. (Claude Code's docs don't classify a *timeout* explicitly; the small timeout bounds the worst case regardless — its `UserPromptSubmit` default is 30s.)
  - **Torn-write on kill is a low-probability residual (DEC-021):** a timeout-kill could in principle interrupt the single buffered append mid-flush, leaving a partial JSONL line — and part-1's `_read_all` currently *raises* on a corrupt line, so one torn line would break lake reads until repaired. Probability is low (one small buffered write to the local materialization; the triggering stall is usually *pre-write*) and the vector is inherent to any synchronous stall-capable hook — it exists at Claude Code's 30s default too, not created by the chosen timeout. The real hardening (reader tolerance of a bad line and/or crash-safe append) is **part-1's**, deferred (D-001); it does not gate this install.

## Success criteria

- Submit a prompt in any Claude Code session → a matching entry exists in `collevity_lake.jsonl` carrying: `text` = the submitted prompt verbatim, `created_at` per the canonical statement in Constraints, `source: "claude-hook"`, `author: "user"`, `context: { "kind": "claude-session", "session_id": <session id>, "cwd": <working directory> }`.
- Simulate a lake-write failure (point `COLLEVITY_LAKE` at a read-only path) → Claude Code accepts and processes the next prompt without any delay or error surfaced to the session. (A diagnostic sidecar line is expected in this scenario as best-effort behavior — see the AC4 implementation note; it is not a guarantee.)
- Call `read_day` for the submission date → the captured prompt text appears in the result list with the correct local wall-clock time, correctly ordered against same-minute neighbors (D1 — landed).

## Out of scope

- Triage and promotion of entries (DEC-002, DEC-004).
- Contextualize layer — adding LLM-derived context to captured prompts.
- Any SDK or LLM call in the hook path (DEC-001); deferred to a later async layer over the lake.
- `source_data` population (reserved, empty in v1).
- Semantic thread-discrimination (part 4's job; the hook provides raw signal — text, session_id, cwd, timestamp — and part 4 clusters).
- Slash-command skip-lists (skip-filtering is itself triage; DEC-002 held — no denylist in v1).
- Lake-file ordering and concurrent-write safety — part 1's guarantees (landed; see Cross-part dependencies).
- Error-sidecar lifecycle (rotation, reader, monitoring) — best-effort breadcrumb only in v1 (DEC-017).
- Workspace-scoped configuration (DEC-005).

## Acceptance criteria (MECE)

> **Mutual exclusivity:** each AC covers a distinct concern — installation (AC1), payload correctness (AC2), lake persistence (AC3), fail-open behavior (AC4), readability (AC5) — with no overlap between groups.
> **Collective exhaustiveness:** every guarantee-level success criterion above traces to at least one AC leaf; every AC leaf traces back to the goal or a success criterion. (The sidecar breadcrumb is deliberately non-AC — DEC-017.)
> Each leaf is independently testable.

### AC1. Hook is installed and fires on every prompt submission

- AC1.1. `~/.claude/settings.json` contains a `UserPromptSubmit` hook entry with a `command` value pointing to the capture script at a stable absolute path, and carrying an explicit bounded `timeout` — a small number of seconds (installed at 10s), not exceeding Claude Code's 30s `UserPromptSubmit` default — so a stalled write cannot delay submission beyond it (DEC-018). The entry **coexists** with any other `UserPromptSubmit` hooks — installation adds this entry to the event's array, it does not replace existing entries.
- AC1.2. The capture script exists at the referenced path, is executable, and exits 0 on a nominal (successful-write) run.

### AC2. Entry payload is correct on every write

- AC2.1. `text` in the written entry equals the submitted prompt text verbatim (no truncation, no escaping artifacts).
- AC2.2. `created_at` conforms to the canonical statement in Constraints (ISO-8601, explicit local offset, microsecond precision, stamped at capture).
- AC2.3. `source` equals `"claude-hook"`.
- AC2.4. `author` equals `"user"`.
- AC2.5. `context` is a JSON object with `"kind": "claude-session"`, a non-empty `"session_id"` string matching the current Claude Code session, and a non-empty `"cwd"` string matching the session's working directory.
- AC2.6. The written entry carries no `id` field (the store mints it) and no `source_data` field; `context` carries only `kind` / `session_id` / `cwd` (no `seq`, no `parent_id`).

### AC3. Entry is persisted to the live lake

- AC3.1. After a prompt is submitted, `collevity_lake.jsonl` gains **one new JSONL line per hook invocation**; that line is parseable as a valid JSON object that passes the schema's `validate()` call. (Line integrity under concurrent appends is part-1's D3 guarantee — landed — not this AC's test surface. If Claude Code ever fires the hook more than once for a single submission, the result is a duplicate entry — accepted as a low-harm, triage-layer concern per DEC-002 and DEC-010, not a hook defect.)

### AC4. Hook is fail-open / non-blocking

- AC4.1. When the lake write raises any exception (I/O error, validation error, import error, missing env var), the hook swallows it and exits 0 with empty stdout — the prompt is never blocked, delayed, or erased. (Critical: for `UserPromptSubmit`, exit code 2 blocks and erases the prompt; the hook must never exit 2.)
- AC4.2. The hook produces no stdout output during a nominal (successful-write) run that would be interpreted by Claude Code as hook output.

> **Scope note (AC4):** AC4.1 covers exceptions raised *inside* the write path — the failures the hook can catch and swallow. External termination by Claude Code (a `timeout` signal-kill on a stall) is deliberately **out of this test surface**: it is not an in-process exception, so its non-blocking outcome rests on Claude Code's exit-code contract (non-2 → non-blocking, DEC-018) and is confirmed at rollout, not by a unit AC. (Mirrors how AC3.1 scopes concurrent-append line integrity out to part-1's D3.)

> **Implementation note (demoted from AC4.3, DEC-017):** on any swallowed failure the shipped script makes a **best-effort** append of one diagnostic line (`ISO-timestamp — error summary`) to an error sidecar (`hook/capture_errors.log` beside the script; override `COLLEVITY_HOOK_ERRLOG`). Any failure of that append is itself swallowed — AC4.1's exit-0/empty-stdout discipline always wins. This is observability, not a guarantee; the residual (both writes fail → traceless loss) is an accepted risk in Constraints.

### AC5. Captured entries surface via `read_day`

- AC5.1. Calling `read_day(today)` after submitting a prompt returns a list that includes the submitted prompt's `text` at the correct local wall-clock time, bucketed by the local-day-of-offset consistent with the `created_at` offset, ordered correctly against same-minute neighbors (D1 — landed).

## Implementation phases

> Phase 1 is **code-complete** (built in the 2026-07-11 fork, merged at commit 606d1c4, 11/11 subprocess-level tests green) except AC1.1 — installation into `~/.claude/settings.json` is deliberately held for Levi's explicit go (`../INSTALL.md`). Phase 2 exercises the live stack after install; its ordering checks no longer wait on part-1 (D1/D2 landed).

### Phase 1. Script implementation + global installation

**Delivers:** a working hook script, installed in `~/.claude/settings.json`, that captures every user prompt and writes it to the live lake — fail-open on any write error.
**Unblocks:** Phase 2 (end-to-end lake and checkin verification) — foundation.

- AC1.1
- AC1.2
- AC2.1
- AC2.2
- AC2.3
- AC2.4
- AC2.5
- AC2.6
- AC3.1
- AC4.1
- AC4.2

### Phase 2. End-to-end lake and checkin verification

**Delivers:** confirmed via a live prompt submission that the lake entry carries correct fields and `read_day` surfaces it with the right time bucket and order.
**Depends on:** Phase 1 (script implementation + global installation).

- AC5.1
