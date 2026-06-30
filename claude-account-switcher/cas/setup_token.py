"""Drive ``claude setup-token`` and verify the captured oat (spec AC2.1/AC2.4/AC2.5).

Three pieces, split so the Phase 2 tests can mock the subprocess boundary while
the parsing logic stays directly unit-testable (DEC-015):

- :func:`find_url` / :func:`find_oat` / :func:`strip_ansi` — pure scrapers over
  the bytes ``setup-token`` prints (verified to print BOTH the OAuth URL, while
  waiting, and the ``sk-ant-oat01-…`` token, after auth, to stdout — DEC-010).
- :class:`SetupTokenMinter` — launches the binary in a throwaway isolated
  ``CLAUDE_CONFIG_DIR`` over a **pty** (so the CLI sees a real terminal and does
  not gate/block-buffer its output — DEC-015), streams its output, hands the URL
  to a callback the moment it appears, and returns the oat once it appears.
- :func:`liveness_check` / :func:`parse_auth_status` — AC2.5: run
  ``CLAUDE_CODE_OAUTH_TOKEN=<oat> claude auth status`` in a fresh config dir and
  confirm ``loggedIn: true`` + ``authMethod: "oauth_token"``.

The live calls here hit the real CLI and a real browser auth — the genuine mint
is a manual step. Automated tests mock :class:`SetupTokenMinter` and
:func:`liveness_check`; they exercise the pure helpers directly.
"""

from __future__ import annotations

import os
import pty
import re
import select
import shutil
import subprocess
import tempfile
from typing import Callable, Optional

from .errors import MintError

#: The claude binary name; overridable for tests / non-PATH installs.
CLAUDE_BIN = os.environ.get("CAS_CLAUDE_BIN", "claude")

# Strip terminal control sequences a pty may interleave before we scan a line.
_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
# The two scraped artifacts have disjoint, unmistakable prefixes, so order of
# arrival on the shared stdout stream does not confuse them.
_URL_RE = re.compile(r"https?://[^\s\"'<>]+")
_OAT_RE = re.compile(r"sk-ant-oat01-[A-Za-z0-9._\-]+")


def strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def find_url(text: str) -> Optional[str]:
    """First OAuth URL in ``text`` (ANSI-stripped), or ``None``."""
    m = _URL_RE.search(strip_ansi(text))
    return m.group(0) if m else None


def find_oat(text: str) -> Optional[str]:
    """First ``sk-ant-oat01-…`` token in ``text`` (ANSI-stripped), or ``None``."""
    m = _OAT_RE.search(strip_ansi(text))
    return m.group(0) if m else None


class SetupTokenMinter:
    """Run ``claude setup-token`` and capture the URL (early) then the oat (late).

    ``mint`` is long-lived by nature: it surfaces the URL, then blocks reading the
    pty while the human authorizes in the browser, then returns once the token is
    printed. The temporary ``CLAUDE_CONFIG_DIR`` is isolated and removed after.
    """

    def __init__(self, claude_bin: str = CLAUDE_BIN) -> None:
        self.claude_bin = claude_bin

    def mint(self, on_url: Callable[[str], None]) -> str:
        """Launch the subprocess; call ``on_url(url)`` once, return the oat.

        Raises :class:`MintError` if the binary cannot be launched or it exits
        without ever printing an oat.
        """
        config_dir = tempfile.mkdtemp(prefix="cas-setup-")
        # Don't leak a stray CLAUDE_CODE_OAUTH_TOKEN into the mint — setup-token
        # produces a fresh credential; an inherited one would only confuse it.
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CODE_OAUTH_TOKEN"}
        env["CLAUDE_CONFIG_DIR"] = config_dir

        master, slave = pty.openpty()
        try:
            proc = subprocess.Popen(
                [self.claude_bin, "setup-token"],
                stdin=slave,
                stdout=slave,
                stderr=slave,
                env=env,
                close_fds=True,
            )
        except FileNotFoundError as exc:
            os.close(master)
            os.close(slave)
            shutil.rmtree(config_dir, ignore_errors=True)
            raise MintError(
                f"could not launch '{self.claude_bin} setup-token': {exc}"
            ) from exc
        os.close(slave)  # the child holds the only writer now

        oat: Optional[str] = None
        url_seen = False
        buf = ""
        try:
            while oat is None:
                try:
                    select.select([master], [], [])
                    data = os.read(master, 4096)
                except OSError:
                    break  # pty closed when the child exited
                if not data:
                    break
                buf += data.decode("utf-8", "replace")
                *lines, buf = buf.split("\n")  # keep the incomplete remainder
                for line in lines:
                    if not url_seen:
                        url = find_url(line)
                        if url:
                            url_seen = True
                            on_url(url)
                    found = find_oat(line)
                    if found:
                        oat = found
                        break
            if oat is None:  # scan whatever trailed without a final newline
                if not url_seen:
                    url = find_url(buf)
                    if url:
                        url_seen = True
                        on_url(url)
                oat = find_oat(buf)
        finally:
            os.close(master)
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
            shutil.rmtree(config_dir, ignore_errors=True)

        if oat is None:
            raise MintError(
                "claude setup-token exited without printing an oat token"
            )
        return oat


def parse_auth_status(stdout: str, stderr: str) -> bool:
    """True iff the output shows ``loggedIn: true`` AND an oauth-token method.

    Tolerant of JSON or human formatting (DEC-001 reports ``loggedIn:true,
    authMethod:oauth_token``); both signals must be present.
    """
    text = f"{stdout}\n{stderr}"
    logged_in = re.search(r'"?loggedIn"?\s*[:=]\s*true', text, re.IGNORECASE) is not None
    oauth = re.search(r"oauth[_-]?token", text, re.IGNORECASE) is not None
    return logged_in and oauth


def liveness_check(oat: str, claude_bin: str = CLAUDE_BIN) -> bool:
    """AC2.5: confirm ``oat`` authenticates as an oauth token in a fresh dir.

    Returns ``False`` (never raises) on a missing binary, timeout, or any output
    that does not clearly show a logged-in oauth-token session.
    """
    config_dir = tempfile.mkdtemp(prefix="cas-live-")
    env = dict(os.environ)
    env["CLAUDE_CONFIG_DIR"] = config_dir
    env["CLAUDE_CODE_OAUTH_TOKEN"] = oat
    try:
        proc = subprocess.run(
            [claude_bin, "auth", "status"],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    finally:
        shutil.rmtree(config_dir, ignore_errors=True)
    return parse_auth_status(proc.stdout, proc.stderr)
