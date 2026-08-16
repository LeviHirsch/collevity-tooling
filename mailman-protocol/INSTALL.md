# Mailman check hook — install runbook

**Status (2026-08-16):** **STUB, NOT INSTALLED.** `bin/mailman_check.py` occupies
the hook slot and does nothing with the payload. Install it only if you want the
slot proven early; nothing breaks if you wait for T2.

Canonical script:

```
…/collevity-tooling/mailman-protocol/bin/mailman_check.py
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

Split deliberately: `~/.collevity/README.md` declares `cache/` disposable —
"deleting a tool's dir costs at most one redundant resync." That is true of
session presence and false of an unread note. Override with `MAILMAN_HOME` and
`MAILMAN_CACHE` if needed.

The stub creates none of these. T1 and T13 do.

## Verify an install

```sh
echo '{"session_id":"test","cwd":"/tmp","prompt":"hi"}' \
  | MAILMAN_DEBUG=1 python3 bin/mailman_check.py; echo "exit=$?"
```

Expect `exit=0`, no stdout, and one line in `bin/mailman_errors.log`. Then submit
a real prompt in a fresh session and confirm the same log grew — that proves the
third slot fires. Unset `MAILMAN_DEBUG` afterwards, or the log grows every prompt.

## Uninstall

Remove the object from the `UserPromptSubmit` array. Nothing else to undo — the
stub writes no state outside its sidecar log.
