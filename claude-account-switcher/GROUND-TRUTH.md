# Ground Truth
*Verified 2026-06-24 against the live `claude` CLI **v2.1.191** on this machine, plus a web scan of the public tools. This is the reality the wiki doc must be built on. Where the launch prompt is wrong or blanked, the correction is here.*

Legend: **[VERIFIED]** = checked on this machine · **[DOCUMENTED]** = from known CLI behaviour, not re-tested here · **[OPEN]** = needs a decision or a check before we write it up.

---

## 1. The discovery command — `claude auth status` [VERIFIED]

```
claude auth status          # JSON is the default
claude auth status --text    # human-readable
```
Real output on this machine:
```json
{
  "loggedIn": true,
  "authMethod": "claude.ai",
  "apiProvider": "firstParty",
  "email": "admin@nascentech.com",
  "orgId": "9e79f787-0b43-443b-a0a4-b9aef219ab33",
  "orgName": "admin@nascentech.com's Organization",
  "subscriptionType": "pro"
}
```
The prompt's instinct is right: this reports the **account email identity**, not disk paths. This is how a dev confirms *which* account a given shell is bound to. Note `subscriptionType` here is `pro` (not Max) — worth flagging for the "trek = primary tier" framing.

## 2. Path A's real lever — `CLAUDE_CONFIG_DIR` [VERIFIED]

The prompt left the env var **blank**. It is **`CLAUDE_CONFIG_DIR`**. It redirects the *entire* config + auth state to a directory of your choosing (default `~/.claude`).

**Proven on this machine:** running `CLAUDE_CONFIG_DIR=<fresh dir> claude auth status` returned `"loggedIn": false` while the default config stayed logged in as admin@nascentech.com. → **Fully isolated auth state, per process. This is the concurrency mechanism.** It is set inline per-process, so two tabs with two different values never touch each other's tokens. The host shell is unchanged. This satisfies requirements 1 (true concurrency) and 2 (zero shell disruption) with no wrapper at all.

Inline / alias form:
```zsh
alias cctrek='CLAUDE_CONFIG_DIR="$HOME/.claude_trek" claude'
alias ccsec='CLAUDE_CONFIG_DIR="$HOME/.claude_secondary" claude'
```

## 3. Login flags [VERIFIED]

```
claude auth login            # --claudeai is the default (subscription)
claude auth login --email <email>   # pre-populate the email on the login page
claude auth login --console  # API/console billing instead of subscription
claude auth login --sso      # force SSO flow
```
`--email` pre-populating the address is a genuinely useful onboarding aid for "log THIS profile into THIS account."

## 4. Where the tokens actually live [DOCUMENTED — keychain not re-probed]

- **macOS:** the OAuth credential is stored in the **login Keychain** (item `Claude Code-credentials`), *not* as a plaintext file under `~/.claude`. (Deliberately not dumped here — credential probing is correctly blocked by the sandbox.)
- **Linux / WSL:** stored as `~/.claude/.credentials.json` (mode 600) inside the config dir.
- Either way, the **isolation test in §2 proves the auth lookup is keyed off `CLAUDE_CONFIG_DIR`** — a separate config dir resolved to a separate (empty) credential even on macOS. So Path A works regardless of the keychain-vs-file storage detail.
- **[OPEN]** Worth one explicit check before publishing: confirm that two `CLAUDE_CONFIG_DIR` values map to two *distinct* macOS Keychain items (vs. one shared item). The §2 result strongly implies distinct, but state it with certainty in the wiki only after a clean confirm.

## 5. Corrections to the prompt's "Chrome cookie" assumptions

- **"Incognito Bypass flag prefix" — [no such flag].** Claude Code's `auth login` opens the system default browser for OAuth; there is no documented `--incognito` flag on `claude`. The real cookie-isolation move is at the **browser** layer, not a `claude` flag.
- **The Manual Copy/Paste URL Intercept — this is the sound method [DOCUMENTED].** `claude auth login` prints the OAuth URL to the terminal. The clean sequence is: copy that URL → paste into an **incognito/private window** (or a Chrome profile already signed into the intended account) → complete auth → the callback returns to the waiting CLI → confirm with `claude auth status`. This sidesteps requirement 3 (default browser silently grabbing the wrong session) without any `claude` flag. The wiki's "functional test sequence" should be: log in profile `trek` via incognito as account A, `claude auth status` shows A; in a second tab log in `secondary` via a *separate* incognito as account B, `claude auth status` shows B; then re-check the first tab still shows A.

## 6. The "fresh read on every keypress" claim — [OPEN / likely overstated]

The prompt asserts Claude Code "reads credentials freshly from disk on every single enter-key prompt." **Not verified, and probably an embellishment.** What is true and sufficient: each `claude` *process* binds to its `CLAUDE_CONFIG_DIR` at launch and manages/refreshes its own token within that scope. The wiki should make the **per-process** claim (which is proven) and drop the per-keystroke claim unless we can demonstrate it.

## 7. Path B and the public tool — reframed

The blanked "public tool" is **`cc-account-switcher-zsh`** (Second-Victor; siblings: `claude-swap`, `ccs`, `ming86/cc-account-switcher`). Critical point for the guide:

> These tools **swap one shared credential** in a single `~/.claude`. That is *mutually exclusive* — only one account is "active" at a time. They **cannot** do Tab-A-and-Tab-B-at-once. They are a different problem (sequential switching) than ours (concurrent isolation).

So Path B, as the prompt frames it ("don't scan PIDs, don't block, just hot-swap"), is mostly **redundant with Path A** for the concurrency goal — `CLAUDE_CONFIG_DIR` already is the lightweight, non-blocking, no-PID-scan mechanism. Path B's honest remaining value is **ergonomics**: a tiny helper to *create/list/label* config dirs and print which account each one is (`claude auth status` per dir), not to "switch" a global. **[OPEN]** decision for Levi: keep Path B as a thin convenience wrapper over Path A, or drop the two-path framing and present one correct approach with optional sugar.

## 8. Multi-agent workspace warning [DOCUMENTED]

Two profiles run in the **same project directory** share that repo's project-scoped state: the hidden **`.claude/`** dir (e.g. `settings.local.json`) and the per-project entry Claude Code keeps keyed by directory path. Concurrent agents in one dir can race on local settings / session files. Prompt's instinct is correct: **mitigate with separate Git worktrees** (already a Collevity convention — see `../dropper-pipeline` setup), one worktree per account/agent, so config-dir isolation (auth) is matched by directory isolation (project state).

---

## Bottom line for "reconsidering components"

1. **Path A (`CLAUDE_CONFIG_DIR` inline) is the spine.** Proven, satisfies all 3 requirements, zero wrapper. The wiki is mostly "document Path A correctly + the incognito-URL login ritual + worktree hygiene."
2. **Path B is questionable as a co-equal path.** Reframe as optional ergonomics over Path A, or cut. → needs Levi's call.
3. **Two factual claims in the prompt are wrong/unverified** (incognito flag; per-keystroke disk reads) — corrected above; don't carry them into the wiki.
4. One small **[OPEN]** verification (keychain item per config dir) before publishing certainty.
