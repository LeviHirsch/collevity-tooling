"""`sync_sources` — the pull-ingest coordination boundary (AC5.1, DEC-018).

`sync_sources()` brings the lake current from **pull-based** external capture
sources before a read. Native **push** surfaces write directly via
`append_entry` and need no sync. Pull-based capture is a *permanent* design
need, so this seam is permanent — but its registered ingesters come and go.

Freshness is a **consumer-composition contract** (DEC-019): `read_day` makes no
standalone freshness guarantee, so a consumer needing current data composes
`sync_sources()` then `read_day()`. Staleness is neither surfaced nor enforced
here.

PHASE 1 SCOPE: this is the boundary only — **no ingesters are registered yet**,
so `sync_sources()` is a well-defined no-op that reports zero work. The Excel
bridge (Phase 2 / AC4–AC5.2) becomes this seam's single v1 ingester; it is
wired in *there*, not here. Per DEC-018/AC5.2 there is deliberately **no
multi-source registry in v1** — do not build one. When Phase 2 lands, its one
ingester call goes at the marked extension point below.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SyncResult:
    """Outcome of a `sync_sources` run."""

    sources_synced: int
    entries_ingested: int


def sync_sources() -> SyncResult:
    """Bring pull-based sources current. No-op in Phase 1 (no ingesters yet).

    Returns a zero-work result. The boundary exists so consumers can already
    write the `sync_sources(); read_day()` composition (DEC-019) — it simply has
    nothing to pull until the Excel bridge registers under it in Phase 2.
    """
    # --- Phase 2 extension point -------------------------------------------
    # The single v1 ingester (the Excel bridge, AC4/AC5.2) runs here. No
    # registry — one explicit call. Until then there is nothing to sync.
    # -----------------------------------------------------------------------
    return SyncResult(sources_synced=0, entries_ingested=0)
