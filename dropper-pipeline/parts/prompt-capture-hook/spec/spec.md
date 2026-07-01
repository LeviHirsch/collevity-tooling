# Prompt-Capture Hook — Specification

> Status: draft
> Revision: 2
> Last updated: 2026-06-30

## Open questions

1. **RESOLVED (2026-06-30).** The `context` shape mismatch is fixed at the source: part-1 `SCHEMA.md` now lists `cwd` in the reserved `claude-hook` context shape, with `kind` / `session_id` / `cwd` as the v1 required keys. The earlier `seq` / `parent_id` placeholders were **dropped** (DEC-008) — both are derivable from `created_at` ordering under a `session_id`, so linkage belongs to the strata layer, not the raw entry. The reserved shape is exactly `{ kind, session_id, cwd }` and the hook writes `{ kind: "claude-session", session_id, cwd }`.

2. **RESOLVED via Claude Code hook docs (2026-06-30).** `UserPromptSubmit` delivers on stdin: `user_prompt` (the prompt text), `session_id`, and `cwd` — mapping directly to the entry's `text`, `context.session_id`, and `context.cwd`. **Caveat:** the text field is `user_prompt` (not `prompt`); on first install the implementer should echo the raw stdin payload once to confirm key names against the running Claude Code version before trusting them. This is a one-time rollout check, not a standing regression guard. **Critical fail-open finding (folded into AC4):** for `UserPromptSubmit`, **exit code 2 BLOCKS and erases the prompt**, and any stdout on an exit-0 run is injected into the conversation as context. So the hook must exit 0 with empty stdout on **both** success and failure — never exit 2, never print to stdout.

3. **Hook script language and stable path.** The interview did not specify Python vs shell, or where the script lives (inside collevity-tooling repo, `~/.claude/bin/`, etc.). The implementer decides; the script must be at a stable absolute path since `~/.claude/settings.json` references it by path.

4. **`collevity` package resolution + `COLLEVITY_LAKE` for the hook process.** The hook script calls `append_entry` from the `collevity` package. Installation must specify how the hook process finds the package (virtualenv / system-Python / `PYTHONPATH`) and how `COLLEVITY_LAKE` is set to the live lake path (`03_TACTIC/_DATA/collevity_lake.jsonl`). These are not configured by the spec — flag for the implementation step.

---

## Cross-part dependencies (on a new part-1 / jsonl-schema iteration)

> These are required by this spec but implemented in **part 1 (jsonl-schema)**, whose iteration 1 is closed. They are **dependencies, not hook ACs** — the hook does not implement them. But AC5.1's fine-grained ordering and the chronological-order constraint below cannot be fully satisfied until part 1 ships them in a follow-on iteration. Sequencing: the hook (Phase 1) can be built and installed independently; full Phase-2 verification of ordering waits on D1/D2.

- **D1 — `read_day` sort/display precision (DEC-013).** `read_day` currently buckets by local-day and sorts the returned rows by an `HH:MM` string (`lake.py`), so it cannot order two entries inside the same minute. Part 1 must raise `read_day`'s sort (and surfaced-time) resolution to sub-minute so the fine-grained `created_at` this hook stamps is actually ordered on read. **Supersedes the DEC-003 consequence** "part 3 requires no change to part 1's `read_day`": the *source-filtering* half of DEC-003 still stands (read_day is **not** modified to skip `claude-hook` entries); only the "no change at all" claim is retired.

- **D2 — settle-time chronological compaction in `sync_sources` (DEC-012).** Live hook writes append to the end of the lake (fast, arrival-order); the Excel bridge batch-appends older-timestamped rows on sync. So the physical file is not chronological between syncs. Part 1's `sync_sources` must, on settle, rewrite the lake sorted by `created_at` (reusing the existing atomic `_rewrite_all`). After a sync the file is chronological; only the transient live tail (appends since the last sync) is unsorted.

- **D3 — concurrent-append safety of `append_entry` (DEC-015).** Global scope makes concurrent Claude sessions realistic; two hook processes can append to the same lake file at once. `append_entry` currently does a plain `open("a")` + single `write()` with no lock (`lake.py`); single small appends are effectively atomic on local disk, but the lake lives in iCloud (DEC-022) where that guarantee weakens. Part 1 must confirm — and if needed harden (advisory lock) — append safety under concurrent writers. The hook does not own this fix; it only depends on the guarantee.

---

## Goal

Install a global Claude Code `UserPromptSubmit` hook that appends every user prompt to the Collevity live lake via `append_entry` — deterministic, fail-open, no LLM in the path.

## Constraints

- **Fail-open / non-blocking:** a lake-write failure must never delay or block prompt submission; the Claude Code session continues normally regardless of write outcome.
- **Zero field-contract change:** writes only fields already accepted by the live lake (`text`, `created_at`, `source`, `author`, `context`); does not mint `id`; leaves `source_data` unpopulated.
- **Global scope (DEC-005 / DEC-014):** installed in `~/.claude/settings.json` so it fires in every Claude Code session — **including non-Collevity, client, and personal work**. This breadth is a knowingly accepted tradeoff (revisit when the workspace migration completes). Note: narrowing scope later stops *future* over-capture but does **not** retroactively remove already-captured entries — the earlier "reversible and lossless" framing of DEC-005 was corrected on this point (DEC-014).
- **Local-offset, high-precision `created_at` (DEC-011):** the hook stamps `created_at` at capture with the correct local UTC offset **and sub-second (microsecond) precision**. Offset *correctness* is inherited from part-1 DEC-017 — owned at capture, neither re-derived nor validated here (the hook validates format, not that the host clock is right).
- **Chronological order is a read/settle concern, not an append concern (DEC-012):** the hook appends in arrival order and makes **no** attempt to order the lake file. `created_at` (ISO-8601 with offset, lexicographically sortable — part-1 DEC-014) is the chronological source of truth; chronological order is recovered by read-time sort (`read_day`) and by settle-time compaction (dependency D2). The hook's only ordering duty is stamping an accurate, high-precision `created_at`.
- **No SDK / LLM call in the path:** the hook is pure plumbing (DEC-001).

## Success criteria

- Submit a prompt in any Claude Code session → a matching entry exists in `collevity_lake.jsonl` carrying: `text` = the submitted prompt verbatim, `created_at` = ISO-8601 with the correct local UTC offset **and sub-second precision** stamped at capture, `source: "claude-hook"`, `author: "user"`, `context: { "kind": "claude-session", "session_id": <session id>, "cwd": <working directory> }`.
- Simulate a lake-write failure (point `COLLEVITY_LAKE` at a read-only path) → Claude Code accepts and processes the next prompt without any delay or error surfaced to the session, **and a diagnostic line recording the failure appears in the error sidecar**.
- Call `read_day` for the submission date → the captured prompt text appears in the result list with the correct local wall-clock time. (Ordering two same-minute captures relative to each other depends on part-1 dependency D1.)

## Out of scope

- Triage and promotion of entries (DEC-002, DEC-004).
- Contextualize layer — adding LLM-derived context to captured prompts.
- Any SDK or LLM call in the hook path (DEC-001); deferred to a later async layer over the lake.
- `source_data` population (reserved, empty in v1).
- Semantic thread-discrimination (part 4's job; the hook provides raw signal — text, session_id, cwd, timestamp — and part 4 clusters).
- Slash-command skip-lists (skip-filtering is itself triage; DEC-002 held — no denylist in v1).
- **Implementing the part-1 changes D1–D3** — they are dependencies (tracked above), not hook work. In particular the hook does **not** re-sort the lake file on append (that is settle-time compaction, D2).
- Workspace-scoped configuration (DEC-005).

## Acceptance criteria (MECE)

> **Mutual exclusivity:** each AC covers a distinct concern — installation (AC1), payload correctness (AC2), lake persistence (AC3), fail-open behavior (AC4), readability (AC5) — with no overlap between groups.
> **Collective exhaustiveness:** every success criterion above traces to at least one AC leaf; every AC leaf traces back to the goal or a success criterion.
> Each leaf is independently testable.

### AC1. Hook is installed and fires on every prompt submission

- AC1.1. `~/.claude/settings.json` contains a `UserPromptSubmit` hook entry with a `command` value pointing to the capture script at a stable absolute path.
- AC1.2. The capture script exists at the referenced path, is executable, and exits 0 on a nominal (successful-write) run.

### AC2. Entry payload is correct on every write

- AC2.1. `text` in the written entry equals the submitted prompt text verbatim (no truncation, no escaping artifacts).
- AC2.2. `created_at` is an ISO-8601 string with an explicit UTC offset **and sub-second (microsecond) precision** (e.g., `2026-06-30T14:05:00.123456-04:00`), stamped by the hook at the moment of capture, with the offset matching the host's current local offset. (Offset *correctness* is inherited from part-1 DEC-017, not validated here — see DEC-011.)
- AC2.3. `source` equals `"claude-hook"`.
- AC2.4. `author` equals `"user"`.
- AC2.5. `context` is a JSON object with `"kind": "claude-session"`, a non-empty `"session_id"` string matching the current Claude Code session, and a non-empty `"cwd"` string matching the session's working directory.
- AC2.6. The written entry carries no `id` field (the store mints it) and no `source_data` field; `context` carries only `kind` / `session_id` / `cwd` (no `seq`, no `parent_id`).

### AC3. Entry is persisted to the live lake

- AC3.1. After a prompt is submitted, `collevity_lake.jsonl` gains **one new JSONL line per hook invocation**; that line is parseable as a valid JSON object that passes the schema's `validate()` call. (If Claude Code ever fires the hook more than once for a single submission, the result is a duplicate entry — accepted as a low-harm, triage-layer concern per DEC-002 and DEC-010, not a hook defect. The hook writes one line per invocation; it does not — and cannot — police Claude Code's fire count.)

### AC4. Hook is fail-open / non-blocking

- AC4.1. When the lake write raises any exception (I/O error, validation error, import error, missing env var), the hook swallows it and exits 0 with empty stdout — the prompt is never blocked, delayed, or erased. (Critical: for `UserPromptSubmit`, exit code 2 blocks and erases the prompt; the hook must never exit 2.)
- AC4.2. The hook produces no stdout output during a nominal (successful-write) run that would be interpreted by Claude Code as hook output.
- AC4.3. On any swallowed failure (per AC4.1), the hook makes a **best-effort** append of a single diagnostic line (`ISO-timestamp — error summary`) to an error sidecar file at a stable path. Any failure of that sidecar append is **itself swallowed** — the hook still exits 0 with empty stdout and never blocks. The sidecar is the only breadcrumb that a capture was lost, so silent discard becomes discoverable (DEC-009).

### AC5. Captured entries surface via `read_day`

- AC5.1. Calling `read_day(today)` after submitting a prompt returns a list that includes the submitted prompt's `text` at the correct local wall-clock time, bucketed by the local-day-of-offset consistent with the `created_at` offset. (Ordering two same-minute captures relative to each other depends on part-1 dependency D1 — see Cross-part dependencies.)

## Implementation phases

> Phase 1 can be built to completion with no work from Phase 2 and no dependence on the part-1 changes D1–D3. Phase 2 exercises the live stack; its ordering checks (AC5.1 sub-minute) additionally depend on part-1 dependency D1 landing.

### Phase 1. Script implementation + global installation

**Delivers:** a working hook script, installed in `~/.claude/settings.json`, that captures every user prompt and writes it to the live lake — fail-open on any write error, with a best-effort error sidecar breadcrumb.
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
- AC4.3

### Phase 2. End-to-end lake and checkin verification

**Delivers:** confirmed via a live prompt submission that the lake entry carries correct fields and `read_day` surfaces it with the right time bucket.
**Depends on:** Phase 1 (script implementation + global installation). Sub-minute ordering within AC5.1 additionally depends on part-1 dependency D1.

- AC5.1

## Open questions

(See top of document. Cross-part dependencies on part 1 are tracked in their own section.)
