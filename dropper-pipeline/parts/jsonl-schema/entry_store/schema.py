"""Logical entry schema — the executable field contract (AC1).

Enforces the required floor (AC1.1), the field types, and the closed top level
(AC1.8). It deliberately does NOT enforce:

  - `context` shape — reserved in v1, not validated (AC1.6); the claude-hook
    conditional requirement is part 3's work.
  - the `meta_notes` prose convention — a convention, not a constraint (AC1.7).
  - `created_at` offset *correctness* — owned at capture, not here (DEC-017);
    we only check an explicit offset is present, not that it is the right one.

See SCHEMA.md for the prose contract this mirrors.
"""

from __future__ import annotations

from datetime import datetime

# The required floor (AC1.1). Order is documentation, not significance.
FLOOR_FIELDS = ("id", "text", "created_at", "source", "author")

# Optional fields, absent-when-unused (AC1.5). Mapped to their JSON type.
OPTIONAL_FIELDS = {
    "context": dict,       # designed source-shaped object (AC1.6) — shape not validated in v1
    "tags": list,          # ad-hoc non-authoritative labels (AC1.7)
    "meta_notes": str,     # prose about the entry (AC1.7); convention not enforced
    "source_data": dict,   # undesigned structured remainder (AC1.7)
}

# Closed top level (AC1.8): nothing outside floor + optional is allowed. This is
# how the strata-era exclusions (entity_axis, kind, lineage_id, tier, modified,
# occurred_at, planned_for, horizon-as-field) are kept out in practice.
ALLOWED_FIELDS = frozenset(FLOOR_FIELDS) | frozenset(OPTIONAL_FIELDS)

# Named purely for a clearer error message when one shows up (AC1.8).
_EXCLUDED_HINT = {
    "entity_axis": "entity facet → vertical store (DEC-003)",
    "kind": "stream-item discriminator deferred (DEC-004)",
    "lineage_id": "no revision history; edits are in-place (DEC-006)",
    "supersedes": "no revision history; edits are in-place (DEC-006)",
    "tier": "persistence-retention is downstream (DEC-009)",
    "modified": "no edit-bump; never read from Excel (DEC-006, DEC-011)",
    "updated_at": "no edit-bump (DEC-006)",
    "occurred_at": "when-it-happened ≠ when-logged → strata (DEC-013/014)",
    "planned_for": "strata-era promotion (DEC-014)",
    "horizon": "folded into `tags` (DEC-014)",
}


class SchemaError(ValueError):
    """An entry violates the logical schema (the field contract)."""


def _check_created_at(value: object) -> None:
    """`created_at` is an ISO-8601 string with an explicit offset (AC1.3).

    We verify it parses AND carries an offset (tzinfo). We do NOT judge whether
    the offset is the *correct* local one — that is owned at capture (DEC-017).
    """
    if not isinstance(value, str):
        raise SchemaError(f"created_at must be an ISO-8601 string, got {type(value).__name__}")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise SchemaError(f"created_at is not valid ISO-8601: {value!r} ({exc})") from exc
    if parsed.utcoffset() is None:
        raise SchemaError(
            f"created_at must carry an explicit offset (e.g. -04:00); got naive {value!r}"
        )


def validate(entry: object) -> None:
    """Validate a logical entry in place. Raise SchemaError on any violation.

    Checks, in order: object-ness, no excluded/unknown top-level keys (AC1.8),
    the required floor is present and well-typed (AC1.1–1.4), and any present
    optional field has the right JSON type (AC1.5–1.7).
    """
    if not isinstance(entry, dict):
        raise SchemaError(f"an entry must be a JSON object, got {type(entry).__name__}")

    # Closed top level (AC1.8) — reject excluded/unknown keys with a pointed reason.
    for key in entry:
        if key in ALLOWED_FIELDS:
            continue
        if key in _EXCLUDED_HINT:
            raise SchemaError(
                f"field {key!r} is explicitly excluded from the v1 entry: "
                f"{_EXCLUDED_HINT[key]}. Stash structured remainder in `source_data` instead."
            )
        raise SchemaError(
            f"unknown top-level field {key!r}; allowed: {sorted(ALLOWED_FIELDS)}. "
            f"Put extra structured data in `source_data` (DEC-012)."
        )

    # Required floor present (AC1.1).
    missing = [f for f in FLOOR_FIELDS if f not in entry]
    if missing:
        raise SchemaError(f"missing required floor field(s): {missing}")

    # Floor types (AC1.1–1.4).
    for f in ("id", "text", "source", "author"):
        if not isinstance(entry[f], str):
            raise SchemaError(f"{f} must be a string, got {type(entry[f]).__name__}")
    _check_created_at(entry["created_at"])

    # author == "user" in v1 (AC1.4).
    if entry["author"] != "user":
        raise SchemaError(f"author must be 'user' in v1, got {entry['author']!r}")

    # source must be a non-empty channel tag (AC1.4).
    if not entry["source"]:
        raise SchemaError("source must be a non-empty channel tag")

    # Optional field types (AC1.5–1.7). Absent is always fine.
    for name, expected in OPTIONAL_FIELDS.items():
        if name in entry and not isinstance(entry[name], expected):
            raise SchemaError(
                f"{name} must be {expected.__name__} when present, "
                f"got {type(entry[name]).__name__}"
            )
