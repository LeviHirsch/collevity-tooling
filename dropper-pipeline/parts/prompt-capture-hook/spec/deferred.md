# Deferred items

_Backlog of feature requests, bug reports, and ideas not yet committed to any iteration. Triaged at each iteration's interview._

## D-001 — Part-1: crash-safe lake read/append (tolerate a torn JSONL line)
- First seen: 2026-07-13 (iteration 1, via /spec revise during review v001-2026-07-13-1827)
- Last touched: 2026-07-13 (iteration 1)
- Defer count: 0
- Category: refactor
- Description: `_read_all` (lake.py) raises `ValueError` on any corrupt/torn JSONL line, so a single bad line breaks every lake read (read_day / sync / edit) until manually repaired. Harden part-1 so the reader tolerates a bad line (skip-and-warn) and/or the append is crash-safe (fsync or atomic-tmp), so a writer killed mid-append can never brick reads.
- Notes: Surfaced by the prompt-capture-hook review (torn-write-on-timeout-kill residual, DEC-021). This is part-1 (jsonl-schema) territory — the hook is a thin writer over `append_entry` (DEC-015 layer logic), so it can't and shouldn't fix reader/writer crash-safety itself. Candidate part-1 iteration-3 AC (alongside the id-bearing-read gap the computer-dropper spike found). Low probability, high blast radius — worth doing before the lake grows.
