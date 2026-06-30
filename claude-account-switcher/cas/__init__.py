"""claude-account-switcher (cas).

Public surface for the store / slot / label bedrock (Phase 1) and the guided
`add` mint flow (Phase 2). The installed CLI name + alias are Phase 5 (AC7.3);
for now invoke via ``python -m cas`` or :func:`cas.cli.main`.
"""

from __future__ import annotations

from .add import run_add
from .cli import main
from .errors import CasError, InvalidLabelError, LabelExistsError, MintError
from .labels import default_label_from_email, is_valid_label, validate_label
from .slots import create_slot, remove_slot, slot_exists
from .store import Record, Store

__all__ = [
    "CasError",
    "InvalidLabelError",
    "LabelExistsError",
    "MintError",
    "Record",
    "Store",
    "create_slot",
    "default_label_from_email",
    "is_valid_label",
    "main",
    "remove_slot",
    "run_add",
    "slot_exists",
    "validate_label",
]
