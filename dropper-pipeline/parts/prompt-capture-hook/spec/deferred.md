# Deferred items

_Backlog of feature requests, bug reports, and ideas not yet committed to any iteration. Triaged at each iteration's interview._

## D-001 — Part-1: crash-safe lake read/append (tolerate a torn JSONL line)
- First seen: 2026-07-13 (iteration 1, via /spec revise during review v001-2026-07-13-1827)
- Last touched: 2026-07-13 (iteration 1)
- Defer count: 0
- Category: refactor
- Description: `_read_all` (lake.py) raises `ValueError` on any corrupt/torn JSONL line, so a single bad line breaks every lake read (read_day / sync / edit) until manually repaired. Harden part-1 so the reader tolerates a bad line (skip-and-warn) and/or the append is crash-safe (fsync or atomic-tmp), so a writer killed mid-append can never brick reads.
- Notes: Surfaced by the prompt-capture-hook review (torn-write-on-timeout-kill residual, DEC-021). This is part-1 (jsonl-schema) territory — the hook is a thin writer over `append_entry` (DEC-015 layer logic), so it can't and shouldn't fix reader/writer crash-safety itself. Candidate part-1 iteration-3 AC (alongside the id-bearing-read gap the computer-dropper spike found). Low probability, high blast radius — worth doing before the lake grows.

## D-002 — Hook authorship integrity: `author:user` is stamped blindly on all UserPromptSubmit captures
- First seen: 2026-07-13 (iteration 1, via Levi post-install consideration)
- Last touched: 2026-07-13 (iteration 1)
- Defer count: 0
- Category: feature (hook iteration 2)
- Description: The hook hardcodes `author: "user"` on every capture, but `UserPromptSubmit` fires for non-human submissions too, so the label is an unverifiable claim. Uphold the "user-written context only" intent by distinguishing genuine user authorship from AI/programmatic submissions.
- Notes: **Verified fact pattern (2026-07-13):** interactive human session → captured correctly; **Task-tool sub-agents (spawned within a session) → do NOT fire the hook (safe)**; headless `claude -p` → fires and stamps `author:user` regardless of launcher (proven: the HOOK-ROLLOUT-TEST entry, an AI-launched session); Agent SDK `query()` → **undocumented, possibly fires (untested — test against the account-switcher SDK harness)**; AI-drafted text a human pastes+sends → fires as `author:user`, hook cannot detect it's AI-drafted. Docs: the payload (session_id/prompt_id/transcript_path/cwd/permission_mode/hook_event_name) has **no field distinguishing human vs programmatic**, so the hook can't self-detect. **Two structurally-distinct problems: (P2) programmatic/agent SESSIONS** — solvable cheaply & low-burden via an env var the *launcher* sets: hook reads `COLLEVITY_HOOK_AUTHOR` (default `user`) and/or `COLLEVITY_HOOK_SKIP`; burden falls on the few automation entry points, not every prompt (hooks inherit the launching process env, and the settings.json command doesn't set these, so a launcher-set value passes through). **(P1) AI-drafted text submitted in a human session** — irreducible at capture; either a creation-time marker attached by the ~few prompt-generating tools, or (preferred) defer authorship-refinement to the future triage/contextualize layer (aligns with DEC-002/004: typing/promotion live downstream of the raw entry). Interim risk is bounded (sub-agents safe; only top-level programmatic sessions leak; low volume today). Candidate = **hook iteration 2** (+ maybe a part-1 `author` vocabulary decision: user/agent/unknown).
