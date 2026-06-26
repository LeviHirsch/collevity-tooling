"""Excel → JSONL bridge — the single v1 pull-ingester (AC4, AC5.2).

The legacy Dropper (`Dropper_excel.xlsm`) stays a live capture channel during the
transition. This bridge pulls its rows into the lake **through the storage seam**
(`append_entry` / `edit_entry`) — never by raw line-matching (AC4.2, DEC-005) —
and keeps a persistent sidecar so re-runs are idempotent and text edits propagate
(AC4.3). It is throwaway: deleting `bridges/` retires it with no core impact
(AC4.5). Per DEC-018/AC5.2 there is deliberately no multi-source registry — this
is one explicit ingester wired in at `lake.sync_sources`'s extension point.

What it reads (AC4.1, recorded ignore-rule protocol):
  - col D `Thing`     → entry `text`
  - col E `Timestamp` → drop-timestamp (naive datetime; the row-identity key)
  - col F `modified`  → **DELIBERATELY NOT READ.** The buggy `modified` column is
    dropped from v1 (DEC-006, DEC-011); the bridge never opens it.

Timezone (AC4.4): the bridge is **tz-dumb** — it stamps every row EDT (`-04:00`),
which is correct for all ongoing drops and all legacy rows *except* the handful
made during the mid-June Colorado trip. Those are corrected once by the disposable
`backfill_mdt_tz.py` script. The bridge itself carries **no** tz logic.

Row identity (AC4.2, DEC-016): there is exactly one Dropper file, so row order is
stable across runs. The sidecar keys each row by its drop-timestamp; on the (in
practice impossible) sub-second collision, the colliding rows fall back to a
`timestamp#rowindex` key — the row-index tiebreaker DEC-016 keeps as
belt-and-suspenders. A row with no usable timestamp **fails the whole run loudly**
(no partial ingest).

Config (env, with dev-friendly defaults):
  - COLLEVITY_DROPPER_XLSM → the .xlsm path (default: the live iCloud Dropper)
  - COLLEVITY_LAKE         → the lake file; the sidecar lives beside it
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from ..lake import _resolve_pool, append_entry, edit_entry

# --- config / locations -----------------------------------------------------

_XLSM_ENV = "COLLEVITY_DROPPER_XLSM"
_DEFAULT_XLSM = (
    Path.home()
    / "Library/Mobile Documents/com~apple~CloudDocs/00_COLLEVITY/Dropper_excel.xlsm"
)
_SHEET = "Sheet1"
_SOURCE = "dropper-excel"  # DEC-007
_EDT_OFFSET = "-04:00"  # bridge stamps EDT for every row (AC4.4); backfill fixes MDT

# 0-based column indexes within a values_only row tuple.
_COL_TEXT = 3  # D = Thing
_COL_TS = 4  # E = Timestamp
# col F (modified) is index 5 — intentionally never referenced (AC4.1).


def _resolve_xlsm(xlsm_path: str | os.PathLike | None) -> Path:
    if xlsm_path is not None:
        return Path(xlsm_path)
    env = os.environ.get(_XLSM_ENV)
    return Path(env) if env else _DEFAULT_XLSM


def source_present(xlsm_path: str | os.PathLike | None = None) -> bool:
    """Whether the Dropper file exists to pull from.

    `sync_sources` uses this to report honestly: no Dropper present → zero
    sources synced (the bridge is registered but has nothing to pull).
    """
    return _resolve_xlsm(xlsm_path).exists()


def _resolve_sidecar(
    sidecar_path: str | os.PathLike | None,
    pool_path: str | os.PathLike | None,
) -> Path:
    """The sidecar lives beside the lake file (DEC-022 keeps both in `_DATA`)."""
    if sidecar_path is not None:
        return Path(sidecar_path)
    return _resolve_pool(pool_path).parent / "excel-ingest-state.json"


# --- sidecar i/o (the bridge's private bookkeeping, NOT an entry field) ------

def _load_sidecar(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_sidecar(path: Path, state: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


# --- row reading + keying ----------------------------------------------------

def _read_rows(xlsm: Path) -> list[tuple[int, str, datetime]]:
    """Return `(row_index, text, timestamp)` for every data row.

    Reads ONLY cols D and E (AC4.1). Fails loudly on a row whose timestamp is
    missing or not a datetime — naming the row, before any ingest (AC4.2).
    """
    import openpyxl  # imported lazily so the core never hard-depends on it

    wb = openpyxl.load_workbook(xlsm, read_only=True, data_only=True)
    ws = wb[_SHEET]
    rows: list[tuple[int, str, datetime]] = []
    for idx, values in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        ts = values[_COL_TS] if len(values) > _COL_TS else None
        if not isinstance(ts, datetime):
            raise ValueError(
                f"{xlsm}: row {idx} has no usable drop-timestamp in col E "
                f"(got {ts!r}); aborting with no partial ingest (AC4.2)."
            )
        text = values[_COL_TEXT] if len(values) > _COL_TEXT else None
        rows.append((idx, "" if text is None else str(text), ts))
    wb.close()
    return rows


def _build_keys(rows: list[tuple[int, str, datetime]]) -> dict[int, str]:
    """Map each row_index → its stable sidecar key (AC4.2, DEC-016).

    Key = the drop-timestamp's ISO string. The row-index tiebreaker is applied
    ONLY to rows sharing an identical timestamp (in practice none, given
    microsecond precision + single-user drop frequency).
    """
    seen: dict[str, int] = {}
    for _, _, ts in rows:
        iso = ts.isoformat()
        seen[iso] = seen.get(iso, 0) + 1
    keys: dict[int, str] = {}
    for idx, _, ts in rows:
        iso = ts.isoformat()
        keys[idx] = iso if seen[iso] == 1 else f"{iso}#{idx}"
    return keys


def _created_at(ts: datetime) -> str:
    """Naive Excel wall-clock + the EDT offset (AC4.4). Backfill fixes MDT rows."""
    return ts.isoformat() + _EDT_OFFSET


# --- the ingester (runs under sync_sources, AC4.6) ---------------------------

def ingest(
    *,
    xlsm_path: str | os.PathLike | None = None,
    sidecar_path: str | os.PathLike | None = None,
    pool_path: str | os.PathLike | None = None,
) -> int:
    """Reconcile the Dropper into the lake; return entries written this run.

    Snapshot reconciliation per run (AC4.3): a row whose key is new → `append_entry`
    (record id + text snapshot in the sidecar); text changed vs the snapshot →
    `edit_entry` on the mapped id (refresh the snapshot); unchanged → skip.
    Idempotent — a no-change re-run writes nothing and returns 0 (AC4.6).

    The whole row set is read and key-validated up front, so a bad-timestamp row
    aborts the run before any write (AC4.2).
    """
    xlsm = _resolve_xlsm(xlsm_path)
    sidecar = _resolve_sidecar(sidecar_path, pool_path)

    rows = _read_rows(xlsm)  # may raise (fail-loud) before any write
    keys = _build_keys(rows)
    state = _load_sidecar(sidecar)

    written = 0
    for idx, text, ts in rows:
        key = keys[idx]
        known = state.get(key)
        if known is None:
            new_id = append_entry(
                {
                    "text": text,
                    "created_at": _created_at(ts),
                    "source": _SOURCE,
                    "author": "user",
                },
                pool_path=pool_path,
            )
            state[key] = {"id": new_id, "text": text}
            written += 1
        elif known["text"] != text:
            edit_entry(known["id"], {"text": text}, pool_path=pool_path)
            known["text"] = text
            written += 1
        # unchanged → skip

    _save_sidecar(sidecar, state)
    return written


def _main() -> int:
    n = ingest()
    print(f"excel bridge: {n} entr{'y' if n == 1 else 'ies'} written this run")
    return 0


if __name__ == "__main__":  # manual run: python -m collevity.lake.bridges.excel
    raise SystemExit(_main())
