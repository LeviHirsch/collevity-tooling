# iterative-draft-review

*A reusable method + (eventual) Claude Code skill for producing high-quality written deliverables through **Rubric-Anchored Blind Iteration**. Seeded 2026-07-01.*

## What it is
A repeatable loop for any *judged* written deliverable (grant pitches, specs, memos, cover letters, marketing copy): **draft → review against an explicit rubric → refine the prompt → blind rewrite → repeat until diminishing returns.** The durable asset is not any single draft — it's the *rubric + accumulated-requirements prompt* per deliverable type.

## Why it exists
It emerged, fully worked, in a real session: drafting a NSF SBIR Project Pitch across three blind iterations (v0.1 → v0.2 → v0.3), each preceded by a rubric-lens review whose critiques were encoded into the next round's prompt. Same model throughout — **prompt specificity, not model choice, drove the gains.** The method proved clean enough to extract.

## Origin & linked session
- **Originating work:** NascenTech / Haptic SBIR prep session (2026-07-01).
- **Source artifacts** (in `00 BUSINESS/00 NASCENTECH/01_STRUCTURE/grants/sbir/`):
  - `deliverables/nsf/nsf-project-pitch_draft-v0.1.md` → `…_v0.2.md` → `…_v0.3.md` (the three iterations)
  - `deliverables/nsf/reviews/review_v0.1-to-v0.2.md` and `review_v0.2-to-v0.3.md` (the review docs — working instances of the template)
- **Linked SSP:** ⚠️ **TODO — not yet created.** The Session Persistent Package for the originating session has not been generated; run `/session-save` in the main SBIR session, then record the resulting path here. Expected location: `00_COLLEVITY/03_TACTIC/claude_session-persistent-packages/2026-07-01-<HHMM>_<slug>__…`. Suggested slug: `nascentech-sbir-and-iteration-method`.

## Status
**Seeded** — initial scope + crude v1 present; spec/interview next.

## Contents
- `spec/scope.md` — initial scope: the method, the skill's surface, rubric-library concept, roadmap, open decisions.
- `deliverables/SKILL_v0.1.md` — crude v1 of the skill (manual, usable now; not yet an installed slash command).

## Next steps
1. Create + link the SSP (above).
2. Run a `/spec` interview to harden scope → `spec/spec.md` + `state.yaml` (mirrors sibling projects).
3. Promote the crude v1 into an installed skill (`/iterate-draft`) once the surface stabilizes.
