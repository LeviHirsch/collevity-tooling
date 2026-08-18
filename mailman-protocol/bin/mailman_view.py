#!/usr/bin/env python3
"""Mailman published session views — what a session says about itself.

Each live session keeps one small published view in the shared cache and keeps
it current. Those views are the address space: a sender (or Haiku, acting as
switchboard) reads them and decides who is worth telling. There is no folder
address, no assigned name, and no subject subscription — T6 died settling that.

NOT A HOOK. This module is free to raise and to exit non-zero, unlike
`mailman_check.py`, `mailman_register.py`, and `mailman_publish.py`, which are
installed into `settings.json` and must exit 0 in silence. The hooks call
`touch()` here inside their own fail-open wrapper; do not push that posture
down into this file.

WHAT A VIEW CARRIES (T18 decision, 2026-08-17)

  Mechanical — written by the hooks, on every trigger:
    session_id, cwd, kind, updated_at

  Semantic — written by the session's own agent, when things change:
    topic       one-line title for the whole session
    recap       a general description of what has happened
    working_on  the short current focus
    reported_at when the semantic fields last changed

The split matters. `updated_at` is last activity (a prompt, a turn ending, or
a report). `reported_at` standing still while `updated_at` moves means the
session has been busy but has not said what it is doing lately. Neither stamp
is liveness — a session left open for days is stale and fully alive.

WHY ONE FILE PER SESSION

The roster (`mailman_register.py`) is append-only JSONL because many sessions
write one shared file. Views are the opposite shape: each session owns its own
file and rewrites it, so there is nothing to contend over, no reduction pass to
find the newest record, and last-write time is just the file's own timestamp.
Writes go through a temp file and `os.replace`, so a reader never catches a
half-written view.

Under `cache/` deliberately, same lifetime rule as the roster:
`~/.collevity/README.md` declares that dir disposable, and a lost view costs at
most one refresh on the session's next turn. Notes live at `~/.collevity/mailman/`
because an unread note is real data loss (T1).

AGE IS NOT LIVENESS

`age_seconds()` reports how long since a view last moved. That is last
activity, not whether the session is still open. Do not refuse a recipient
because the view is old — a session left idle for days is stale and fully
alive. An ended-session signal does not exist yet.

Environment:
  MAILMAN_CACHE       — disposable state dir. Default `~/.collevity/cache/mailman`.
  CLAUDE_SESSION_ID   — fallback identity for `report` (see resolve_session_id).
  GROK_SESSION_ID     — same, for Grok.

CLI (the self-report path — this is what an agent calls):
  python3 bin/mailman_view.py report --topic "..." --working-on "..."
  python3 bin/mailman_view.py show [--session ID] [--json]
  python3 bin/mailman_view.py list [--json]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_CACHE = Path.home() / ".collevity" / "cache" / "mailman"
VIEWS_DIRNAME = "views"

_SESSION_ENV = ("CLAUDE_SESSION_ID", "GROK_SESSION_ID")

# Sorts before every real timestamp, so an unparseable `updated_at` reads as
# maximally stale instead of crashing whoever is scanning views.
_EPOCH = datetime.min.replace(tzinfo=timezone.utc)


class ViewError(RuntimeError):
    """Raised when a view cannot be identified or written. Hooks catch this."""


def cache_dir() -> Path:
    return Path(os.environ.get("MAILMAN_CACHE") or DEFAULT_CACHE)


def views_dir() -> Path:
    return cache_dir() / VIEWS_DIRNAME


def view_path(session_id: str) -> Path:
    """One file per session. The id is used verbatim, so it must be a bare name.

    Session ids are uuids in both harnesses; anything carrying a path separator
    is a malformed payload, not a session, and must not be allowed to steer the
    write out of the views dir.
    """
    if not session_id or "/" in session_id or "\\" in session_id or session_id in (".", ".."):
        raise ViewError(f"unusable session id: {session_id!r}")
    return views_dir() / f"{session_id}.json"


def _now() -> str:
    return datetime.now().astimezone().isoformat()


def _parsed_time(value: object) -> datetime:
    if not isinstance(value, str) or not value:
        return _EPOCH
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return _EPOCH
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class View:
    """One session's published account of itself."""

    session_id: str
    cwd: str = ""
    kind: str = ""
    updated_at: str = ""
    topic: str = ""
    recap: str = ""
    working_on: str = ""
    reported_at: str = ""

    @property
    def described(self) -> bool:
        """True once the session has said anything about itself."""
        return bool(self.topic or self.recap or self.working_on)


def _from_dict(data: dict) -> View:
    """Tolerant read: unknown keys are dropped, missing ones default, and a
    non-string value is coerced rather than fatal. A view is a cache entry, and
    refusing to read the whole roster of sessions because one file drifted in
    shape would be the wrong trade."""
    fields = View.__dataclass_fields__
    clean = {}
    for key in fields:
        if key in data:
            value = data[key]
            clean[key] = value if isinstance(value, str) else ""
    session_id = clean.get("session_id") or ""
    if not session_id:
        raise ViewError("view has no session_id")
    clean["session_id"] = session_id
    return View(**clean)


def write_view(view: View) -> Path:
    """Replace this session's view atomically.

    Temp file in the same dir then `os.replace`, so a concurrent reader sees
    either the old view or the new one and never a truncated file.
    """
    target = view_path(view.session_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(asdict(view), ensure_ascii=False, indent=2) + "\n"

    handle, tmp_name = tempfile.mkstemp(dir=str(target.parent), prefix=".view-", suffix=".tmp")
    tmp = Path(tmp_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as fh:
            fh.write(payload)
        os.replace(tmp, target)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return target


def read_view(session_id: str) -> View | None:
    """This session's view, or None when it has never published one.

    Reading is total: an unusable id, a missing file, or a garbled one all read
    as "nothing published" rather than raising. Writing is the strict direction
    — `view_path` still refuses a bad id there, where it would matter.
    """
    try:
        raw = view_path(session_id).read_text(encoding="utf-8")
    except ViewError:
        return None
    except (FileNotFoundError, NotADirectoryError, IsADirectoryError, PermissionError, UnicodeDecodeError):
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    try:
        return _from_dict(data)
    except ViewError:
        return None


def read_all_views(directory: Path | None = None) -> list[View]:
    """Every readable view, freshest first. Unreadable files are skipped."""
    target = directory or views_dir()
    try:
        entries = sorted(target.iterdir())
    except (FileNotFoundError, NotADirectoryError, PermissionError):
        return []

    views: list[View] = []
    for entry in entries:
        if entry.suffix != ".json" or not entry.is_file():
            continue
        found = read_view(entry.stem)
        if found is not None:
            views.append(found)
    views.sort(key=lambda v: _parsed_time(v.updated_at), reverse=True)
    return views


def age_seconds(view: View, now: datetime | None = None) -> float:
    """Seconds since this view last moved. Last activity, not liveness — see
    the module docstring; do not treat a large number as a dead session."""
    reference = now or datetime.now(timezone.utc)
    return (reference - _parsed_time(view.updated_at)).total_seconds()


def touch(session_id: str, cwd: str = "", kind: str = "") -> View:
    """Refresh the mechanical half, preserving whatever the session has said.

    This is the hook path: it runs on every trigger and must never clobber
    topic/recap/working_on, which only the session's own agent writes.
    """
    existing = read_view(session_id)
    if existing is None:
        existing = View(session_id=session_id)
    updated = replace(
        existing,
        cwd=cwd or existing.cwd,
        kind=kind or existing.kind,
        updated_at=_now(),
    )
    write_view(updated)
    return updated


def report(
    session_id: str,
    topic: str | None = None,
    recap: str | None = None,
    working_on: str | None = None,
) -> View:
    """Write the semantic half. Only the fields passed are changed.

    Passing an empty string clears a field; passing None leaves it alone. That
    distinction is why these are Optional rather than defaulting to "".
    """
    if topic is None and recap is None and working_on is None:
        raise ViewError("report needs at least one of --topic/--recap/--working-on")

    existing = read_view(session_id) or View(session_id=session_id)
    stamp = _now()
    updated = replace(
        existing,
        topic=existing.topic if topic is None else topic,
        recap=existing.recap if recap is None else recap,
        working_on=existing.working_on if working_on is None else working_on,
        reported_at=stamp,
        updated_at=stamp,
    )
    write_view(updated)
    return updated


def resolve_session_id(explicit: str | None = None, cwd: str | None = None) -> str:
    """Which session am I? Explicit id, then environment, then this directory.

    The last step is a convenience for an agent that cannot see its own id, and
    it is deliberately not the folder addressing T6 died on — this picks which
    of *my own* files to write, never who receives a note. It refuses when the
    directory holds more than one session rather than guessing, because guessing
    would let one session overwrite another's view.
    """
    if explicit:
        return explicit
    for name in _SESSION_ENV:
        value = os.environ.get(name)
        if value:
            return value

    here = str(Path(cwd or os.getcwd()).expanduser().resolve())
    matches = [v for v in read_all_views() if v.cwd and str(Path(v.cwd).expanduser().resolve()) == here]
    if len(matches) == 1:
        return matches[0].session_id
    if not matches:
        raise ViewError(
            f"no session id: pass --session, or set {_SESSION_ENV[0]}; "
            f"no published view sits at {here}"
        )
    raise ViewError(
        "no session id: pass --session — "
        f"{len(matches)} sessions publish from {here}: "
        + ", ".join(v.session_id for v in matches)
    )


def harness_kind(payload: dict) -> str:
    """'claude-session' | 'grok-session' from either envelope shape.

    Grok reaches this install through Claude-settings hook compatibility and
    sends camelCase; `sessionId` without `session_id` is the decisive marker.
    Mirrors `mailman_register.py`'s detection — T17 folds the two copies into
    one shared helper once both hooks are on main.
    """
    forced = (os.environ.get("COLLEVITY_HOOK_SOURCE") or "").strip().lower()
    if forced in ("grok-hook", "grok"):
        return "grok-session"
    if forced in ("claude-hook", "claude"):
        return "claude-session"
    if "sessionId" in payload and "session_id" not in payload:
        return "grok-session"
    if os.environ.get("GROK_SESSION_ID") or os.environ.get("GROK_HOOK_EVENT"):
        return "grok-session"
    return "claude-session"


def _print_view(view: View, as_json: bool) -> None:
    if as_json:
        print(json.dumps(asdict(view), ensure_ascii=False))
        return
    print(f"{view.session_id}  {view.kind}  {view.cwd}")
    print(f"  updated  {view.updated_at or '(never)'}")
    print(f"  reported {view.reported_at or '(never)'}")
    if view.topic:
        print(f"  topic    {view.topic}")
    if view.working_on:
        print(f"  working  {view.working_on}")
    if view.recap:
        print(f"  recap    {view.recap}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Publish and read mailman session views.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_report = sub.add_parser("report", help="say what this session is doing")
    p_report.add_argument("--session", help="session id (default: env, then this directory)")
    p_report.add_argument("--topic", help="one-line title for the whole session")
    p_report.add_argument("--recap", help="general description of what has happened")
    p_report.add_argument("--working-on", dest="working_on", help="the current focus")

    p_show = sub.add_parser("show", help="print one view")
    p_show.add_argument("--session", help="session id (default: env, then this directory)")
    p_show.add_argument("--json", action="store_true", help="machine-readable output")

    p_list = sub.add_parser("list", help="print every published view, freshest first")
    p_list.add_argument("--json", action="store_true", help="machine-readable output")

    args = parser.parse_args(argv)

    if args.command == "list":
        views = read_all_views()
        if args.json:
            print(json.dumps([asdict(v) for v in views], ensure_ascii=False))
            return 0
        if not views:
            print("no sessions have published a view", file=sys.stderr)
            return 1
        for view in views:
            _print_view(view, as_json=False)
        return 0

    try:
        session_id = resolve_session_id(args.session)
    except ViewError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.command == "report":
        try:
            updated = report(
                session_id,
                topic=args.topic,
                recap=args.recap,
                working_on=args.working_on,
            )
        except ViewError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        _print_view(updated, as_json=False)
        return 0

    found = read_view(session_id)
    if found is None:
        print(f"no view published for {session_id}", file=sys.stderr)
        return 1
    _print_view(found, as_json=args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
