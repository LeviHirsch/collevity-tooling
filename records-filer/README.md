# Records Filer
*Seeded 2026-07-06. Sibling to `dropper-pipeline/` — shares the "Dropper" drop-zone
vocabulary, distinct domain.*

## What this project is

An auto-filer for **business records** dropped into a folder: read each dropped file,
classify it **by content** (not filename), name it to the house convention, and sort it to
its proper home in the NascenTech tree. `dropper-pipeline/` is the *personal-capture*
Dropper (conversation → JSONL → threads); this is the *business-records* Dropper (scanned
tax notices, registrations, statements → filed, named documents).

Born from a real use case: on 2026-07-06 eight scanned government documents (VA/DC/IRS tax
notices, an EFTPS enrollment with a live PIN, a DC business-tax registration) landed in
`_dropper/` with meaningless, content-mismatched filenames. Filing them by hand produced the
convention and rules this project encodes.

## Phases

- **Phase 1 — manual-trigger skill (DONE, live).** The `dropper-filer` skill. You invoke it
  ("process the dropper"); it reads, classifies, proposes a filing map, and moves on your
  approval. Part of NascenTech operating procedure.
- **Phase 2 — always-on watcher (DEFERRED, needs its own spec).** A background process that
  files drops without a manual trigger. See `WATCHER-SCOPING.md`. Scope via `/spec` before
  building.

## Contents

- `README.md` — this file. Project home.
- `skill/SKILL.md` — **canonical source** of the Phase-1 `dropper-filer` skill.
- `WATCHER-SCOPING.md` — Phase-2 inputs and open questions (do not build yet).

## Install / where it runs

The skill is **installed** (copied) to the NascenTech project at
`00 BUSINESS/00 NASCENTECH/.claude/skills/dropper-filer/SKILL.md`, which is where Claude Code
picks it up when working in that folder. `skill/SKILL.md` here is the versioned original;
keep the two in sync (canonical → install is a copy).

> **iCloud caveat:** `.claude/` is a hidden dotfolder. Hidden folders sync **Mac↔Mac** in
> iCloud (verified: the tree already has live `.claude/` files) but are **invisible and
> inaccessible on iOS, the Files app, and iCloud.com**, and sync is best-effort. So the
> install is a Mac-only convenience; **this project (visible, git-versioned) is the source of
> truth.** Validate sync with the marker test in `WATCHER-SCOPING.md` before relying on the
> install across machines.

## Rules of record

The naming + routing rulebook lives with the data it governs, at the NascenTech root:
`CONVENTIONS.md` (grammar) and `FILING-RULES.md` (operational routing + source tokens). The
skill reads those; this project points to them rather than duplicating them.

## Related

- `../dropper-pipeline/` — the personal-capture Dropper (shared vocabulary, different domain).
- `[[strategy-scope-spec]]` (S3) · `[[collevity]]` · Collevity `/spec` process for Phase 2.
