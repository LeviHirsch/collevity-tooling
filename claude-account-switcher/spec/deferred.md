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
