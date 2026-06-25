# claude-account-switcher
*Seeded 2026-06-24. Side project under the `collevity-tooling` monorepo.*

## Objective (confirmed via interview, 2026-06-24)

Run **multiple Claude accounts on one machine — truly concurrently** — where the **right account is guaranteed in each slot** and **authorization is an explicit, portable artifact you control**, not a side effect of which account your browser happens to be logged into.

"Concurrent" means more than two terminal tabs: it includes **launching SDK agents under different accounts simultaneously** (for usage control / cost separation). The slot mechanism must therefore be env/process-scoped so it works identically for an interactive session and a spawned SDK process.

## The design spine (reframed)

- **Slot / concurrency primitive:** `CLAUDE_CONFIG_DIR` — per-process, proven to isolate auth state. Two processes with two values never touch each other's tokens. (This is what the public switchers *miss* — they swap one shared credential, which is mutually exclusive, not concurrent.)
- **Credential primitive:** authorize each account **once** and capture a **portable token** (candidate: `claude setup-token`), then *plant* it into the named slot. After the one-time mint, nothing reads the browser again — no auto-login hijack, and a teammate can be handed a pre-minted credential.
- **The unavoidable browser moment:** the one-time mint may legitimately use a browser (incognito preferred, to dodge the cookie-auth grab). Setup must be **straightforward, optionally guided, and flawless** — including **right-account verification** (most users won't grok the Chrome-profile trap, so we guide + verify via `claude auth status` email match + error-check).

See `GROUND-TRUTH.md` for what's been **verified on the live CLI** vs. what's still open, and `LAUNCH-PROMPT.md` for the original (Gemini) brief and its corrected assumptions.

## Scope

**In scope (now):**
- Concurrent multi-account on one machine (CLI tabs **and** SDK agents), via `CLAUDE_CONFIG_DIR` slots.
- One-time portable-credential setup + right-account verification + onboarding guidance.
- A distributable tool: others clone, point their own accounts in, get the same.

**Out of scope (kept as guiding context, not built now):**
- The team-provisioning / "check-in auto-binds you to your work account and runs processes" layer. Levi mints/holds accounts; teammates receive them. Future.

## Deliverable & distribution

- Workshop (private): this folder — everything, incl. future `spec/`, drafts, notes.
- Release (public): the deliverable is **exported** to a standalone public repo named `claude-account-switcher` (contents sourced from this project's `deliverables/`, created when the build runs). The word "deliverables" is only the internal staging folder — never the public repo name.

## Status

**Interview done, objective + scope locked, ground truth verified. Spec not yet written.** Next: run `/spec` to formalize, then build (Path A slots + credential mint + verification + docs).

## Related
- `../dropper-pipeline` (sibling project) · monorepo root `../README.md`
- [[collevity]] · [[orchestration-conventions]]
