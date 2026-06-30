"""The `run` command: per-process oat injection into a child (spec AC3).

This is the tool's primary capability — launch ``<cmd…>`` as a child with the
slot's credential injected **for that process only**, never touching the parent
shell (the runner pattern, DEC-007). The oat's lifetime is exactly the child's;
it never enters ``os.environ``, the tool's stdout, or shell history (AC3.2).

Design decisions surfaced for this phase (forks the spec left open):

- **Process model = ``subprocess.Popen``, cas stays alive as the parent.** A pure
  ``os.execvpe`` would replace cas with the child and make AC3.6's "additionally
  print guidance after the child fails" impossible (there is no cas left to print
  it). Popen lets cas wait, propagate the child's exit code, forward signals, and
  run the best-effort auth-failure check after the child exits.
- **stdout = TTY-aware tee; stdin + stderr = always inherited.** A live dead-token
  probe (CLI v2.1.197) showed the auth failure prints to **stdout** — not stderr —
  as ``Failed to authenticate. API Error: 401 Invalid bearer token`` with exit 1.
  So detection has to watch stdout. To keep an interactive child transparent, when
  cas's stdout is a TTY we inherit it directly (no scan); when it is piped/headless
  (the SDK case ``run`` exists for) we tee it — passing bytes through verbatim and
  live while buffering a tail to scan. stderr is always inherited, so AC3.6's
  "surface the child's stderr unmodified" holds trivially.
- **``--`` boundary = manual split before argparse** (see :func:`split_double_dash`),
  so the child's own flags (``claude -p --foo``) are never interpreted by cas.

The boundary the Phase 3 tests mock is :class:`Launcher` (the real subprocess +
tee); everything around it — env construction, label lookup, the auth matcher,
exit-code normalization, the ``--`` split — is pure and unit-tested directly.
"""

from __future__ import annotations

import os
import re
import signal
import subprocess
import sys
from typing import Callable, Optional, Sequence, Tuple

from .io import ConsoleIO, IO
from .paths import slot_dir
from .store import Record, Store

#: Exit code when the label is unknown (AC3.5 — fails before any launch).
NO_SUCH_LABEL = 2

#: Exit code when the child command itself cannot be found / launched.
COMMAND_NOT_FOUND = 127

#: How many trailing bytes of teed stdout to keep for the auth scan (AC3.6).
_TAIL_MAX = 64 * 1024

# A launcher returns (raw_returncode, captured_tail_or_None). The tail is the
# teed stdout text when we scanned it, else None (TTY passthrough — nothing to
# scan). raw_returncode may be negative (killed by signal) — see normalize.
Launcher = Callable[[Sequence[str], dict], Tuple[int, Optional[str]]]


# --- pure helpers (unit-tested directly) -----------------------------------

def split_double_dash(argv: Sequence[str]) -> Tuple[list, Optional[list]]:
    """Split ``argv`` on the FIRST ``--``.

    Returns ``(before, after)``. ``after`` is ``None`` when no ``--`` is present,
    and ``[]`` when ``--`` is the last token. Only the first ``--`` is consumed;
    any later ``--`` stays in ``after`` (so ``run x -- claude -- y`` hands the
    child ``claude -- y`` verbatim).
    """
    argv = list(argv)
    if "--" in argv:
        i = argv.index("--")
        return argv[:i], argv[i + 1:]
    return argv, None


def build_child_env(label: str, record: Record) -> dict:
    """The child's env: a copy of the parent's plus exactly the two AC3.1 vars.

    Returns a fresh dict — ``os.environ`` is never mutated (AC3.2), so concurrent
    ``run`` invocations under different labels cannot collide on the parent env
    or on each other's child env (AC3.4).
    """
    env = dict(os.environ)
    env["CLAUDE_CONFIG_DIR"] = str(slot_dir(label))
    env["CLAUDE_CODE_OAUTH_TOKEN"] = record.oat
    return env


def looks_like_auth_failure(text: str) -> bool:
    """Best-effort, conservative auth-failure detector (AC3.6).

    Grounded in a live dead-token probe (CLI v2.1.197), whose stdout was
    ``Failed to authenticate. API Error: 401 Invalid bearer token``. Kept
    conservative on purpose: a bare ``401`` only counts when it co-occurs with an
    auth word, so a non-auth HTTP 401 echoed by the child does not mis-fire the
    guidance.
    """
    low = text.lower()
    if "invalid bearer token" in low:
        return True
    if "failed to authenticate" in low:
        return True
    if "authentication_error" in low:
        return True
    if "401" in low and any(
        w in low for w in ("authenticat", "bearer", "token", "unauthorized")
    ):
        return True
    return False


def normalize_exit_code(returncode: int) -> int:
    """Map a ``Popen.returncode`` to a shell exit code.

    A child killed by signal N reports ``-N``; the shell convention is ``128+N``.
    A normal exit passes through unchanged.
    """
    if returncode < 0:
        return 128 + (-returncode)
    return returncode


# --- the real subprocess boundary (mocked in tests) ------------------------

def _pump_and_capture(proc: subprocess.Popen) -> str:
    """Stream the child's piped stdout to ours verbatim; return a bounded tail.

    Bytes are written through and flushed as they arrive (live passthrough), so
    a downstream pipe consumer sees them in real time; only the last
    :data:`_TAIL_MAX` bytes are retained for the AC3.6 scan.
    """
    out = sys.stdout.buffer
    tail = bytearray()
    try:
        while True:
            chunk = proc.stdout.read(4096)
            if not chunk:
                break
            out.write(chunk)
            out.flush()
            tail += chunk
            if len(tail) > _TAIL_MAX:
                del tail[:-_TAIL_MAX]
    finally:
        proc.stdout.close()
    proc.wait()
    return tail.decode("utf-8", "replace")


def _real_launcher(cmd: Sequence[str], env: dict) -> Tuple[int, Optional[str]]:
    """Launch ``cmd`` with ``env``; inherit stdin+stderr, TTY-aware tee on stdout.

    Forwards terminal signals to the child while waiting (so Ctrl-C reaches the
    child and we never kill a live session ourselves — zero-shell-disruption).
    """
    stdout_is_tty = sys.stdout.isatty()
    popen_kwargs = {"env": env}
    if not stdout_is_tty:
        popen_kwargs["stdout"] = subprocess.PIPE  # tee so we can scan (AC3.6)

    proc = subprocess.Popen(list(cmd), **popen_kwargs)

    installed = {}

    def _forward(signum, _frame):
        try:
            proc.send_signal(signum)
        except (ProcessLookupError, OSError):
            pass

    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        try:
            installed[sig] = signal.signal(sig, _forward)
        except (ValueError, OSError):
            pass  # not in main thread / unsupported — terminal still signals the group
    try:
        if stdout_is_tty:
            proc.wait()
            captured = None
        else:
            captured = _pump_and_capture(proc)
    finally:
        for sig, handler in installed.items():
            try:
                signal.signal(sig, handler)
            except (ValueError, OSError):
                pass
    return proc.returncode, captured


# --- the command -----------------------------------------------------------

def run_command(
    label: str,
    cmd: Sequence[str],
    *,
    store: Optional[Store] = None,
    io: Optional[IO] = None,
    launcher: Optional[Launcher] = None,
) -> int:
    """Run ``cmd`` under ``label``'s injected credential. Returns an exit code.

    AC3.5: an unknown label fails here, before any subprocess is launched, with a
    clear error listing the available labels. AC3.3: the stored ``email`` is
    echoed (no live lookup). AC3.6: a child that exits with a recognizable
    auth-failure signal triggers re-mint guidance; no automatic revoke/re-mint.
    """
    store = store if store is not None else Store()
    io = io if io is not None else ConsoleIO()
    launcher = launcher if launcher is not None else _real_launcher

    # AC3.5 — resolve the label BEFORE touching any subprocess.
    record = store.read(label)
    if record is None:
        labels = store.labels()
        if labels:
            io.error(
                f"no slot named {label!r}. Available labels: {', '.join(labels)}"
            )
        else:
            io.error(
                f"no slot named {label!r}. No slots exist yet — run 'cas add' first."
            )
        return NO_SUCH_LABEL

    # AC3.3 — identity echo from the stored binding (no live email lookup). Goes
    # to stderr so a piped child's stdout stays clean for downstream consumers.
    io.notice(f"running as {label} ({record.email})")

    # AC3.1/AC3.2 — exactly two extra vars, in the child's env only.
    child_env = build_child_env(label, record)

    try:
        returncode, captured = launcher(cmd, child_env)
    except FileNotFoundError:
        io.error(f"command not found: {cmd[0]}")
        return COMMAND_NOT_FOUND

    # AC3.6 — best-effort, auth-specific guidance; the child's own output already
    # passed through unmodified. No automatic revocation or re-mint.
    if returncode != 0 and captured and looks_like_auth_failure(captured):
        io.error(
            f"this looks like an authentication failure for {label!r} — the stored "
            f"token may be dead. To re-mint: 'cas rm {label}' then 'cas add'."
        )

    return normalize_exit_code(returncode)
