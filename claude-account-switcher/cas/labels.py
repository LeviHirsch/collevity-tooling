"""Label validation and the email-derived default (spec AC1.5).

A label is both the store key AND a slot directory name, so it must be
filesystem-safe: no path separators, no null bytes, not empty, and not a
directory-traversal name (``.`` / ``..``). These guards keep
``slots/<label>/`` from ever escaping the slots dir.

Uniqueness (the other half of AC1.5) is enforced by the store at write time,
not here, because it requires reading existing records — see
:meth:`cas.store.Store.write`.
"""

from __future__ import annotations

import os

from .errors import InvalidLabelError

# Reject both POSIX and Windows separators regardless of host, so a label minted
# on one platform stays safe if the store is ever carried to another.
_EXPLICIT_SEPARATORS = ("/", "\\")
_TRAVERSAL_NAMES = (".", "..")


def validate_label(label: str) -> None:
    """Raise :class:`InvalidLabelError` if ``label`` is not filesystem-safe.

    Returns ``None`` when the label is valid.
    """
    if not isinstance(label, str):
        raise InvalidLabelError("label must be a string")
    if label == "":
        raise InvalidLabelError("label must not be empty")
    if "\0" in label:
        raise InvalidLabelError("label must not contain a null byte")

    seps = set(_EXPLICIT_SEPARATORS)
    seps.add(os.sep)
    if os.altsep:
        seps.add(os.altsep)
    for sep in seps:
        if sep and sep in label:
            raise InvalidLabelError(
                f"label must not contain a path separator ({sep!r}): {label!r}"
            )

    if label in _TRAVERSAL_NAMES:
        raise InvalidLabelError(f"label must not be {label!r}")


def is_valid_label(label: str) -> bool:
    """Boolean form of :func:`validate_label` (no exception)."""
    try:
        validate_label(label)
    except InvalidLabelError:
        return False
    return True


def default_label_from_email(email: str) -> str:
    """Return the default label for an email: its local-part (text before ``@``).

    Does not validate the result — the caller should pass it through
    :func:`validate_label` (an email like ``@host`` yields an empty local-part,
    which is invalid).
    """
    if not isinstance(email, str):
        raise InvalidLabelError("email must be a string")
    return email.split("@", 1)[0]
