# Mobile shortcut (part 2) — pre-spec brief (2026-07-11)

*Interview prep, not the spec. One structural finding + the option space, so the
human-gated `/spec` interview starts warm. ⚑ = inference/recommendation.*

## The structural finding: "writes the pool day-one" (amb #4) has a catch

The stub's default — shortcut writes the *same pool* day one — collides with two
settled rules:

1. **Seam-only rule (part 1):** nothing touches the JSONL except
   `append_entry`/`edit_entry`/`read_day`/`sync_sources`. An iOS Shortcut
   appending a line directly bypasses the seam.
2. **Id minting (AC1.2/DEC-010):** the seam mints the UUIDv7 on append. A
   direct-appended line has no `id` → schema-invalid entry sitting in the lake
   (and `validate()` never ran on it).

So "same pool day-one" can hold **in spirit** (one store, no second silo) while
the mechanism goes through an ingest step — exactly how Excel already works.

## Option space for the append mechanism

| # | Mechanism | How | Trade |
|---|---|---|---|
| A ⚑ | **Inbox file + bridge** (Excel-bridge pattern, recommended) | Shortcut appends one JSON(-ish) line — or one file per drop — to `…/_DATA/mobile-inbox/`; a second registered ingester in `sync_sources` mints ids, validates, dedupes, deletes/marks consumed | Proven pattern; offline-tolerant for free (iCloud queues the file); no server; latency = next sync (checkin/CLI composes sync anyway). Needs bridge code + DEC-018's "no registry" stance relaxed to *two* explicit ingesters |
| B | **Relay to the Mac** (SSH via "Run Script Over SSH", or a tiny always-on local HTTP endpoint) | Shortcut calls the Mac; Mac runs `append_entry` | True day-one pool write through the seam; but requires Mac awake/reachable — fails exactly when mobile capture matters (out of the house); adds an always-on service |
| C | **Direct JSONL append from Shortcuts** | Shortcut builds the JSON line and appends to the lake file | Violates seam-only + id rules; JSON-escaping in Shortcuts is fragile; concurrent-write safety (D3 flock) can't be honored from iOS. Reject ⚑ |

**Recommended default ⚑: A.** It matches the existing architecture (pull-ingest
boundary is explicitly "permanent" in `lake.py`), inherits offline/queue/dedupe
answers the stub asks for, and keeps the shortcut itself dumb (friction floor).
Amb #4 then resolves as: *one store day-one, via ingest* — same answer Excel got.

## What the shortcut itself needs to capture (per drop)
`text` (typed / dictated / share-sheet) · capture timestamp **with tz offset**
(Shortcuts "Current Date" formatted ISO w/ offset — verify µs availability;
seconds likely the floor ⚑) · fixed `source: "mobile-shortcut"` · `author: "user"`.
Dedupe key for the bridge: content-hash or per-drop filename UUID (Shortcuts has
"Make UUID"? — verify; else timestamp+hash ⚑).

## Interview questions worth pre-loading
1. Ratify A vs B (or A now, B never/later)?
2. One inbox *file* (append) vs one *file per drop* (no partial-line risk,
   trivially atomic — recommended ⚑)?
3. Sync trigger: is "next checkin/CLI run" fresh enough, or does Levi want a
   faster path (e.g., the future computer-dropper server also syncing)?
4. Friction floor: home-screen icon? Action button? Share-sheet? Dictation-first?
5. Does the DEC-018 "single ingester, no registry" decision get amended (2
   explicit ingesters) or is the inbox folded into the Excel bridge's sweep?

## Dependencies check (all satisfiable now)
Part 1 built; iter-2 D3 lock (in fork) protects concurrent bridge/hook writes;
nothing here waits on the hook install.
