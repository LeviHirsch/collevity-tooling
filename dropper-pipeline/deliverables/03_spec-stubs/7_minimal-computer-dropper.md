# Spec-stub — Minimal Computer Dropper + Editable Table View · op-path slot 4 (new, DEC-007)

*Drafted 2026-07-11 in the full pass — the part DEC-007 pulled forward but never
got a launch packet. Format follows the DP-1 §3 stubs. **Proposal**: lives in the
full-pass workspace; move to `deliverables/03_spec-stubs/` (as e.g.
`7_minimal-computer-dropper.md`) when ratified.*

## Problem statement
DEC-007 found today's Excel does **3 jobs**: computer capture · whole-stream
view · edit-older. The original op-path only restored them at the *last* part
(full app wrapper), leaving a long gap where retiring Excel would lose
capabilities. This part is the deliberately minimal replacement for those 3
jobs — enough to retire Excel — while the full filing-UX wrapper stays last.

## Inputs
- The live lake + seam (`append_entry` / `edit_entry` / `read_day` /
  `sync_sources`) — part 1, built. After iter 2: writer-lock + settle
  compaction make a second computer writer safe.
- DEC-007's job inventory (capture / view / edit-older) as the scope fence.

## Outputs
- A computer-side surface with exactly three affordances:
  1. **Drop box** — type text, hit enter, `append_entry` to the lake (µs +
     offset stamp, `source:` its own channel tag).
  2. **Whole-stream table view** — chronological, scroll/filter by day.
  3. **Edit-in-place** — click an older entry, correct text, `edit_entry`.

## "Done"
Levi stops opening `Dropper_excel.xlsm`: a computer drop reaches the lake in
≤ the Excel's current friction; the stream is browsable; an old entry can be
corrected — then **Excel retires** (bridge deleted per its clean-delete design,
`source: dropper-excel` entries stay in the lake forever).

## What its `/spec` must settle
- **Stack (= open amb #3, inherited):** Swift menu-bar app vs local web page
  (vs a third option: terminal TUI). The wrapper stub's stack question applies
  here first now that this part leads. Recommended default ⚑: local web
  (single HTML + tiny Python server over the seam) — fastest to ship, reuses
  the venv, no signing/distribution; revisit native for the full wrapper.
- Whether view/edit go through the seam only (yes — seam-only rule) and
  whether the server composes `sync_sources()` on load (checkin-style).
- `source` channel tag value (e.g. `computer-dropper`).
- Keyboard-first UX floor (the Excel muscle-memory it replaces).
- What it explicitly does NOT do: typing/leveling/threading (ingest's job),
  filing UX (full wrapper's job), mobile (part 2's job).

## Dependencies
Part 1 iter 2 (D3 writer lock — two computer writers + hook may coexist;
built-in-fork 2026-07-11, pending merge). Not blocked by the hook or part 2.

## Derived direction (from the full pass)
- Keep it under a week of sessions; if the spec balloons, it's absorbing the
  wrapper — cut back to the 3 jobs.
- Excel retirement is this part's acceptance test, not a separate project.
