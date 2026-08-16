# mailman-protocol — invariants

- **Hooks fail open; modules do not.** A script in `bin/` that is installed into
  `settings.json` (`mailman_check.py`, `mailman_register.py`) must exit 0 on
  every path and write nothing to stdout it did not mean to — on Claude
  `UserPromptSubmit`, exit 2 erases the user's prompt and stray stdout is
  injected. A `bin/` module that is *not* a hook (`mailman_resolve.py`) is free
  to raise and to exit non-zero; say which it is in its docstring.
- **State is split by lifetime, not by convenience.** Roster →
  `~/.collevity/cache/mailman/` (that dir is declared disposable; session
  presence is correctly losable). Notes and read-state →
  `~/.collevity/mailman/` (an unread note is data loss, not a resync).
  `MAILMAN_CACHE` / `MAILMAN_HOME` override.
- **Both envelope shapes, always.** Claude sends `session_id`, Grok sends
  `sessionId` and reaches the same install through hook compatibility. Anything
  reading a payload accepts both.
- Stdlib only, no venv — these run on the live prompt path.
  Tests: `python3 -m pytest tests/ -q`.
