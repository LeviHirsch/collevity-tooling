#!/usr/bin/env python3
"""Mailman recipient resolution — a directory in, a session id out.

This is the address space. A sender picks a recipient by *project directory*;
the note that gets stored carries the resolved `session_id` plus the cwd it was
chosen by (T6). Everything here reads the roster `mailman_register.py` writes.

NOT A HOOK. Unlike `mailman_check.py` and `mailman_register.py`, this module is
never installed into `settings.json` and never touches stdout on a live prompt
path, so it is free to raise and to exit non-zero. Callers that *are* hooks own
their own fail-open behaviour; do not push it down here.

THE THREE DECISIONS (2026-08-16, see T6)

1. **No liveness filter.** Every session that ever registered stays resolvable,
   ranked by most-recent registration. The roster has no SessionEnd hook, so
   "live" is not knowable from it — and T16 drains queued notes at session
   start, which makes addressing a dormant session correct rather than a black
   hole. Staleness policy belongs wherever retention lands, not here.

2. **Newest wins, ambiguity surfaced.** `resolve()` picks the most recently
   registered match and hands back the full candidate list beside it, so the
   send side (T3) can warn or offer a pick. Resolution never blocks on a tie
   and never hides that there was one.

3. **Exact, else nearest descendant.** The address is normalized and compared
   against normalized session cwds. Exact matches short-circuit; only when
   there are none does an address match sessions sitting *below* it, nearest
   first — `…/collevity-tooling` reaching a session in
   `…/collevity-tooling/mailman-protocol`. Dev worktrees nest sessions far too
   deep for exact-only to be usable.

   Deliberately NOT the reverse: an address *below* a session's cwd does not
   match that session. That direction was not decided, and guessing it would
   let a note aimed at one subproject land in a parent that never asked for it.

Environment:
  MAILMAN_CACHE — disposable state dir. Default `~/.collevity/cache/mailman`.

CLI (verification, not a hook):
  python3 bin/mailman_resolve.py [DIR] [--all] [--json] [--exclude SESSION_ID]
  Exit 0 with the resolved session id on stdout, or exit 1 when nothing matches.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_CACHE = Path.home() / ".collevity" / "cache" / "mailman"
ROSTER_NAME = "roster.jsonl"

# Sorts before every real timestamp, so an unparseable `registered_at` loses
# every recency comparison instead of crashing resolution.
_EPOCH = datetime.min.replace(tzinfo=timezone.utc)


def cache_dir() -> Path:
    return Path(os.environ.get("MAILMAN_CACHE") or DEFAULT_CACHE)


def roster_path() -> Path:
    return cache_dir() / ROSTER_NAME


def normalize(path: str | Path) -> str:
    """A comparable absolute path. Both sides of every match go through this.

    `resolve()` is non-strict, so a session whose directory has since been
    deleted still normalizes rather than raising — the roster outlives the
    directories it names.
    """
    return str(Path(path).expanduser().resolve())


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


def read_roster(path: Path | None = None) -> list[dict]:
    """Every well-formed roster line, oldest first.

    A torn or truncated line is skipped rather than fatal: the roster lives in
    a directory `~/.collevity/README.md` declares disposable, and refusing to
    resolve anything because one line got garbled would be the wrong trade.
    """
    target = path or roster_path()
    try:
        raw = target.read_text(encoding="utf-8")
    except (
        FileNotFoundError,
        NotADirectoryError,
        IsADirectoryError,
        PermissionError,
        UnicodeDecodeError,
    ):
        return []

    records = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def latest_by_session(records: list[dict]) -> list[dict]:
    """One record per session — the newest. `SessionStart` fires on resume and
    clear as well as startup, so a session legitimately has several lines."""
    newest: dict[str, dict] = {}
    for record in records:
        session_id = record.get("session_id")
        cwd = record.get("cwd")
        if not isinstance(session_id, str) or not session_id:
            continue
        if not isinstance(cwd, str) or not cwd:
            continue
        prior = newest.get(session_id)
        if prior is None or _parsed_time(record.get("registered_at")) >= _parsed_time(
            prior.get("registered_at")
        ):
            newest[session_id] = record
    return list(newest.values())


@dataclass(frozen=True)
class Candidate:
    """One session that could receive a note sent to the queried directory."""

    session_id: str
    cwd: str
    kind: str
    registered_at: str
    #: 0 when the session sits exactly at the address, else how many path
    #: segments below it. Only ever non-zero on a descendant fallback.
    depth: int

    @property
    def exact(self) -> bool:
        return self.depth == 0


@dataclass(frozen=True)
class Resolution:
    """The chosen recipient, plus everything the sender needs to second-guess it."""

    session_id: str
    cwd: str
    #: Every match at the same quality as the chosen one, best first.
    candidates: list[Candidate] = field(default_factory=list)

    @property
    def ambiguous(self) -> bool:
        return len(self.candidates) > 1

    @property
    def exact(self) -> bool:
        return bool(self.candidates) and self.candidates[0].exact


def _depth_below(address: str, session_cwd: str) -> int | None:
    """Segments from `address` down to `session_cwd`, or None if not below it."""
    if session_cwd == address:
        return 0
    try:
        relative = Path(session_cwd).relative_to(address)
    except ValueError:
        return None
    return len(relative.parts)


def candidates(
    cwd: str | Path,
    records: list[dict] | None = None,
    exclude: str | None = None,
) -> list[Candidate]:
    """Sessions addressable at `cwd`, best first.

    Exact matches short-circuit: when any session sits exactly at the address,
    descendants are not considered at all. Otherwise the nearest descendants
    win. Within one quality tier the most recently registered session leads.
    """
    address = normalize(cwd)
    roster = latest_by_session(records if records is not None else read_roster())

    matches: list[Candidate] = []
    for record in roster:
        session_id = record["session_id"]
        if exclude and session_id == exclude:
            continue
        session_cwd = normalize(record["cwd"])
        depth = _depth_below(address, session_cwd)
        if depth is None:
            continue
        matches.append(
            Candidate(
                session_id=session_id,
                cwd=session_cwd,
                kind=str(record.get("kind") or ""),
                registered_at=str(record.get("registered_at") or ""),
                depth=depth,
            )
        )

    if any(match.exact for match in matches):
        matches = [match for match in matches if match.exact]

    # Nearest first, then newest; session_id only to keep ties deterministic.
    matches.sort(
        key=lambda m: (m.depth, -_parsed_time(m.registered_at).timestamp(), m.session_id)
    )
    return matches


def resolve(
    cwd: str | Path,
    records: list[dict] | None = None,
    exclude: str | None = None,
) -> Resolution | None:
    """The recipient for a note addressed to `cwd`, or None if nothing matches."""
    found = candidates(cwd, records=records, exclude=exclude)
    if not found:
        return None
    return Resolution(
        session_id=found[0].session_id, cwd=found[0].cwd, candidates=found
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Resolve a project directory to a mailman recipient."
    )
    parser.add_argument(
        "cwd", nargs="?", default=os.getcwd(), help="directory to address (default: .)"
    )
    parser.add_argument("--exclude", help="session id to leave out (usually your own)")
    parser.add_argument(
        "--all", action="store_true", help="list every candidate, not just the pick"
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    resolution = resolve(args.cwd, exclude=args.exclude)
    if resolution is None:
        if args.json:
            print(json.dumps({"session_id": None, "candidates": []}))
        else:
            print(f"no session registered at or below {normalize(args.cwd)}", file=sys.stderr)
        return 1

    if args.json:
        print(
            json.dumps(
                {
                    "session_id": resolution.session_id,
                    "cwd": resolution.cwd,
                    "ambiguous": resolution.ambiguous,
                    "exact": resolution.exact,
                    "candidates": [vars(c) for c in resolution.candidates],
                },
                ensure_ascii=False,
            )
        )
        return 0

    if args.all:
        for candidate in resolution.candidates:
            marker = "*" if candidate.session_id == resolution.session_id else " "
            where = "exact" if candidate.exact else f"+{candidate.depth}"
            print(
                f"{marker} {candidate.session_id}  {where:>6}  "
                f"{candidate.kind}  {candidate.registered_at}  {candidate.cwd}"
            )
    else:
        print(resolution.session_id)

    if resolution.ambiguous and not args.all:
        print(
            f"note: {len(resolution.candidates)} sessions match; "
            f"picked the most recently registered",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
