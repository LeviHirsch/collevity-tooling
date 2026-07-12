---
name: dropper-filer
description: File records dropped into the NascenTech _dropper/ folder. Reads each file, classifies it by CONTENT (never by filename), names it to the house convention, proposes a filing map, and moves it to its proper home only after approval. Trigger on "process the dropper", "file the dropper", "sort _dropper", or when the user drops scanned records (tax notices, registrations, statements) into _dropper/ and wants them filed.
---

# Dropper Filer

Turn a pile of dropped records into correctly-named files in their proper homes.
The drop zone is `_dropper/` at the NascenTech root. Sources of truth for naming and
routing are `CONVENTIONS.md` and `FILING-RULES.md` at that same root — read them first.

## Cardinal rule

**Classify by document content, never by the filename.** Dropped scans arrive with
meaningless names and frequently lead with a language-assistance / cover page. Read the
masthead, notice number, date, and account off the page.

## Procedure

1. **Inventory.** List `_dropper/`. For each file, get its page count if you can; note it's
   likely an iCloud item (materialize by reading it — `mdls` metadata may be unavailable).

2. **Identify — one file per read call.** Read each document's identifying pages. **Do not
   batch multiple files into a single read call:** rendered page images come back in call
   order and cross-file batches get mis-attributed (this caused a real mis-ID on 2026-07-06).
   Read one file per call; for multi-page scans, read the page bearing the notice number/date.

3. **Reconcile ambiguities before naming.** Watch for: cover pages whose content page is
   missing/blank (→ `...-cover-only`, `undated`, flag for re-scan); multi-doc bundles;
   true duplicates; A/B pairs (e.g. IRS CP148A to old address + CP148B to new). Escalate a
   genuine ambiguity; don't guess.

4. **Derive names + destinations** from `FILING-RULES.md`:
   `<descriptor>_<entity>_<date>_<source>.ext`. Registration/enrollment →
   `payroll/state-registrations/`; government notice/correspondence → `tax/notices/`;
   filings → `tax/<year>/`; entity governance → `01_STRUCTURE/_ENTITY/corporate/…`.

5. **Present the map + flags.** Show a `dropper file → is → destination/new-name` table.
   Call out flags: credential-bearing docs (PINs/passwords), incomplete scans, ambiguities.
   Get a quick go before moving anything.

6. **Move, safely.** Same-volume `mv -n` (atomic rename, no-clobber). Never `cp` then `rm`.
   Refuse any move whose destination already exists (collision) and report it.

7. **Verify + report.** List destination folders, confirm counts, confirm `_dropper/` is
   empty aside from dotfiles, confirm no collisions. Report what moved where and any flags.

## Notes

- Prefer absolute paths in shell; the working directory can reset between calls, and the
  tree lives under a path with spaces (`.../00 BUSINESS/00 NASCENTECH`).
- iCloud `.DS_Store` noise is expected in `_dropper/`; ignore it.
- This is the **manual-trigger** phase. The always-on watcher is a separate, deferred
  project — see `WATCHER-SCOPING.md` in the records-filer project.
- If `FILING-RULES.md` has no rule for a record kind, propose one, file the record, and note
  the new rule so it can be added — the rulebook grows from real cases.
