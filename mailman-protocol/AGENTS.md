# mailman-protocol — invariants

- **Hooks fail open; modules do not.** A script in `bin/` that is installed into
  `settings.json` (`mailman_check.py`, `mailman_register.py`,
  `mailman_publish.py`) must exit 0 on every path and write nothing to stdout it
  did not mean to — on Claude `UserPromptSubmit`, exit 2 erases the user's
  prompt and stray stdout is injected; on `Stop`, a non-zero exit reads as
  blocking the turn. A `bin/` module that is *not* a hook (`mailman_view.py`) is
  free to raise and to exit non-zero; say which it is in its docstring.
- **A hook's imports are part of its fail-open contract.** An `ImportError` at
  module level escapes `main()`'s handler and exits non-zero. Hooks that import
  a sibling module wrap the import in `try/except` and degrade instead.
- **State is split by lifetime, not by convenience.** Roster and published views
  → `~/.collevity/cache/mailman/` (that dir is declared disposable; session
  presence is correctly losable). Notes and read-state → `~/.collevity/mailman/`
  (an unread note is data loss, not a resync). `MAILMAN_CACHE` / `MAILMAN_HOME`
  override.
- **Shared files append; owned files replace.** The roster is one file many
  sessions append to, so it is JSONL, append-only, reduced newest-wins by the
  reader. A view is owned by one session, so it is a whole file rewritten
  through a temp file and `os.replace` — no contention, no reduction pass, and
  staleness is the file's own timestamp.
- **Mechanical and semantic view fields have different authors.** Hooks write
  `session_id`, `cwd`, `kind`, `updated_at`. Only the session's own agent writes
  `topic`, `recap`, `working_on` (and `reported_at`). A hook refresh must never
  clobber the semantic half — that is what `touch()` guarantees.
- **Addressing is by published view.** A recipient is chosen by reading what
  sessions publish about themselves — never by folder, assigned name, or subject
  subscription. T6 was retired settling this; do not reintroduce a folder-to-
  session lookup as an address. A directory is at most a filter.
- **View age is last activity, not liveness.** `age_seconds()` reports how long
  since a view last moved. Both triggers only fire on activity, so a session
  left open for days is stale and fully alive. Do not refuse a recipient because
  the view is old. An ended-session signal does not exist yet; T3 must not
  invent a live/dead test from age.
- **Both envelope shapes, always.** Claude sends `session_id`, Grok sends
  `sessionId` and reaches the same install through hook compatibility. Anything
  reading a payload accepts both.
- Stdlib only, no venv — these run on the live prompt path.
  Tests: `python3 -m pytest tests/ -q`.
