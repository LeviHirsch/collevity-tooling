---
name: iterate-draft
description: Produce a high-quality written deliverable via Rubric-Anchored Blind Iteration — draft, review against an explicit rubric, refine the prompt, blind-rewrite, repeat until diminishing returns. Use for grant pitches, specs, memos, cover letters, or any judged written artifact.
status: crude v0.1 (manual; not yet an installed slash command)
---

# Skill: iterate-draft (crude v0.1)

**Run this loop by hand for now.** It is deliberately manual until the surface stabilizes.

## When to use
Any written deliverable judged against an external standard, where you want the draft to measurably improve *and* to leave behind a reusable rubric.

## Inputs to gather — none need to pre-exist
Each input has a **fallback chain**; the skill does **not** require pre-made rubric or resource docs.
- **Source material** (what the draft draws from): provided files/paths → else the user's brief / this conversation → else the agent researches it. Any grounding works.
- **Ground-truth rules** (limits, required sections, format): fetch from the authoritative source (funder page, style guide) → else infer sensible defaults and state them explicitly.
- **Rubric** (how "good" is judged): a rubric from the library → else **derive one** (step 0, not a prerequisite): pull the real criteria from an authoritative source, or synthesize from first principles (purpose, audience, what this document type rewards/rejects), or ask the user for the 3–5 things that matter.
- **Output path**.

## The loop
### 1. Draft (v_N) — use the prompt scaffold below
### 2. Review v_N against the rubric
Produce a **numbered critique**: each item = a specific, addressable weakness tied to a rubric criterion. Capture it in a review doc (template below).
### 3. Refine the prompt
- Turn each critique into an explicit instruction.
- **Carry every prior-version win forward as a hard requirement** (so the rewrite can't regress).
### 4. Blind rewrite (v_N+1)
- Fresh agent, **does not see v_N**, **same model** (prompt is the only variable). Output to a new versioned file.
### 5. Graduation test — STOP when
Remaining critiques are **content decisions only the human can make** (missing facts, unnamed people, real numbers) rather than craft problems. Three rounds is often enough.

> Maturity note: once a draft is strong, switch step 4 from *blind* to *targeted revision* to avoid regressing hard-won gains.

---

## Prompt scaffold (for the drafting agent)
```
You are drafting <DELIVERABLE> from scratch. Write the final artifact to disk yourself.
[WRITE BLIND: do not open/reference any prior draft at <paths>. Output to <new versioned path>.]

# Source material (read these)
<absolute file paths>

# Ground-truth rules (WebFetch — do not rely on memory)
<authoritative URLs for limits/required sections/format>

# How this is judged (the RUBRIC)
<the explicit criteria; what the reviewer/funder rewards and rejects>

# Accumulated requirements (prior wins — all MUST be met)
<the standard, carried forward every round>

# This round's fixes
<each critique from the last review, as an instruction>

# Constraints + self-check
<hard limits; report counts/limits after each section; leave ~10% headroom>

# Traceability
Insert numbered endnotes citing which rule/source drove each choice; collect them at the end.

# Output
<paths>. After writing, summarize: constraint compliance, how you handled <the hard problems>, open questions for the team.
```

## Review-doc template
```
# <Deliverable> — Review Notes: v_N → v_N+1
## Purpose        (what was reviewed; blind or revise)
## The lens       (the rubric)
## Critiques of v_N   (numbered table: # | weakness | why it matters)
## Prompt refinements applied
## Evaluation of v_N+1 (scorecard: # | critique | result ✅/⚠️)
## What v_N did that v_N+1 dropped (and why that's right)
## Residual / content decisions (the graduation-test items)
## Constraint/count evolution (table across versions)
## Meta-lesson
```

## Generality & when (not) to use
**General to essentially any document.** The loop is type-agnostic; only the *rubric* and *ground-truth rules* specialize per document — and both are pluggable/derivable (see fallback chain above). SBIR just happened to have a *published* rubric (NSF's criteria); a blog post, cover letter, spec, landing page, or email works identically with a **derived** rubric.
- **Best fit:** anything where "good" is *definable*, even implicitly.
- **Softer fit:** purely subjective/creative work — still works; judge against a self-defined rubric (purpose, audience, voice, clarity).
- **Skip / go light:** trivial or very short docs — graduate after v1, or use `revise` mode for a single round; the multi-round loop is overhead you don't need.

## Reference implementation
The two review docs at `…/01_STRUCTURE/grants/sbir/deliverables/nsf/reviews/` are working instances of the review template; the three `nsf-project-pitch_draft-v0.*.md` files show the draft progression. Reuse them as worked examples.
