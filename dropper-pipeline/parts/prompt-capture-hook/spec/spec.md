# Prompt-Capture Hook — Specification

> Status: draft
> Revision: 1
> Last updated: 2026-06-30

## Open questions

1. **RESOLVED (2026-06-30).** The `context` shape mismatch is fixed at the source: part-1 `SCHEMA.md` now lists `cwd` in the reserved `claude-hook` context shape, with `kind` / `session_id` / `cwd` as the v1 required keys. The earlier `seq` / `parent_id` placeholders were **dropped** (DEC-008) — both are derivable from `created_at` ordering under a `session_id`, so linkage belongs to the strata layer, not the raw entry. The reserved shape is exactly `{ kind, session_id, cwd }` and the hook writes `{ kind: "claude-session", session_id, cwd }`.

2. **RESOLVED via Claude Code hook docs (2026-06-30).** `UserPromptSubmit` delivers on stdin: `user_prompt` (the prompt text), `session_id`, and `cwd` — mapping directly to the entry's `text`, `context.session_id`, and `context.cwd`. **Caveat:** the text field is `user_prompt` (not `prompt`); on first install the implementer should echo the raw stdin payload once to confirm key names against the running Claude Code version before trusting them. **Critical fail-open finding (folded into AC4):** for `UserPromptSubmit`, **exit code 2 BLOCKS and erases the prompt**, and any stdout on an exit-0 run is injected into the conversation as context. So the hook must exit 0 with empty stdout on **both** success and failure — never exit 2, never print to stdout.

3. **Hook script language and stable path.** The interview did not specify Python vs shell, or where the script lives (inside collevity-tooling repo, `~/.claude/bin/`, etc.). The implementer decides; the script must be at a stable absolute path since `~/.claude/settings.json` references it by path.

4. **`collevity` package resolution + `COLLEVITY_LAKE` for the hook process.** The hook script calls `append_entry` from the `collevity` package. Installation must specify how the hook process finds the package (virtualenv / system-Python / `PYTHONPATH`) and how `COLLEVITY_LAKE` is set to the live lake path (`03_TACTIC/_DATA/collevity_lake.jsonl`). These are not configured by the spec — flag for the implementation step.

---

## Goal

Install a global Claude Code `UserPromptSubmit` hook that appends every user prompt to the Collevity live lake via `append_entry` — deterministic, fail-open, no LLM in the path.

## Constraints

- **Fail-open / non-blocking:** a lake-write failure must never delay or block prompt submission; the Claude Code session continues normally regardless of write outcome.
- **Zero field-contract change:** writes only fields already accepted by the live lake (`text`, `created_at`, `source`, `author`, `context`); does not mint `id`; leaves `source_data` unpopulated.
- **Global scope:** installed in `~/.claude/settings.json` so it fires in every Claude Code session (DEC-005).
- **Local-offset `created_at`:** the hook owns offset-correctness — stamps the correct local UTC offset at capture time; the store neither re-derives nor validates it (DEC-017 from part 1).
- **No SDK / LLM call in the path:** the hook is pure plumbing (DEC-001).

## Success criteria

- Submit a prompt in any Claude Code session → a matching entry exists in `collevity_lake.jsonl` carrying: `text` = the submitted prompt verbatim, `created_at` = ISO-8601 with the correct local UTC offset stamped at capture, `source: "claude-hook"`, `author: "user"`, `context: { "kind": "claude-session", "session_id": <session id>, "cwd": <working directory> }`.
- Simulate a lake-write failure (point `COLLEVITY_LAKE` at a read-only path) → Claude Code accepts and processes the next prompt without any delay or error surfaced to the session.
- Call `read_day` for the submission date → the captured prompt text appears in the result list with the correct local wall-clock time.

## Out of scope

- Triage and promotion of entries (DEC-002, DEC-004).
- Contextualize layer — adding LLM-derived context to captured prompts.
- Any SDK or LLM call in the hook path (DEC-001); deferred to a later async layer over the lake.
- `source_data` population (reserved, empty in v1).
- Semantic thread-discrimination (part 4's job; the hook provides raw signal — text, session_id, cwd, timestamp — and part 4 clusters).
- Slash-command skip-lists (skip-filtering is itself triage; deferred).
- Any changes to part 1's `read_day` (DEC-003).
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
- AC2.2. `created_at` is an ISO-8601 string with an explicit UTC offset (e.g., `2026-06-30T14:05:00-04:00`), stamped by the hook at the moment of capture, with the offset matching the host's current local offset.
- AC2.3. `source` equals `"claude-hook"`.
- AC2.4. `author` equals `"user"`.
- AC2.5. `context` is a JSON object with `"kind": "claude-session"`, a non-empty `"session_id"` string matching the current Claude Code session, and a non-empty `"cwd"` string matching the session's working directory.
- AC2.6. The written entry carries no `id` field (the store mints it) and no `source_data` field; `context` carries only `kind` / `session_id` / `cwd` (no `seq`, no `parent_id`).

### AC3. Entry is persisted to the live lake

- AC3.1. After a prompt is submitted, `collevity_lake.jsonl` gains exactly one new JSONL line per prompt; that line is parseable as a valid JSON object that passes the schema's `validate()` call.

### AC4. Hook is fail-open / non-blocking

- AC4.1. When the lake write raises any exception (I/O error, validation error, import error, missing env var), the hook swallows it and exits 0 with empty stdout — the prompt is never blocked, delayed, or erased. (Critical: for `UserPromptSubmit`, exit code 2 blocks and erases the prompt; the hook must never exit 2.)
- AC4.2. The hook produces no stdout output during a nominal (successful-write) run that would be interpreted by Claude Code as hook output.

### AC5. Captured entries surface via `read_day`

- AC5.1. Calling `read_day(today)` after submitting a prompt returns a list that includes `{"text": <prompt text>, "time": <HH:MM matching the captured local wall-clock time>}`, bucketed by the local-day-of-offset consistent with the `created_at` offset.

## Implementation phases

> Phase 1 can be built to completion with no work from Phase 2. Phase 2 exercises the live stack and needs a working installation to run against.

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

**Delivers:** confirmed via a live prompt submission that the lake entry carries correct fields and `read_day` surfaces it with the right time bucket.
**Depends on:** Phase 1 (script implementation + global installation)

- AC5.1

## Open questions

(See top of document.)
