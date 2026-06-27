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
