# Prompt-capture hook — install runbook

**Status (2026-08-01):** LIVE for Claude Code. Shared script also accepts **Grok**
`UserPromptSubmit` envelopes (camelCase). Grok already invokes this install via
Claude-settings hook compatibility (`~/.claude/settings.json`); no second
command is required (a duplicate `~/.grok/hooks` entry would double-capture).

**SessionStart / entry-router:** same Claude settings file runs
`entry-router/catchup.sh` on SessionStart — Grok inherits that too when Claude
hook compat is on. That is the router parity path (#3).

Canonical script:

```
…/dropper-pipeline/parts/prompt-capture-hook/hook/capture_prompt.py
```

## What gets installed

One `UserPromptSubmit` + one `SessionStart` (router catch-up) in
`~/.claude/settings.json` (live).

## settings.json snippet

Merge into `~/.claude/settings.json` (top-level `hooks` key; create if absent).
If a `UserPromptSubmit` array already exists, **append** this hook object to it —
do not replace existing entries (hooks coexist; AC1.1). The command sets its whole
environment explicitly (spec open-Q4): lake path + interpreter, no inherited-env
reliance.

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "COLLEVITY_LAKE='/Users/levi/Library/Mobile Documents/com~apple~CloudDocs/00_COLLEVITY/03_TACTIC/_DATA/collevity_lake.jsonl' PYTHONPATH='/Users/levi/Library/Mobile Documents/com~apple~CloudDocs/00_COLLEVITY/02_CONTENT/collevity-tooling/dropper-pipeline/parts/jsonl-schema' '/Users/levi/Library/Mobile Documents/com~apple~CloudDocs/00_COLLEVITY/02_CONTENT/collevity-tooling/dropper-pipeline/parts/jsonl-schema/.venv/bin/python3' '/Users/levi/Library/Mobile Documents/com~apple~CloudDocs/00_COLLEVITY/02_CONTENT/collevity-tooling/dropper-pipeline/parts/prompt-capture-hook/hook/capture_prompt.py'",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

Notes:
- Interpreter = the jsonl-schema part's `.venv` python (has `uuid6`).
  **`PYTHONPATH` is required** — verified 2026-07-11: the venv does *not* have
  `collevity` installed as a package (the /checkin launcher supplies the path
  itself); without PYTHONPATH the hook fail-opens on ImportError and every
  capture is lost to the sidecar.
- Error sidecar defaults to `hook/capture_errors.log` next to the script;
  override with `COLLEVITY_HOOK_ERRLOG=…` in the same command if preferred.
- **`"timeout": 10`** bounds how long a stalled write can delay prompt submission
  (DEC-018). A normal append is sub-second; this caps a pathological iCloud
  materialization / lock stall at 10s (vs Claude Code's 30s `UserPromptSubmit`
  default). On timeout Claude Code kills the command and — because a non-2 exit
  is non-blocking — the prompt **still goes through**; only that one capture is
  dropped to the breadcrumb. Fail-open holds. Tune the value if 10s ever proves
  too tight for a legitimately-slow-but-succeeding write.

## One-time rollout check (spec open-Q2 — do this on first install)

1. Temporarily point the command at a copy of the script with this line added
   at the top of `_capture()` (or just trust the tolerant reader — the script
   already accepts both `prompt` and `user_prompt`):
   `Path('/tmp/hook_payload_echo.json').write_text(sys.stdin.read())` *(then
   restore; remember stdin can only be read once)*.
2. Submit one throwaway prompt; confirm the payload's key names.
3. Restore the real script. Confirm the throwaway prompt landed in the lake:
   `tail -1 …/collevity_lake.jsonl`.
4. **Single-fire check** (contrarian review 2026-07-13): the throwaway submission
   should add exactly **one** new lake line, not two — confirming Claude Code does
   not double-fire `UserPromptSubmit` on this version. If two appear, it's tolerated
   triage debt (DEC-010), not a hook defect — but note it.

## Post-install / post-upgrade verification (manual — you own this gate)

Do after Claude Code or Grok CLI upgrades, or when capture feels silent.

1. **Claude:** submit a throwaway prompt → `tail -1` lake → expect
   `source: claude-hook`, verbatim text, offset `created_at`, context session_id+cwd.
2. **Grok:** submit a throwaway prompt → `tail -1` lake → expect
   `source: grok-hook` (same script; camelCase envelope).
3. **Sidecar:**
   `…/prompt-capture-hook/hook/capture_errors.log` — no new error lines for those submits.
4. **Day read:** `python3 ~/.claude/skills/checkin/read_lake_day.py` (today) shows them.
5. **Router:** `entry-router/catchup.log` gains a SessionStart/catch-up line after a
   new session (Claude or Grok); or run `…/entry-router/catchup.sh` by hand once.

Fail-open drill (optional): point `COLLEVITY_LAKE` at a read-only path, submit →
prompt still goes through; sidecar gains one line; restore path.

## Breakage (capture-health)

Silent fail-open is by design. Standing thread **`capture-health`**: soft probes
(checkin), sidecar skim, upgrade verify. Do not rely on prompts blocking.

## Rollback

Delete the `UserPromptSubmit` entry from `~/.claude/settings.json`. Capture
stops immediately; nothing else to undo (already-captured entries stay, DEC-014).

## Known accepted tradeoffs (from the spec)

- **Global scope** — fires in every session incl. client/personal work
  (DEC-005/014, Levi-ratified). Not retroactively reversible.
- Duplicate fires (if Claude Code ever double-fires) are triage's problem
  (DEC-010), not the hook's.
- iCloud file eviction of the script would mean lost captures + breadcrumbs,
  never blocked prompts.
- **Torn-write on timeout-kill** (DEC-021) — if a stall trips the `timeout` and
  Claude Code SIGKILLs the hook mid-append, a partial JSONL line is *possible*
  (low probability). Because part-1's reader currently raises on a corrupt line,
  that would break lake reads until the bad line is removed. The real fix (reader
  tolerance / crash-safe append) is part-1's, deferred as D-001; not gating this
  install. On a timeout the prompt still submits.
