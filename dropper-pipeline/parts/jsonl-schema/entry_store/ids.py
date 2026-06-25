"""UUIDv7 minting for entry ids (AC1.2, DEC-010, DEC-021).

UUIDv7 is not in the Python stdlib `uuid` module (slated for 3.14). We use the
pure-Python `uuid6` package, whose `uuid7()` returns a stdlib `uuid.UUID` — so
the value drops natively into a future Postgres `uuid` column (DEC-010) and
needs no custom type. Time-ordered: free chronological sort + index locality.

This is the *only* place ids are minted. The store seam calls `mint_id()` on
append; capture surfaces never mint the canonical id.
"""

from __future__ import annotations

import uuid6


def mint_id() -> str:
    """Return a fresh UUIDv7 as a canonical string (AC1.2)."""
    return str(uuid6.uuid7())
