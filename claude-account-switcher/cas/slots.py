"""Slot config-dir lifecycle (spec AC1.3).

Each label gets a directory at ``~/.collevity/slots/<label>/`` that later phases
hand to ``claude`` as ``CLAUDE_CONFIG_DIR``. It is created at ``add`` time and
is absent before any ``add`` runs — so creation is an explicit act here, never a
side effect of importing or reading the store.

The dir holds no secret in phase 1 (the oat lives in the store record); it is
fully regenerable, so removal is unconditional. Validate the label before
calling any of these (see :func:`cas.labels.validate_label`).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from .labels import validate_label
from .paths import slot_dir

_SLOT_MODE = 0o700


def slot_exists(label: str) -> bool:
    validate_label(label)
    return slot_dir(label).is_dir()


def create_slot(label: str) -> Path:
    """Create (idempotently) the slot config dir for ``label`` and return it.

    Created ``0o700`` since it will hold per-account auth/config state in later
    phases. Validates the label first so a separator can never escape the slots
    dir.
    """
    validate_label(label)
    path = slot_dir(label)
    path.mkdir(parents=True, exist_ok=True, mode=_SLOT_MODE)
    return path


def remove_slot(label: str) -> bool:
    """Delete the slot config dir for ``label`` unconditionally.

    Returns ``True`` if a directory was removed, ``False`` if none existed.
    """
    validate_label(label)
    path = slot_dir(label)
    if not path.exists():
        return False
    shutil.rmtree(path)
    return True
