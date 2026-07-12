# Computer-dropper spike — findings (2026-07-11)

*Stack de-risking spike for Phase C / amb #3 (see 05_ stub). Code:
`fork/computer-dropper-spike/server.py` — throwaway by intent, ~150 lines,
stdlib-only. Exercised headlessly against a scratch lake; never touched live data.*

## What it proved

All three Excel jobs work over the existing seam in one file, no dependencies:
- **Drop:** POST → `append_entry` → id minted, µs+offset stamp, `source:
  computer-dropper`. Verified.
- **Whole-stream view:** day table with times, chronological. Verified.
- **Edit-older:** contenteditable cell → `edit_entry` in place. Verified
  (entry text updated in the lake file, id/timestamp preserved).
- Freshness: page-load composes `sync_sources()` first (checkin pattern,
  DEC-019).

## Evidence for the amb-#3 stack call ⚑

**Local web wins for Phase C.** The whole surface cost one sitting and zero
install/signing/distribution; Swift buys nothing at this scope. Recommend:
part-4-new `/spec` presumes local-web; native stays a full-wrapper (Phase F)
question. TUI ruled out by the edit-older UX.

## ⚠ Spec finding (the spike's real payoff)

**The seam has no id-bearing read.** `read_day` returns `{text, time,
created_at}` — sufficient for /checkin, insufficient for any edit UI
(`edit_entry` requires the id). The spike worked around it by calling the
private `_read_all` (documented violation). Part-4-new's `/spec` must settle
the seam-level answer — candidates: `read_day(..., with_ids=True)` ·
a `read_entries(day)` returning full records · ids always included (would
change /checkin's row shape — the D1 additive-passthrough precedent says
additive is fine ⚑). This belongs in part 1 iteration 3, one tiny AC.

## Open UX notes for the real spec (not solved here)

Multi-day scroll (spike shows today only) · keyboard-first nav · concurrent
sessions editing the same entry (last-write-wins today) · launchd/menu-bar
autostart · whether the same server becomes the mobile-inbox sync trigger
(07_ question 3).
