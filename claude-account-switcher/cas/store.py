"""The per-user credential store: single JSON file, record-per-label (spec AC1).

Layout on disk (AC1.2 — "keyed by label"):

    {
      "<label>": {"email": ..., "oat": ..., "mint_date": ..., "mint_profile": ...},
      ...
    }

The file lives at ``~/.collevity/store.json`` (AC1.1), is written ``chmod 600``
(the ``oat`` is a 1-year bearer token — the sensitive value), and survives a
restart because it is just a file on disk.

Read convention (AC1.2): reading an absent label returns ``None`` and never
raises. Invalid or colliding labels raise typed errors from :mod:`cas.errors`.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .errors import LabelExistsError
from .labels import validate_label
from .paths import store_path

# Mode bits: 0o600 for the secret-bearing file, 0o700 for the dir that holds it
# (and the slot dirs). Set explicitly rather than relying on umask.
_FILE_MODE = 0o600
_DIR_MODE = 0o700


@dataclass
class Record:
    """One stored account binding (AC1.2 schema).

    ``mint_profile`` (AC1.4) is always present in the serialized form; its value
    may be ``None``. Phase 1 only round-trips it — no profile association or
    validation is done here (D-002).
    """

    email: str
    oat: str
    mint_date: str
    mint_profile: Optional[str] = None

    def to_dict(self) -> dict:
        # mint_profile is emitted unconditionally so the field is always present
        # in the schema on disk (AC1.4), value possibly null.
        return {
            "email": self.email,
            "oat": self.oat,
            "mint_date": self.mint_date,
            "mint_profile": self.mint_profile,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Record":
        # .get for mint_profile tolerates an older record that lacks the key.
        return cls(
            email=data["email"],
            oat=data["oat"],
            mint_date=data["mint_date"],
            mint_profile=data.get("mint_profile"),
        )


class Store:
    """CRUD over the single JSON store file.

    Stateless beyond its path: every operation reads/writes the file fresh, so
    two short-lived processes never share an in-memory view that could drift
    from disk. (Concurrent *writers* are out of scope for phase 1; v1 mints
    are interactive and serial.)
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        # Resolve lazily-by-default through paths.store_path(), so a test that
        # sets COLLEVITY_HOME is honored without passing a path explicitly.
        self.path = Path(path) if path is not None else store_path()

    # -- internal load/save -------------------------------------------------

    def _load_raw(self) -> dict:
        """Return the raw ``{label: record_dict}`` map; ``{}`` if no file yet."""
        if not self.path.exists():
            return {}
        with self.path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError(
                f"store at {self.path} is malformed: expected a JSON object"
            )
        return data

    def _save_raw(self, data: dict) -> None:
        """Atomically write ``data`` as JSON with secure permissions.

        Writes to a temp file (created 0o600) in the same dir, then
        ``os.replace`` swaps it in — so a reader never sees a half-written
        store, and the file is never world-readable even momentarily.
        """
        directory = self.path.parent
        directory.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(directory, _DIR_MODE)
        except OSError:
            # Best-effort dir hardening; the file mode below is the guarantee.
            pass

        tmp = directory / (self.path.name + ".tmp")
        fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, _FILE_MODE)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, sort_keys=True)
                f.write("\n")
        except Exception:
            tmp.unlink(missing_ok=True)
            raise
        os.replace(tmp, self.path)
        # os.replace can carry the destination's prior mode on some systems;
        # reassert 600 to be certain (AC1.1).
        os.chmod(self.path, _FILE_MODE)

    # -- read ---------------------------------------------------------------

    def read(self, label: str) -> Optional[Record]:
        """Return the :class:`Record` for ``label``, or ``None`` if absent.

        Absent is not an error (AC1.2): this never raises for a missing label.
        """
        raw = self._load_raw().get(label)
        if raw is None:
            return None
        return Record.from_dict(raw)

    def exists(self, label: str) -> bool:
        return label in self._load_raw()

    def labels(self) -> list[str]:
        """All stored labels, sorted."""
        return sorted(self._load_raw().keys())

    def all(self) -> dict[str, Record]:
        """Every record keyed by label."""
        return {k: Record.from_dict(v) for k, v in self._load_raw().items()}

    def labels_for_email(self, email: str) -> list[str]:
        """Labels currently bound to ``email`` (supports the AC2.7 dup warn).

        Email-uniqueness is intentionally NOT enforced (AC1.2): this is a query,
        not a constraint.
        """
        return sorted(
            label
            for label, rec in self._load_raw().items()
            if rec.get("email") == email
        )

    # -- write / delete -----------------------------------------------------

    def write(self, label: str, record: Record, *, overwrite: bool = False) -> None:
        """Validate ``label`` and write ``record``.

        Raises :class:`InvalidLabelError` if the label is not filesystem-safe,
        and :class:`LabelExistsError` if it already exists and ``overwrite`` is
        ``False`` — in which case nothing is written, satisfying AC1.5's
        "blocked until a unique label is given".
        """
        validate_label(label)
        data = self._load_raw()
        if not overwrite and label in data:
            raise LabelExistsError(label)
        data[label] = record.to_dict()
        self._save_raw(data)

    def delete(self, label: str) -> bool:
        """Remove ``label`` from the store.

        Returns ``True`` if a record was removed, ``False`` if it was absent
        (never raises for a missing label — symmetric with :meth:`read`).
        """
        data = self._load_raw()
        if label not in data:
            return False
        del data[label]
        self._save_raw(data)
        return True
