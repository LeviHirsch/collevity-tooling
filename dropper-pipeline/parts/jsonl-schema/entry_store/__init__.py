"""Collevity Entry Store — logical entry schema + thin storage seam (Phase 1).

The public surface IS the seam (AC2.3, DEC-005). Import these; do not read or
write the JSONL pool directly:

    from entry_store import append_entry, edit_entry, read_day, sync_sources

- append_entry(entry)        → mint id, append one line, return the id   (AC2.1)
- edit_entry(id, changes)    → in-place correction, no revision history  (AC2.2)
- read_day(day)              → pure read, {text, time} per local-day entry (AC3)
- sync_sources()             → pull-ingest boundary (no ingesters in v1)  (AC5.1)

Schema contract: SCHEMA.md.  validate()/SchemaError are exported for callers
that want to check an entry before handing it to the seam.
"""

from __future__ import annotations

from .ids import mint_id
from .schema import SchemaError, validate
from .store import append_entry, edit_entry, read_day
from .sync import SyncResult, sync_sources

__all__ = [
    "append_entry",
    "edit_entry",
    "read_day",
    "sync_sources",
    "SyncResult",
    "validate",
    "SchemaError",
    "mint_id",
]
