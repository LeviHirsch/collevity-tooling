#!/usr/bin/env python3
"""Read a single local day out of the lake — the seam's read *consumer*.

A first-class home for what used to be /checkin's `read_dropper_day.py` shim.
Per DEC-019 the consumer owns the freshness composition: this CLI calls
`sync_sources()` (pull any new/edited external-capture rows into the lake — the
Excel bridge in Phase 2) and THEN `read_day()` (a pure, side-effect-free read).
The seam stays Excel-blind; the bridge is imported lazily inside `sync_sources`.

This module is **location-agnostic**: it never hardcodes a lake path. Resolution
is the seam's own order — explicit `pool_path` (not used here) → `COLLEVITY_LAKE`
env var → package default. A real deployment points `COLLEVITY_LAKE` at the live
lake outside the code tree; that pointer is deployment config, owned by the
caller (e.g. /checkin's launcher), not baked in here.

Usage:
    python -m collevity.lake.cli [YYYY-MM-DD]      # defaults to today
    collevity-read-day [YYYY-MM-DD]                # installed console script

Output is `[HH:MM] text` per entry — the format /checkin's extraction step
already parses — preceded by a header and a one-line sync report on stderr.
"""
from __future__ import annotations

import datetime
import sys

from collevity.lake import read_day, sync_sources


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    target = argv[0] if argv else datetime.date.today().isoformat()

    # Freshness composition (DEC-019): pull, then read. A failed pull (e.g. Excel
    # holds a lock) is non-fatal — warn and read the lake as-is rather than block
    # /checkin; the lake is still a superset of what the failed source would add.
    try:
        res = sync_sources()
        print(
            f"(sync: {res.entries_ingested} written (new or edited) "
            f"from {res.sources_synced} source(s))",
            file=sys.stderr,
        )
    except Exception as e:  # noqa: BLE001 — read must not be blocked by a flaky pull
        print(f"WARN: sync_sources failed ({e}); reading possibly-stale lake.", file=sys.stderr)

    rows = read_day(target)  # pure read; pool resolved via COLLEVITY_LAKE / default
    print(f"# Lake entries for {target} ({len(rows)} found)\n")
    for r in rows:
        print(f"[{r['time']}] {r['text'].strip()}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
