"""claude-account-switcher (cas) — phase 1 substrate.

Public surface for the store / slot / label bedrock that later phases build on.
No CLI is wired up yet (that is phase 2+); this package is the library layer.
"""

from __future__ import annotations

from .errors import CasError, InvalidLabelError, LabelExistsError
from .labels import default_label_from_email, is_valid_label, validate_label
from .slots import create_slot, remove_slot, slot_exists
from .store import Record, Store

__all__ = [
    "CasError",
    "InvalidLabelError",
    "LabelExistsError",
    "Record",
    "Store",
    "create_slot",
    "default_label_from_email",
    "is_valid_label",
    "remove_slot",
    "slot_exists",
    "validate_label",
]
