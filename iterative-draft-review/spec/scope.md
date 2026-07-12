# iterative-draft-review — Initial Scope (v0.1)

*Seeded 2026-07-01. This is a crude scope to be hardened via `/spec` later. Kept intentionally revisable.*

## Problem
Producing a genuinely strong written deliverable (grant pitch, spec, memo) usually takes several rounds of "write, react, rewrite." Done ad hoc, the improvement is invisible and non-transferable — you can't tell whether the draft got better because of editing, the model, or luck, and none of the learning carries to the next document. We want a **repeatable, legible** process that produces better drafts *and* a reusable asset.

## The method: Rubric-Anchored Blind Iteration
**Loop:**
1. **Draft** — an agent writes v_N from a *grounded* prompt (source files + rules/limits fetched, not recalled).
2. **Review** — critique v_N against an **explicit rubric**, producing a numbered list of specific, addressable weaknesses.
3. **Refine the prompt** — encode each critique as an instruction, and **carry the prior version's wins forward as hard requirements** so the next pass can't regress. The prompt becomes a growing spec.
4. **Blind rewrite** — a fresh agent writes v_N+1 *without seeing v_N*, model held constant, so the **prompt is the only variable**.
5. **Graduation test** — stop when remaining gaps are *content decisions* (facts only the human can supply), not craft problems.

**Principles that make it work:**
- Rubric is the standard (judge against real criteria, not taste).
- Blind rewrite isolates the variable + prevents anchoring. *Trade-off:* at high maturity, switch to targeted revision to avoid regressing a strong draft.
- Accumulate the standard in the prompt (prior wins as requirements + new fixes).
- Build in traceability (endnotes citing which rule/source drove each choice) and constraint self-checks (limits, counts).
- Prompt specificity > model choice.

## Skill scope
**In scope:**
- Orchestrating the loop for one deliverable at a time.
- A **reusable prompt scaffold** (fill-in template) for the drafting agent.
- A **review-doc template** (critique table → prompt refinements → scorecard → verdict → diminishing-returns check → meta-lesson).
- A small **rubric library** (one rubric per deliverable type), grown over time.
- The **graduation test** as an explicit stop condition.

**Out of scope (for now):**
- Automated quality scoring / eval harness (future).
- Multi-deliverable batch orchestration.
- Anything requiring the human's content decisions (the loop *surfaces* these, doesn't invent them).

## Proposed skill surface
- Command: `/iterate-draft <deliverable> [--rubric <name>] [--round N] [--mode blind|revise]`
- Inputs: source material paths, the rubric (named from library or inline), prior version (only in `revise` mode), output path.
- Outputs: v_N+1 draft (with endnotes + self-checked constraints) + a review doc for the N→N+1 transition.

## Rubric library (the real durable asset)
`rubrics/` (future): e.g., `nsf-project-pitch.md`, `nih-specific-aims.md`, `commercialization-plan.md`, `cover-letter.md`. Each rubric = the explicit criteria a deliverable of that type is judged against. Seed it from the NSF-pitch review docs already written.

## Roadmap
- **v0.1 (now):** crude, manual skill doc — run the loop by hand with the scaffold. See `deliverables/SKILL_v0.1.md`.
- **v0.2:** harden via `/spec`; extract the first real rubric (NSF pitch) from the existing review docs; template the review doc.
- **v1.0:** installed `/iterate-draft` skill + rubric library; blind/revise modes; auto constraint-checks.

## Carrying forward — balancing immediate delivery vs. long-term flexibility
- **Ship crude now, harden later.** v0.1 is usable today by hand; don't block on the full skill. (This scope doc + SKILL_v0.1 = the immediate deliverable.)
- **Separate the stable core from the growing edges.** The *loop* is stable; the *rubrics* grow. Keep rubrics as data files, not baked into the skill logic — that's what keeps it flexible/revisable.
- **Treat every real use as a rubric contribution.** Each deliverable you run through it should leave behind (or improve) a rubric. The library compounds.
- **Keep it model-agnostic.** The value is the prompt/rubric, not a model; don't hard-code a model choice.
- **Version the prompt scaffold and rubrics** so revisions are legible (same discipline that made the method work is how the skill itself should evolve).

## Open decisions (for the `/spec` pass)
1. Blind-vs-revise default, and when to auto-switch to revise (maturity heuristic).
2. Where the rubric library lives (in this repo vs. a shared skills dir).
3. Whether v1.0 is a Claude Code skill, a CLI, or both.
4. How tightly to couple the review-doc output to the loop (always emit one, or optional).
