# Collevity Entry — Logical Schema (v1)

> The canonical field-level shape of a Collevity **entry**: one item in the
> horizontal, append-dominant time-stream (the "lake"). This document is the
> field contract; `entry_store/schema.py` is its executable enforcement of the
> required floor. The stream stays deliberately **thin** — typing, structure,
> entities, and revision history accrete downstream in the strata layer, never
> on the raw entry (DEC-009).
>
> Spec: `spec/spec.md` (AC1). Decisions: `spec/decisions.log`.

A **valid entry is exactly one JSON object** carrying the required floor. On
disk the pool is JSONL — one entry object per line (DEC-005).

---

## Required floor (AC1.1)

Every entry MUST carry all five. A record missing any of them is invalid.

| field        | type   | rule |
|--------------|--------|------|
| `id`         | string | UUIDv7. **Minted by the store seam on append** (`append_entry`), never by the capture surface (AC1.2, DEC-010). |
| `text`       | string | The drop body. The one field a capture surface must supply. |
| `created_at` | string | ISO-8601 **with explicit offset** (AC1.3). |
| `source`     | string | Always-present channel tag, e.g. `dropper-excel`, `claude-hook` (AC1.4, DEC-002). |
| `author`     | string | Present; **equals `user` in v1** (AC1.4). |

### `id` — UUIDv7 (AC1.2, DEC-010)
A UUIDv7 string (RFC 9562), time-ordered for free chronological sort and index
locality on the future Postgres rung. **Store-minted on append**, not surface-
minted — surfaces may hold a transient local id, but the core assigns the
canonical one. Generated via the `uuid6` library (`uuid6.uuid7()` → stdlib
`uuid.UUID`); not in the Python stdlib `uuid` module (DEC-021).

### `created_at` — ISO-8601 + offset (AC1.3, DEC-014)
Instant **and** local offset in a single string, e.g. `2026-06-24T15:42:00-04:00`.

- **No separate `tz` field.** The offset on the string is the whole story.
- **IANA zone name deferred** — the offset pins the instant and the local day;
  a named zone is only needed for DST-correct forward-dated reasoning, additive
  later (DEC-014).
- Sorts lexicographically; maps to Postgres `timestamptz`.
- Roots out the tz mis-bucketing bug: `read_day` buckets by the **local day of
  this offset** (AC3.2), so an evening/late-night drop lands on the day it was
  made, not the next UTC day.
- **Offset correctness is owned at capture, not here (DEC-017).** Each capture
  surface stamps the correct local offset at write time; the store assumes it
  and neither re-derives nor validates it. (The Excel channel can't self-stamp;
  its offset is the **bridge's** duty — Phase 2 / AC4.4 — not the core's.)

### `source` / `author` (AC1.4, DEC-002)
`source` is a simple channel tag, always present. `author` is present and is
`user` for every v1 entry (even Claude-prompt drops are user entries — DEC-002).

---

## Optional fields (AC1.5)

Four optional fields, **absent-when-unused**. A record carrying **none** of them
still validates. Each has a distinct job (DEC-012); do not overload one for
another's purpose.

| field         | type   | job |
|---------------|--------|-----|
| `context`     | object | **Designed** source-shaped context (AC1.6, DEC-002). |
| `tags`        | array  | Ad-hoc, non-authoritative labels (AC1.7, DEC-008). |
| `meta_notes`  | string | Prose annotations *about* the entry (AC1.7, DEC-012). |
| `source_data` | object | **Undesigned** structured remainder from the source (AC1.7, DEC-012). |

### `context` — optional source-shaped object (AC1.6, DEC-002)
Channel-specific structured context, keyed to `source`. **Reserved in v1, not
validated** — no hook channel exists yet. The reserved shape for the
`claude-hook` source:

```json
"context": { "kind": "claude-session", "session_id": "...", "seq": 3, "parent_id": "..." }
```

(`parent_id` optional.) When the prompt-capture hook goes live (part 3),
`context` becomes **conditionally required** for `source: claude-hook` entries —
that conditional validation is part 3's work, not v1's.

### `tags` — optional free-form array (AC1.7, DEC-008)
Ad-hoc labels for crude filtering/associating the raw stream before the entity
layer exists. **Non-authoritative**: not a taxonomy, no committed vocabulary,
not load-bearing for typed retrieval (the strata layer owns authoritative
typing). Absorbs the former `horizon` (a plan/projected drop is just a tag —
DEC-014).

### `meta_notes` — optional prose string (AC1.7, DEC-012)
Unstructured human/AI annotations about the entry. Safe because it is prose — it
can't silently become a queryable schema.

> **Convention (documented, not enforced):** append-only, one line each,
> `ISO-timestamp — free prose`, **newest at the bottom**, **no typed prefixes /
> categories**. Wanting typed prefixes is the tripwire to promote the data to
> `source_data` or a real field — not to bend `meta_notes` into a schema.

The store does not parse or validate this convention; it only checks the field
is a string.

### `source_data` — optional structured stash (AC1.7, DEC-012)
The **schema-on-read** lossless stash: structured remainder *from the source*
preserved verbatim when it doesn't warrant core fields — neither discarded
(lossy) nor promoted-everything (rigid). A field can be promoted later with its
history intact. **Reserved in v1, not required to populate**; first populator is
the claude-hook session payload (part 3). This — not arbitrary top-level keys —
is the home for any extra structured data a source carries.

---

## Explicitly excluded (AC1.8)

The following are **deliberately not part of the v1 entry**. They are noted as
the natural strata-era promotions, but an entry MUST NOT carry them at the top
level (the store rejects them — see "Closed top level" below).

| excluded field            | why out | reference |
|---------------------------|---------|-----------|
| `entity_axis`             | entity/"things" facet → vertical store, out of scope | DEC-003 |
| `kind`                    | stream-item-kind discriminator deferred; `source`/`tags` distinguish for now | DEC-004 |
| `lineage_id` / revision   | edits are in-place corrections; no revision history (versioning is an entity concern) | DEC-006 |
| `tier`                    | persistence-retention lifecycle is a downstream concern | DEC-009 |
| `modified` / `updated_at` | no edit-bump; the Excel `modified` column is never even read | DEC-006, DEC-011 |
| `occurred_at`             | when-it-happened ≠ when-logged → strata record concern | DEC-013, DEC-014 |
| `planned_for`             | no v1 consumer; strata-era promotion | DEC-014 |
| `horizon` (as a field)    | folded into `tags` — a bare label once its backing times are gone | DEC-014 |

**Closed top level.** Beyond the 5 floor + 4 optional fields above, the entry
has **no other top-level keys**. Any extra structured data belongs in
`source_data` (DEC-012), not as a new top-level field. The store rejects unknown
top-level keys — this is how the exclusions above are kept out in practice and
how strata-era fields are prevented from leaking in early.

---

## Minimal valid entry (floor only)

```json
{
  "id": "019f00a9-caa5-73eb-a38d-84658b96e6a7",
  "text": "Picked up the prescription.",
  "created_at": "2026-06-24T15:42:00-04:00",
  "source": "dropper-excel",
  "author": "user"
}
```

## Fuller entry (some optionals)

```json
{
  "id": "019f00aa-1b2c-7def-8000-0123456789ab",
  "text": "Idea: weekly report generated from the lake, not hand-written.",
  "created_at": "2026-06-24T22:10:00-04:00",
  "source": "dropper-excel",
  "author": "user",
  "tags": ["idea", "collevity"],
  "meta_notes": "2026-06-25T09:00:00-04:00 — revisit after the schema part ships"
}
```
