# claude-account-switcher — Specification

> Status: draft
> Revision: 3
> Last updated: 2026-06-26

## Goal

Decouple Claude account authorization from the browser session — making it an explicit, portable, per-process artifact — so N Claude accounts can run on one machine concurrently for SDK/headless agents (via per-process oat slots) and sequentially for interactive sessions (via whole-environment switch), with the right account guaranteed in each slot.

## Constraints

- **True SDK concurrency:** two or more processes run under different accounts simultaneously with no token hijack and no shared shell state mutation.
- **Zero shell disruption:** no PID-scanning, no forced sub-shell, no killing live sessions; the parent shell is never mutated by the runner.
- **Browser-decoupled after mint:** the browser is touched exactly once per oat (the initial mint ritual); nothing reads or depends on browser session state after that.
- **Right-account verification built in:** the correct account is confirmed at `add` time by human attestation (consent page shows the email; the tool enforces a retype-confirm). Subsequent launches echo the stored label→email binding; scripted live email lookup is permanently unavailable (oat is `user:inference` scope only — no `user:profile`).
- **Portable core:** mac and Linux mechanisms are identical (`CLAUDE_CONFIG_DIR` + `CLAUDE_CODE_OAUTH_TOKEN` work the same); verified on macOS. Linux/WSL documented as expected/untested. The only platform-specific piece is the optional Chrome-profile mint-routing convenience (AC2.2), which degrades to a portable fallback.
- **Secret stored local-only:** the oat file lives outside the repo AND outside iCloud (physical location is the defense; `.gitignore` does not stop iCloud sync).
- **Credential primitive = 1-year inference-scoped oat:** the portable artifact is the `sk-ant-oat01-…` string produced by `claude setup-token`, injected per-process via `CLAUDE_CODE_OAUTH_TOKEN`.

## Success criteria

- Two `cas run <label> -- <cmd>` invocations under different labels execute concurrently with no token collision and no mutation of each other's or the parent shell's environment.
- `add <label>` drives the full mint ritual (logged-out browser context → auto-captures oat → email retype-confirm → liveness check → store write) without requiring the human to copy-paste the oat string.
- `list` displays each label with its bound email, oat age, and indicates which label (if any) matches the current interactive login.
- `use <label>` performs a sequential whole-environment interactive switch via `claude auth login`.
- `rm <label>` drops the record from the store and walks the user through server-side revocation with safe-ID guidance.
- Right-account shown via label→email echo at `run` and `use`; no **automated** false-positive is possible because the binding is write-once at mint. The residual risk is human mis-attestation at capture (typing the wrong email), mitigated — not eliminated — by the AC2.6 retype-confirm.

## Out of scope

- **Team-provisioning / onboarding / check-in layer** — do not build; v1 must keep it *feasible* via cheap seams (record-per-label schema; optional per-label `mint_profile` field) without implementing the layer itself.
- **Windows / PowerShell** — deferred; rides with the team-provisioning layer.
- **No-reauth credential-blob swap (D-001)** — swapping the macOS Keychain `claudeAiOauth` blob + `oauthAccount` metadata for interactive switch without reauth; deferred (fragile, undocumented internals, spoof hazard).
- **Persistent Chrome-profile↔account association & onboarding (D-002)** — recording a durable profile↔Claude-account link and auto-relaunching that profile on future mint/reauth; deferred. NOTE: v1 *does* enumerate Chrome profiles and open the mint URL in a user-selected one (a browser-routing convenience, macOS/Chrome only — see AC2.2), recording the chosen profile in the `mint_profile` field; what remains deferred is the persistent association, auto-reuse, and onboarding flow.
- **iCloud-synced encrypted multi-device credential store (D-003)** — deferred; requires encryption-at-rest + key-distribution solution first.
- **1Password backend + store-backend abstraction** — deferred; reserved as the team-layer backend.
- **Encryption-at-rest** — deferred; FileVault + `chmod 600` is the v1 at-rest security posture.
- **`env` subcommand (power-user oat export to parent shell)** — deferred; the runner (`run`) is the default to preserve token hygiene.

## Acceptance criteria (MECE)

> This tree is mutually exclusive (no AC overlaps another) and collectively exhaustive (every success criterion and constraint traces to at least one AC leaf; every AC leaf traces back). Each leaf is independently testable.

### AC1. Credential store and slot substrate

- **AC1.1.** A per-user local store exists under `~/.collevity/` (exact filename determined at implementation), has permissions `chmod 600`, resides outside the repo AND outside iCloud, and survives a tool restart with all records intact.
- **AC1.2.** The store uses a record-per-label schema: each entry is a JSON object `{ email, oat, mint_date, mint_profile? }` keyed by label; reading an absent key returns "not found" and never crashes. Email-uniqueness across labels is not enforced at the schema level (duplicate bindings are permitted; the `add` flow warns — AC2.7).
- **AC1.3.** Each slot has a corresponding config dir at `~/.collevity/slots/<label>/` suitable for use as `CLAUDE_CONFIG_DIR`; the dir is created at `add` time and is absent before any `add` runs.
- **AC1.4.** The `mint_profile` field is present in the schema and accepted by the store's read/write layer (value may be `null`). It is populated by the mint-time profile selection (AC2.2); no persistent profile↔account association, auto-reuse, or validation logic is implemented (D-002).
- **AC1.5.** A label must be filesystem-safe (no path separators, no null bytes), unique across all records, and defaults to the email's local-part (text before `@`); a collision on the default forces the user to supply a custom label before any record is written.

### AC2. `add` — guided mint, capture, and bind

- **AC2.1.** `add <label>` (or `add` with no label, defaulting to the email local-part after confirmation) launches `claude setup-token` as a subprocess in a temporary isolated `CLAUDE_CONFIG_DIR` and captures the printed OAuth URL from its stdout (verified: `setup-token` prints the URL to stdout — DEC-010).
- **AC2.2.** The tool routes the captured OAuth URL into a browser for approval so the user authorizes in a deliberately chosen context. On macOS with Chrome, it offers to open the URL in a user-selected Chrome profile (presenting the available profiles so the user can pick one). The consent page (AC2.3) remains the authority on which account is being authorized — a Chrome profile's identity (its Google login) need not match the Claude account, so the profile list is a convenience for choosing a context, not an account cross-check. If a profile cannot be listed or targeted for any reason — non-macOS, Chrome absent, the chosen profile has no open window, unreadable profile data, or the user declines — the tool falls back to printing the URL for the user to open or paste into the context they want. The chosen path is announced to the user. (The mechanism for targeting a profile is an implementation-discovery item, DEC-012; the print fallback is the guaranteed path.) No persistent profile↔account association or auto-reuse is performed (deferred, D-002).
- **AC2.3.** The tool explicitly directs the user to read the consent page's "Logged in as `<email>`" display and use the Switch-account link if the wrong account is shown, before approving the authorization. (This is the account-selection step; it happens on the consent page before approval, distinct from the post-capture retype-confirm at AC2.6.)
- **AC2.4.** The oat string is auto-scraped from `setup-token`'s stdout (verified: the `sk-ant-oat01-…` token prints to stdout after auth — DEC-010); the user is never asked to copy or paste the oat.
- **AC2.5.** After token capture, the tool runs a liveness check (`CLAUDE_CODE_OAUTH_TOKEN=<oat> claude auth status` in a fresh config dir) and confirms `loggedIn: true, authMethod: "oauth_token"` before proceeding; a failed liveness check aborts `add` with a clear error.
- **AC2.6.** The tool prompts the user to type the email address they observed on the consent page; after entry, the tool echoes it back and requires an explicit confirmation keystroke before writing; no scripted auto-read of the email is attempted.
- **AC2.7.** On successful confirmation, the record `{ email, oat, mint_date, mint_profile? }` is written to the store with `chmod 600` (`mint_profile` populated only if a Chrome profile was selected at AC2.2), the slot config dir `~/.collevity/slots/<label>/` is created, and the tool prints a summary: label, email, and mint date. If the email is already bound under a different label, the tool warns and requires explicit confirmation before writing (non-blocking — duplicate bindings are permitted).
- **AC2.8.** If the chosen label collides with an existing record (including the default email-local-part label), the user is prompted to supply a different label; the write is blocked until a unique label is given.

### AC3. `run` — SDK/headless per-process runner

- **AC3.1.** `run <label> -- <cmd…>` launches `<cmd…>` as a child process with exactly two extra env vars injected: `CLAUDE_CONFIG_DIR=~/.collevity/slots/<label>/` and `CLAUDE_CODE_OAUTH_TOKEN=<oat from record>`.
- **AC3.2.** The oat is never written to the tool's stdout, never placed in the parent shell's environment, and never appears in shell history (the runner pattern, not env-export).
- **AC3.3.** Immediately before launch, the tool prints: `running as <label> (<email>)` using the email stored at mint; no live email lookup is attempted.
- **AC3.4.** Two or more `cas run` invocations under different labels can execute simultaneously without any token collision, config-dir collision, or parent-shell mutation; each child's env is fully isolated.
- **AC3.5.** If `<label>` does not exist in the store, the command fails before launching any subprocess and prints a clear error listing available labels.
- **AC3.6.** If a launched child process exits with an error, the tool surfaces the child's stderr unmodified. *If* a clean, auth-specific failure signal is detectable (best-effort — detectability is an implementation-discovery item, not a guarantee), the tool additionally prints guidance directing the user to `cas rm <label>` and re-run `cas add`. No automatic revocation or re-mint is performed.

### AC4. `list` — slot registry display

- **AC4.1.** `list` (no args) prints one row per stored label showing: label, bound email, and oat age in human-readable units (e.g. "42 days" derived from `mint_date`).
- **AC4.2.** `list` runs `claude auth status` against the **default config dir** (no special env) and matches the returned `email` field against stored records; the matching label row is marked as the active interactive login; if no match, a "no active interactive login matched" note is appended. (The email field is available here because this is the non-oat interactive path; the oat-token path returns no email per DEC-001, but `list` never uses it for the match.)
- **AC4.3.** Output requires no flag or pipe to be human-readable; the active vs inactive distinction is visually unambiguous in a terminal.

### AC5. `use` — sequential interactive switch

- **AC5.1.** `use <label>` invokes `claude auth login --email <stored-email>` (the reauth-based sequential whole-environment switch per DEC-004; the `--email` flag is verified in active use — DEC-010); the user completes the reauth flow natively in the browser.
- **AC5.2.** The tool does not attempt to mutate `~/.claude.json` or any Keychain entry directly; the only side effect is whatever `claude auth login` writes.
- **AC5.3.** If `<label>` does not exist in the store, the command fails with a clear error before invoking any auth subcommand.

### AC6. `rm` — drop record and guide revocation

- **AC6.1.** `rm <label>` removes the record from the store and prints confirmation of the deletion.
- **AC6.2.** The tool prints step-by-step server-side revocation guidance: navigate to Settings → Claude Code → Authorization tokens; identify the correct entry by its `user:inference`-only scope and the mint date shown by `list`; warns explicitly NOT to revoke multi-scope device-login entries, recognizable by the presence of `user:sessions:claude_code` and `user:profile` in the scope list (the setup-token oat has neither — it is `user:inference`-only).
- **AC6.3.** As part of `rm`, the slot config dir `~/.collevity/slots/<label>/` is deleted unconditionally (the dir holds no secret — the oat lives in the store record being removed — and is regenerable by re-running `add`); the deletion is reported to the user.
- **AC6.4.** If `<label>` does not exist in the store, the command fails with a clear error.

### AC7. Distribution and export packaging

- **AC7.1.** The tool's source lives under `collevity-tooling/claude-account-switcher/` in the private monorepo; `deliverables/` within that directory is a staging area only — no code is executed from `deliverables/` directly.
- **AC7.2.** An export step (script or documented procedure) produces a clean public repo (`claude-account-switcher`) with no monorepo-internal paths, no Levi-specific config baked in, and no private file references.
- **AC7.3.** The installed CLI name is `claude-switch` (canonical); a `cas` symlink alias is created at install time; both invoke identical behavior.

## Implementation phases

> Each phase is implementable to completion without any work from a later phase. Dependencies flow only backward. Every leaf AC appears in exactly one phase.

### Phase 1. Store and slot substrate

**Delivers:** the per-user local store (file, schema, CRUD), slot config-dir lifecycle, and label validation — the bedrock every other command builds on.
**Unblocks:** all subsequent phases.

- AC1.1
- AC1.2
- AC1.3
- AC1.4
- AC1.5

### Phase 2. `add` — mint capture flow

**Delivers:** end-to-end guided onboarding: `setup-token` subprocess, OAuth URL routing to the browser (Chrome-profile pick with portable fallback), oat auto-scrape, liveness verification, email retype-confirm, and store write — the only mechanism that produces valid records.
**Depends on:** Phase 1 (store and slot substrate).

- AC2.1
- AC2.2
- AC2.3
- AC2.4
- AC2.5
- AC2.6
- AC2.7
- AC2.8

### Phase 3. `run` — SDK per-process runner

**Delivers:** the core concurrency deliverable — per-process oat injection into a child subprocess, identity echo, concurrent-safe isolation, and dead-token error surface. This is the primary capability this tool exists to provide.
**Depends on:** Phase 1 (store substrate to look up records); Phase 2 (live records produced by `add` required for end-to-end testability).

- AC3.1
- AC3.2
- AC3.3
- AC3.4
- AC3.5
- AC3.6

### Phase 4. Management verbs — `list`, `use`, `rm`

**Delivers:** slot visibility (`list`), sequential interactive switch (`use`), and guided removal + server-side revocation guidance (`rm`). Together these complete the day-to-day operational surface.
**Depends on (data):** Phase 1 (store reads/writes); Phase 2 (records to manage).
**Ordering note (sequencing, not a data dependency):** sequenced after Phase 3 so the primary `run` deliverable is demonstrable before the management surface is layered on (DEC-008). `list`/`use`/`rm` have no code dependency on `run`.

- AC4.1
- AC4.2
- AC4.3
- AC5.1
- AC5.2
- AC5.3
- AC6.1
- AC6.2
- AC6.3
- AC6.4

### Phase 5. Distribution and export packaging

**Delivers:** the clean-export pipeline from private monorepo workshop to public `claude-account-switcher` repo, plus the installed CLI name and alias.
**Depends on:** Phase 4 (complete tool before packaging).

- AC7.1
- AC7.2
- AC7.3

## Open questions

None blocking. The interview passed the clarity gate (2026-06-26) on all five core items, and the load-bearing CLI spike — whether `claude setup-token` prints the OAuth URL (and the oat) to stdout — was verified resolved (DEC-010; both print to stdout). Two acknowledged implementation-discovery items remain (neither a spec-level open question, because each has a guaranteed fallback): (1) whether a dead-oat failure produces a cleanly auth-specific signal at the child-process boundary — AC3.6 handles this as best-effort, surfacing the child's stderr regardless; (2) whether a focus-then-open (or any) technique reliably lands the URL in the chosen Chrome profile — AC2.2 falls back to printing the URL either way (DEC-012).

## Deferred for cross-platform (tracked, not open)

- The Chrome-profile mint-routing convenience (AC2.2) is macOS/Chrome-specific. A future iteration should add the equivalent profile-selection routing for Linux/other browsers, or confirm the portable fallback is sufficient there.
