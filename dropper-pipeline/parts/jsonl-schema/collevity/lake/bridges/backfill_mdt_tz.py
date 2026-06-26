"""ONE-SHOT, DISPOSABLE tz backfill — DELETE AFTER RUNNING (AC4.4).

The Excel bridge stamps every row EDT (`-04:00`). That is correct for all ongoing
drops and all legacy rows except the handful Levi made during a **round-trip to
Colorado** (Mountain time) in mid-June 2026. This script rewrites exactly those
rows' `created_at` offset to MDT (`-06:00`), keeping the same naive wall-clock
digits (the Excel timestamp WAS the local Mountain wall-clock at capture).

It is a run-once migration, not part of the bridge — the bridge carries no tz
logic, and this file is meant to be deleted once the backfill has been applied
(Open Question 1 / DEC-023 resolved by reading the entries' own text + timestamps,
2026-06-26).

The MDT set (resolved from the entries' own text):
  * r772 (Jun 13 09:30) — at the HOME airport, outbound: still EDT → not touched.
  * r773–r779 (Jun 15 08:42 → Jun 17 14:49) — in Colorado: MDT. Confirmed by Levi's
    own notes ("timestamps for 6/15-17 here ... are MDT"; r780 at 21:01 "now EDT").
  * everything else — EDT → not touched.

The window below brackets exactly r773–r779 (no drops exist in the Jun 13 PM →
Jun 15 AM or Jun 17 14:49 → 21:01 gaps), keyed off the drop-timestamp the bridge
stored in the sidecar. Idempotent: re-running re-sets the same `-06:00` value.

Run: `python -m collevity.lake.bridges.backfill_mdt_tz` (after the bridge has run).
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from ..lake import edit_entry
from .excel import _resolve_sidecar

# Naive (Mountain wall-clock) window bracketing the Colorado-trip rows r773–r779.
_MDT_LOW = datetime(2026, 6, 15, 0, 0, 0)
_MDT_HIGH = datetime(2026, 6, 17, 15, 0, 0)  # exclusive; r780 is at 21:01
_MDT_OFFSET = "-06:00"


def _ts_from_key(key: str) -> datetime:
    """Recover the drop-timestamp from a sidecar key (`iso` or `iso#rowindex`)."""
    iso = key.split("#", 1)[0]
    return datetime.fromisoformat(iso)


def backfill(
    *,
    sidecar_path: str | os.PathLike | None = None,
    pool_path: str | os.PathLike | None = None,
) -> int:
    """Stamp MDT-window legacy rows `-06:00`; return how many were rewritten."""
    sidecar = _resolve_sidecar(sidecar_path, pool_path)
    if not sidecar.exists():
        raise FileNotFoundError(
            f"no sidecar at {sidecar}; run the Excel bridge before the tz backfill"
        )
    state: dict[str, dict] = json.loads(sidecar.read_text(encoding="utf-8"))

    changed = 0
    for key, val in state.items():
        ts = _ts_from_key(key)
        if _MDT_LOW <= ts < _MDT_HIGH:
            edit_entry(
                val["id"],
                {"created_at": ts.isoformat() + _MDT_OFFSET},
                pool_path=pool_path,
            )
            changed += 1
    return changed


def _main() -> int:
    n = backfill()
    print(f"tz backfill: stamped {n} MDT-window row(s) -06:00. Safe to delete this script now.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
