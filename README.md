# collevity-tooling
*Private monorepo for Collevity's buildable dev projects. Seeded 2026-06-24.*

This repo is the **workshop**: it holds the full working state of each tooling project — specs, drafts, notes, and deliverable source. It is **private** and is the single source of truth.

Named `collevity-tooling` (not `collevity`) deliberately: it scopes to *code/projects only* and leaves room for future sibling Collevity repos. It does **not** track the personal Collevity context system (Apple Notes, Dropper `.xlsm`, strategy docs) — those stay outside git.

## Projects

| Folder | What it is | Status |
|---|---|---|
| `dropper-pipeline/` | capture → store → ingest → thread pipeline; first joint S3/A3 test | active — part 1 built (iter 2 merged 07-11); hook Phase-1 code merged, spec in-review, not installed; see its `PROGRESS.md` |
| `claude-account-switcher/` | concurrent multi-account Claude Code tooling | built + verified (v1, phase 4 audit 07-01; OAuth-URL fix landed) |
| `iterative-draft-review/` | Rubric-Anchored Blind Iteration — reusable method/skill for judged written deliverables | seeded 2026-07-01; spec next |
| `records-filer/` | records filing skill + watcher (scoping) | seeded; uncommitted — WATCHER-SCOPING.md open |

## Public releases

Each shareable tool is published as its **own standalone public repo** (e.g. `claude-account-switcher`) by **exporting** that project's `deliverables/` into a purpose-built public repo. Nothing in this private monorepo's history is ever exposed; the public repo is built clean. See `GIT-RUNBOOK.md`.

## Working with this repo

It uses the iCloud-safe pattern: the working tree lives in iCloud, the real git directory lives **outside** iCloud at `/Users/levi/dev/collevity/collevity-tooling.git`, linked by the `.git` *file* (a `gitdir:` pointer, not a directory). `GIT-RUNBOOK.md` explains the everyday commands and how they're adjusted for this setup.

## Conventions
- One history, one remote, one branch (`main`). Projects are folders, not sub-repos — scope your work with paths (`git add claude-account-switcher/`, `git log -- dropper-pipeline/`).
- Committer: `Levi Hirsch <dorkingham@gmail.com>`.
