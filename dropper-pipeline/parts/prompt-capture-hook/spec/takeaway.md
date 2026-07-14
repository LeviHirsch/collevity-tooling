# Prompt-Capture Hook — Takeaway: iteration 1

> Source spec: `../archive/` Rev 5 (converged 2026-07-13 at SHA `df51ed6`)
> Implementation verified: 2026-07-13 (report: `archive/v001-2026-07-13-2246-verify.md`)
> Verdict: PASS (12/12 leaf ACs, zero gaps)

## Shipped state `[from-code]`

- `hook/capture_prompt.py` — the `UserPromptSubmit` capture script. Pure plumbing: reads the hook payload from stdin, builds an entry (`text`, µs-offset `created_at`, `source:"claude-hook"`, `author:"user"`, `context:{kind,session_id,cwd}`), and appends via the part-1 seam `append_entry`. **Fail-open by contract:** every path returns exit 0 with empty stdout (`:89-94`); a swallowed failure best-efforts one breadcrumb line to `capture_errors.log` (`:47-54`). Tolerant reader accepts both `prompt` and `user_prompt` keys (`:60`).
- `~/.claude/settings.json` — global `UserPromptSubmit` hook entry (installed live 2026-07-13): `type:command`, explicit `timeout:10`, env set inline (`COLLEVITY_LAKE`, `PYTHONPATH` → jsonl-schema part, `.venv` python). Clean add — no prior `hooks` key.
- `INSTALL.md` — install runbook: snippet, PYTHONPATH rationale, one-time payload-key rollout check, single-fire check, fail-open drill, rollback, accepted tradeoffs (incl. torn-write residual).
- `tests/test_hook.py` — 11 subprocess-level tests, all green.
- Capture is **live and global** as of 2026-07-13.

## Deviations from spec

### Accepted gaps
None. All 12 leaf ACs PASS with both code reference and live end-to-end evidence.

### Other deviations
- AC1.1 (installation) was deliberately **held** through the spec loop for Levi's explicit go, then completed live this session — the spec always intended this gating, so it's an intended sequence, not a deviation.

## Discoveries during implementation

- **"Never delay" was untested against a *stall*** (the hook runs synchronously from Claude Code's view). Closed with an explicit `timeout:10`; verified via docs that a non-2 exit / timeout signal-kill is non-blocking so the prompt still submits (DEC-018).
- **The timeout fix has a torn-write residual** — a SIGKILL mid-append could tear a JSONL line, and part-1's `_read_all` *raises* on a corrupt line (whole-file read break). Low probability; the real fix (reader tolerance / crash-safe append) is part-1's, deferred as **D-001** (DEC-021). Not gating.
- **`author:"user"` is stamped blindly and is unverifiable.** Empirically (CLI 2.1.208, claude-agent-sdk 0.2.117): Task-tool sub-agents do NOT fire the hook (verified post-install); `claude -p` fires as user; **the Agent SDK `query()` fires the hook even at `setting_sources=None` default** — only `setting_sources=[]` is hermetic. So SDK/programmatic sessions pollute the lake as `author:user`. Material for the account-switcher roadmap. Captured as **D-002** (hook iteration 2 candidate).
- Settings.json **hot-loads** — the hook fired same-session without a restart.
- Global scope means the lake captures across all concurrent sessions (observed live).

## Key decisions (this iteration)

See `../decisions.log` under `# Iteration 1` (DEC-001..022). Load-bearing:

- **DEC-018** — a same-machine stall bounds delay (not blocks); explicit hook `timeout`, no in-hook watchdog (wrong layer).
- **DEC-021** — torn-write-on-kill accepted as low-probability; reader/append hardening deferred to part-1 (D-001).
- **DEC-017** — error sidecar demoted from AC to owned limitation (best-effort ≠ testable guarantee).
- **DEC-019** — live hook chosen over Claude Code transcript-mining (unified lake substrate).
- **DEC-022** — converged at `df51ed6` by human judgment on a clean 3-persona pass.

## Open for next iteration

- **D-002 — hook iteration 2: authorship integrity.** Add `COLLEVITY_HOOK_SKIP`/`_AUTHOR` env levers (launcher-set via `options.env` / process env) so programmatic/agent sessions can relabel or skip; decide the `author` vocabulary (user/agent/unknown). Priority raised by the SDK finding.
- **D-001 — part-1 iteration 3: crash-safe lake read/append** (tolerate a torn line / atomic append). Pairs with the id-bearing-read gap the computer-dropper spike found.
- **P1 (AI-drafted text submitted in a human session)** — irreducible at capture; belongs to the future triage/authorship-discrimination layer (DEC-002/004).
