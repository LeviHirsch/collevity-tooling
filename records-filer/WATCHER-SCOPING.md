# Phase 2 — Always-on Watcher: Scoping Inputs
*Deferred. Do NOT build yet. Scope with `/spec` before writing code.*

The goal of Phase 2 is to remove the manual trigger: a drop into `_dropper/` gets classified,
named, and filed (or quarantined for approval) without someone invoking the skill. Below are
the inputs, constraints, and open questions gathered while doing Phase 1 by hand.

## Open questions to resolve in the spec

1. **Trigger mechanism.** launchd `WatchPaths` agent vs. an fswatch/FSEvents daemon vs. a
   small always-running local server vs. a scheduled poll (cron/CronCreate). Does this warrant
   *hosting a server* at all, or is a per-Mac launchd agent sufficient? Decide against the
   actual need — a single founder on Mac(s) is very different from a team.

2. **iCloud materialization.** Files in `_dropper/` may be **dataless placeholders** (not yet
   downloaded). `mdls` metadata was unavailable on the 2026-07-06 batch. A watcher must force
   download / wait for materialization before reading, and tolerate sync latency and partial
   writes (don't act on a file mid-sync).

3. **Dotfolder reality (Mac-only, invisible).** Hidden `.`-folders sync Mac↔Mac but are
   invisible on iOS/Files/iCloud.com and sync best-effort. Config/commands stored in `.claude/`
   or a `.collevity/` cannot be seen or edited from phone/web. Decide where watcher config and
   logs live given this.

4. **`.collevity/` at the business root (the Q3-option-3 question).** Should Collevity become
   first-class infra inside the business tree — a `.collevity/` folder holding watcher config,
   command registry, and drop-zone definitions? Weigh the first-class-infra benefit against the
   Mac-only/invisible dotfolder constraint. Alternative: a *visible* `_collevity/` (leading
   underscore, per house convention) so it's reachable everywhere.

5. **Unattended moves of legal/financial records — safety.** Auto-moving tax and legal
   documents is high-stakes. Require a **human-approval or quarantine step**: low-confidence or
   flagged items (credential-bearing, incomplete scan, ambiguous, no matching rule) land in a
   `_dropper/_review/` holding area instead of being filed. Never auto-`rm`; only `mv`.

6. **Classification engine.** Phase 1 uses a human-in-the-loop LLM read. Phase 2 options:
   same LLM invoked headlessly per file, vs. OCR + rules, vs. hybrid. Confidence threshold
   governs auto-file vs. quarantine.

7. **Audit + reversibility.** Every automated move logged (source name, hash, destination,
   timestamp, rule fired) so any misfile is traceable and undoable.

## Reuse / alignment

- Naming + routing rulebook already exists: `CONVENTIONS.md` + `FILING-RULES.md` (root). The
  watcher must consume the *same* rulebook as the Phase-1 skill — one source of truth.
- Share "Dropper" vocabulary with `../dropper-pipeline/`; keep domains distinct (business
  records vs. personal capture). Consider whether a common Dropper substrate (watch → stage →
  classify → route → log) should be factored out to serve both.

## Not now, but note
Team scale, multi-device, and a shared drop zone (email-to-dropper, scan-to-dropper) would
change the answer on hosting a server — revisit if NascenTech adds staff who file records.
