# Mailman hooks — install runbook

**Status (2026-08-17):** **NOT INSTALLED.** Two entries are described here and
neither is live yet; installing touches the prompt path, which is Levi's call.

- `bin/mailman_check.py` — `UserPromptSubmit`. Still a stub for note *delivery*
  (that is T2), but it now refreshes this session's published view on every
  prompt (T18).
- `bin/mailman_publish.py` — `Stop`. Refreshes the same view when an agent turn
  ends, so a session in a long autonomous run does not read as stopped.

The `SessionStart` entry for `bin/mailman_register.py` is still undocumented
here — T17 folds it in.

Canonical scripts:

```
…/collevity-tooling/mailman-protocol/bin/mailman_check.py
…/collevity-tooling/mailman-protocol/bin/mailman_publish.py
```

Stdlib only — no venv, no `PYTHONPATH`. That is deliberate: this runs on every
prompt, and the fewer things it can fail to import, the better.

## Read this before installing

The prompt-capture hook's spec verified two behaviours of Claude
`UserPromptSubmit`, and both are load-bearing here:

- **Exit code 2 blocks and ERASES the user's prompt.**
- **stdout on exit 0 is injected into the conversation.**

`mailman_check.py` therefore exits 0 on every path including its own bugs, and
the stub writes nothing to stdout. When T2 adds delivery, stdout becomes
deliberate — the exit code does not. The design phrase "the scripted check can
stop the turn" means *the check does no further work*; it must never be read as
exit 2.

`tests/test_check_stub.py` asserts this contract against malformed JSON, empty
stdin, non-object payloads, missing keys, and an unwritable sidecar.
`tests/test_view.py` re-asserts it now that the hook also writes a view — including
a session id shaped like a path, which the view module refuses outright.

The same reasoning covers `Stop`: a non-zero exit there reads as blocking the
turn, so `mailman_publish.py` exits 0 on every path too.

## Where it sits

Third in the existing `UserPromptSubmit` array, after both live hooks:

```
UserPromptSubmit:  capture_prompt.py  →  sync_lake.py  →  mailman_check.py
```

Last on purpose. Capture is the one thing that must not be disturbed; a mailman
fault should never be upstream of it. Grok reaches this same install through
Claude-settings hook compatibility, so one entry covers both harnesses.

## settings.json snippet

Merge into `~/.claude/settings.json`. A `UserPromptSubmit` array already exists —
**append** this object to it, do not replace the existing entries.

```json
{
  "type": "command",
  "command": "python3 '/Users/levi/Library/Mobile Documents/com~apple~CloudDocs/00_COLLEVITY/02_CONTENT/collevity-tooling/mailman-protocol/bin/mailman_check.py'",
  "timeout": 5
}
```

`"timeout": 5` — tighter than capture's 10s. Capture must survive an iCloud
materialization stall because losing a prompt capture is permanent; a missed
note check just happens again next prompt. Cheap failure, short leash.

## State it will use

| Path | Role | Lifetime |
|---|---|---|
| `~/.collevity/mailman/notes.jsonl` | the notes (T1) | **durable** |
| `~/.collevity/mailman/notes.read.jsonl` | read-state (T9) | **durable** |
| `~/.collevity/cache/mailman/roster.jsonl` | live sessions (T13) | disposable |
| `~/.collevity/cache/mailman/views/<session_id>.json` | published views (T18) | disposable |

Split deliberately: `~/.collevity/README.md` declares `cache/` disposable —
"deleting a tool's dir costs at most one redundant resync." That is true of
session presence and false of an unread note. Override with `MAILMAN_HOME` and
`MAILMAN_CACHE` if needed.

T1 and T13 create the first three. The view files are created by
`mailman_check.py` and `mailman_publish.py` themselves — one per session, rewritten
in place through a temp file and `os.replace`, so a reader never catches a half
view.

## Verify an install

```sh
echo '{"session_id":"test","cwd":"/tmp","prompt":"hi"}' \
  | MAILMAN_DEBUG=1 python3 bin/mailman_check.py; echo "exit=$?"
```

Expect `exit=0`, no stdout, and one line in `bin/mailman_errors.log`. Then submit
a real prompt in a fresh session and confirm the same log grew — that proves the
third slot fires. Unset `MAILMAN_DEBUG` afterwards, or the log grows every prompt.

## The Stop entry

`Stop` has no existing mailman array. Add one:

```json
{
  "type": "command",
  "command": "python3 '/Users/levi/Library/Mobile Documents/com~apple~CloudDocs/00_COLLEVITY/02_CONTENT/collevity-tooling/mailman-protocol/bin/mailman_publish.py'",
  "timeout": 5
}
```

This does **not** wait on T14. That spike is about what *injection* each event
supports — whether stdout from `Stop` reaches context and whether blocking there
loops. This hook injects nothing; it writes a file and exits.

Verify it the same way:

```sh
echo '{"session_id":"test","cwd":"/tmp"}' \
  | MAILMAN_DEBUG=1 python3 bin/mailman_publish.py; echo "exit=$?"
cat ~/.collevity/cache/mailman/views/test.json
```

## Saying what this session is doing

The hooks only write the mechanical half of a view. `topic`, `recap`, and
`working_on` are written by the session's own agent, when they change:

```sh
python3 bin/mailman_view.py report --topic "Mailman protocol" --working-on "T18"
python3 bin/mailman_view.py list
```

`mailman_view.py` is **not** a hook — it is free to fail loudly. With no
`--session` it uses `CLAUDE_SESSION_ID`/`GROK_SESSION_ID`, then the lone
published view in the current directory, and refuses rather than guessing when
two sessions publish from the same place.

## Uninstall

Remove the objects from the `UserPromptSubmit` and `Stop` arrays. Then delete
`~/.collevity/cache/mailman/views/` if you want the published views gone — that
dir is disposable and nothing else reads it yet.
