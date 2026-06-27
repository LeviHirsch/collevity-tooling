"""Filesystem locations for the per-user store and slot config dirs.

The base directory is ``~/.collevity/`` by default (spec AC1.1: outside the repo
AND outside iCloud — a real home-dir path is the defense, since this repo lives
inside iCloud Drive). The default is overridable via the ``COLLEVITY_HOME``
environment variable so tests can run hermetically in a temp dir without
touching the real home; this mirrors the sibling project's ``COLLEVITY_LAKE``.

Nothing here is macOS-specific: ``Path.home()`` and these joins behave
identically on macOS and Linux (constraint: portable core).
"""

from __future__ import annotations

import os
from pathlib import Path

#: Environment variable that, when set, relocates the entire store/slot tree.
HOME_ENV = "COLLEVITY_HOME"

#: Default base-dir name under the user's home directory.
DEFAULT_DIRNAME = ".collevity"

#: Filename of the single JSON store inside the base dir.
STORE_FILENAME = "store.json"

#: Sub-directory of the base dir that holds the per-label slot config dirs.
SLOTS_DIRNAME = "slots"


def base_dir() -> Path:
    """Return the base directory holding the store and slots.

    Honors ``COLLEVITY_HOME`` if set (expanding ``~``); otherwise
    ``~/.collevity/``. The path is returned whether or not it exists yet.
    """
    override = os.environ.get(HOME_ENV)
    if override:
        return Path(override).expanduser()
    return Path.home() / DEFAULT_DIRNAME


def store_path() -> Path:
    """Absolute path to the single JSON store file."""
    return base_dir() / STORE_FILENAME


def slots_dir() -> Path:
    """Absolute path to the directory that contains all slot config dirs."""
    return base_dir() / SLOTS_DIRNAME


def slot_dir(label: str) -> Path:
    """Absolute path to one label's slot config dir (``CLAUDE_CONFIG_DIR``).

    The caller is responsible for validating ``label`` first (see
    :func:`cas.labels.validate_label`); this function does no validation, so it
    must not be handed unvalidated input that could contain path separators.
    """
    return slots_dir() / label
