# Interview Brief — claude-account-switcher
*Handoff from the 2026-06-24 setup session into a fresh `/spec interview`. Splits what's already settled (don't re-litigate) from what the interview should actually drive on.*

**Read order for the fresh session:** this file → `GROUND-TRUTH.md` (verified CLI facts) → `README.md` (objective + scope). The `claude-account-switcher` auto-memory note loads automatically and echoes the same.

---

## LOCKED — settled in prior interview-quality discussion; treat as given

- **Objective.** Run multiple Claude accounts on one machine *truly concurrently*, with the **right account guaranteed in each slot**, where **authorization is an explicit, portable artifact** — not a side effect of which account the browser is logged into.
- **Concurrency includes the SDK.** Not just two terminal tabs — launching **SDK agents under different accounts simultaneously** (for usage/cost control). The mechanism must be env/process-scoped so it works identically for an interactive session and a spawned SDK process.
- **Design spine (reframed off the original Gemini prompt):**
  - *Slot / concurrency primitive* = `CLAUDE_CONFIG_DIR` (per-process; **empirically proven** to isolate auth state).
  - *Credential primitive* = authorize each account **once**, capture a **portable token**, plant it into the named slot. Browser touched only at the one-time mint.
  - Public single-credential switchers (cc-account-switcher-zsh etc.) are mutually exclusive, not concurrent — explicitly **not** our model.
- **Right-account verification is a deliverable**, not an afterthought (`claude auth status` email match + guidance + error-checking). Most users won't grok the Chrome-profile trap.
- **Browser decoupling is a hard constraint.** After the one-time mint, nothing reads the browser session. Incognito preferred at mint to dodge the cookie grab.
- **Distribution:** private workshop here in the monorepo → **export** the deliverable to a clean public repo named `claude-account-switcher`. "deliverables/" is staging only.
- **Out of scope now** (guiding context, do NOT spec it this iteration): the team-provisioning / "check-in auto-binds teammate to their work account + runs processes" layer. Levi mints/holds accounts; teammates receive them. Future iteration.
- **Verified facts** live in `GROUND-TRUTH.md` — discovery cmd is `claude auth status`; corrections: no `claude` incognito flag; isolation is per-*process*, not per-keystroke; CLI tested at v2.1.191.

## OPEN — what the interview should actually resolve

1. **Credential-mint mechanism.** Is `claude setup-token` the right primitive — does it yield a transplantable token, and does its one-time mint still require a browser? *Blocked on a manual test Levi will run in an isolated `CLAUDE_CONFIG_DIR`.* Alternatives to weigh: keychain-item transplant, `.credentials.json` transplant, env-injection. **The spec likely can't converge until this is answered.**
2. **Slot model & UX.** How are slots created / named / listed / removed? Convention (`~/.claude_<label>`)? A small registry? How does a user define their own labels (trek/secondary were just examples)?
3. **Setup flow — what does "flawless" mean concretely?** One command vs guided? Which options (incognito vs dedicated browser profile)? This needs to become testable acceptance criteria.
4. **Verification UX.** What does the guided "did you authorize the right account?" flow look like — interactive confirm, error messages, re-mint path?
5. **Platform support.** macOS only for v1, or Linux/WSL too? (Drives credential storage: Keychain vs `.credentials.json`.)
6. **SDK orchestration interface.** How does a user actually launch SDK agents under different accounts — env-var wrapper, a helper script, documented pattern?
7. **Distribution shape.** What does the public repo ship — one script, a set, install method (curl/brew), docs structure?
8. **Concurrency hazards.** The same-project-dir `.claude/` race; worktree mitigation — in scope for v1 or documented-only?
9. **v1 MVP boundary.** Smallest thing that proves it (e.g., 2 accounts, macOS, CLI tabs) vs the full ask (N accounts + SDK + cross-platform + public-ready). Where's the line for *this* iteration?

## Constraints / non-negotiables to carry into ACs
- True concurrency (two processes, two accounts, no token hijack).
- Zero shell disruption (no PID-scanning wrapper, no forced sub-shell, no killing live sessions).
- Browser-decoupled auth after mint.
- Right-account verification built in.
