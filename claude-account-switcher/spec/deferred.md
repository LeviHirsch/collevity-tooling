# Deferred backlog

Future-tense, mutable. Items consciously postponed out of the current iteration. Triaged at the
start of each new iteration's interview.

---

## D-001 — No-reauth interactive switch (credential-blob swap)
- **Category:** enhancement
- **Deferred since:** iteration 1
- **Last touched:** iteration 1 (2026-06-25)
- **Defer count:** 1
- **Source:** via /spec interview (iteration 1); Levi's `/status` hot-swap discovery
- **Description:** Switch the active interactive account WITHOUT a browser reauth by swapping a
  previously-captured credential set: the macOS Keychain `claudeAiOauth` blob (accessToken +
  **refreshToken** + expiresAt) AND the `~/.claude.json` `oauthAccount` metadata block. The
  refreshToken keeps the session alive, so no OAuth round-trip is needed.
- **Why deferred:** depends on undocumented Keychain/JSON internals (fragile across CLI updates);
  spoof hazard if metadata is swapped without the credential; possible Keychain-password prompts on
  write. Too risky as a *distributable* v1 backbone; reauth (DEC-004) ships instead.
- **Open spikes before adopting:** (1) confirm a full swap actually switches the *operative* account
  (not just the displayed nameplate); (2) confirm `security` write doesn't prompt for password each
  switch; (3) confirm robustness across a `claude` version bump.

---

## D-002 — Chrome-profile-as-account-anchor (onboarding + verification)
- **Category:** enhancement / onboarding-layer
- **Deferred since:** iteration 1
- **Last touched:** iteration 1 (2026-06-26) — partially pulled forward; see "Now built in v1" below
- **Defer count:** 1
- **Source:** via /spec interview (iteration 1); Levi's Chrome-profile onboarding idea
- **Now built in v1 (DEC-011):** Chrome-profile *enumeration + selection + open-the-mint-URL-in-the-chosen-profile* is now a v1 browser-routing convenience (AC2.2, macOS/Chrome), and the chosen profile is recorded in `mint_profile`. What remains deferred here is the **persistent profile↔account association, auto-reuse on future mint/reauth, and the onboarding flow** that ties them together.
- **Description:** Enumerate the user's Chrome profiles (Chrome `Local State` exposes each profile's
  google email); onboarding associates a chosen Chrome profile with a chosen Claude account; launch
  that profile to mint/reauth in the correct cookie context (a robust, persistent replacement for
  incognito). NOTE: a Chrome profile's google email is NOT reliably the Claude account's email, so
  it does NOT cross-check the typed email. The profile's value is **context continuity** — an
  US-asserted association (profile X ↔ Claude account Y, recorded at onboarding) means relaunching
  that profile lands the same Claude login via persistent cookies. That's a "same context → same
  account" guarantee, not an email match; it does not by itself resolve the DEC-005 fat-finger risk.
- **Why deferred:** reading Chrome internals is platform-specific and brittle; the
  associate-and-onboard flow belongs to the deferred team-provisioning/onboarding layer; v1 capture
  uses dedicated-logged-out-profile / incognito / manual paste WITHOUT enumeration.
- **Prepare-for seam in v1 (build now, cheap):** (1) capture step accepts an OPTIONAL mint-context
  profile identifier per label; (2) store schema is a record-per-label (extensible), so a
  `mint_profile` field and a profile-derived verification can slot in without redesign.
- **Caveat:** profile's Google login == Claude login only under Google-SSO; otherwise the profile is
  still a durable mint context but the auto-association is looser.

---

## D-004 — `add` mint: interactive auth-code paste-back bridge (BLOCKER)
- **Category:** defect / blocker
- **Deferred since:** iteration 1
- **Last touched:** iteration 1 (2026-07-21)
- **Defer count:** 1
- **Source:** via live manual tryout during paused /spec close (iteration 1); see DEC-017
- **Description:** `claude setup-token` (v2.1.198) prompts `Paste code here if prompted >` and waits on
  stdin for the `code#state` string from the remote callback page (`platform.claude.com/oauth/code/
  callback`) before exchanging it for the oat. cas `mint()` only reads the pty and never forwards a
  pasted code, so `add` stalls and cannot complete. **Fix:** detect the paste prompt in the pty stream,
  prompt the user via the io surface for the code, `os.write` it to the pty master (setup-token's
  stdin), then continue scraping the oat. Forward the full `code#state` string verbatim.
- **Why deferred:** Levi chose plan-not-fix for now (2026-07-21); it is real interaction work plus a
  DEC-010 addendum, better done deliberately than hacked mid-tryout.
- **Blocks:** end-to-end `add`; therefore any real `list`/`run`/`use`/`rm` on genuine records; and
  `/spec close` for iteration 1 (cannot close over a non-functional core flow).
- **Prereq already done:** pty widened to 4096 cols so the URL no longer truncates at 80 chars
  (committed separately; verified live + regression-tested).
- **Open question surfaced alongside:** whether the paste prompt can be reliably detected vs. timed;
  whether to strip `#state` (setup-token appears to want the full string — confirm during the fix).

---

## D-005 — `add` profile picker: show the Claude-account email per Chrome profile, not just Google email
- **Category:** enhancement / onboarding-layer
- **Deferred since:** iteration 1
- **Last touched:** iteration 1 (2026-07-21)
- **Defer count:** 1
- **Source:** via live manual tryout (iteration 1); Levi's observation while running `cas add`
- **Description:** The profile menu currently labels each Chrome profile with its Google/profile email
  (from Chrome `Local State`). Levi would like to additionally surface the *Claude* account email tied
  to that profile — e.g. derived from Claude's account-switcher history — so the pick reflects the
  Claude identity, not just the Google login. Relates closely to **D-002** (Chrome-profile-as-account-
  anchor): both want a durable profile↔Claude-account association surfaced at mint time.
- **Why deferred:** cosmetic/UX enhancement, not a blocker; depends on reading Claude's account-switcher
  state (undocumented, brittle) and overlaps the D-002 association work. Out of iteration-1 scope.
- **Caveat (from D-002):** a profile's Google login is not reliably its Claude login, so any such label
  is a best-effort hint, not an authoritative account cross-check.

---

## D-006 — `add` opens the Chrome profile before selection is confirmed
- **Category:** polish / UX
- **Deferred since:** iteration 1
- **Last touched:** iteration 1 (2026-07-21)
- **Defer count:** 1
- **Source:** via live manual tryout (iteration 1); Levi's observation
- **Description:** Levi noted the browser window launches "before a selection is made / before
  confirmation," which isn't ideal. Investigate whether the auto-open can be suppressed until after an
  explicit confirm, or whether the early open originates from `setup-token` itself ("Opening browser to
  sign in…" appears in its output) rather than cas's own routing. If it's setup-token's own auto-open,
  cas may be double-opening (its Chrome route + setup-token's default open); if so, consider suppressing
  one. Determine source before deciding the fix.
- **Why deferred:** UX polish, not a blocker; needs a small investigation into who opens the browser.

---

## D-003 — Multi-device synced credential store (encrypted)
- **Category:** enhancement
- **Deferred since:** iteration 1
- **Last touched:** iteration 1 (2026-06-26)
- **Defer count:** 1
- **Source:** via /spec interview (iteration 1); Levi's "let my other devices read it" idea
- **Description:** Let Levi's own devices share one oat store automatically (e.g. via iCloud) so a
  token minted once is usable everywhere without manual copy. Gated on **encryption-at-rest** so the
  cloud holds ciphertext, not the plaintext bearer token. Core unsolved sub-problem = **key
  distribution** (each device needs the decryption key; the key must not itself be the synced
  secret — candidates: a memorized passphrase, or a per-device Keychain key with a bootstrap).
- **Why deferred:** v1 is local-only (DEC-006); the oat is portable so the same token already works
  on every device once placed. Sync is convenience, not capability. Encryption + key distribution is
  real work; not worth it until multi-device use is actually felt.
- **Note:** the non-secret registry (label→email) can already sync freely today without any of this —
  only the secret needs the encrypted-sync treatment.
