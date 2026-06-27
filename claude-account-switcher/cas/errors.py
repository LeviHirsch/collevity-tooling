"""Typed errors for the claude-account-switcher store/slot/label substrate.

Phase 1 convention (see spec AC1.2, AC1.5): a *missing* label is NOT an error —
the read layer returns ``None`` for it and never raises. Errors are reserved for
*invalid input* (a malformed label) and *constraint violations* (a label that
already exists), so the command layer can catch a specific type and render a
clear message without inspecting strings.
"""

from __future__ import annotations


class CasError(Exception):
    """Base class for every error this tool raises. Catch this to catch all."""


class InvalidLabelError(CasError):
    """A label is not filesystem-safe (path separator, null byte, empty, etc.).

    Maps to AC1.5's "must be filesystem-safe" requirement.
    """


class LabelExistsError(CasError):
    """A label already exists in the store and overwrite was not requested.

    Maps to AC1.5's "unique across all records" requirement: on collision the
    store refuses to write, so no record is overwritten until a unique label is
    supplied.
    """

    def __init__(self, label: str) -> None:
        self.label = label
        super().__init__(f"label {label!r} already exists in the store")
