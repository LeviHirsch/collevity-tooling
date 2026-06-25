# GIT-RUNBOOK — collevity-tooling

How git works *in this repo specifically*. Two things make it non-standard: (1) it's a **monorepo** (many projects, one history), and (2) it uses the **iCloud-safe external-gitdir** pattern. Everything below accounts for both.

---

## 1. The mental model: one repo, many folders

`dropper-pipeline/` and `claude-account-switcher/` are **not** separate repos anymore. There is **one** `.git`, **one** history, **one** remote, **one** `main` branch. A single commit can touch both folders.

What that changes in practice:
- `git status` / `git log` show **everything**, across all projects.
- To work on just one project, **scope by path** — git doesn't restrict you to a subfolder automatically.

```sh
git add claude-account-switcher/         # stage only this project's changes
git commit -m "switcher: ..."            # prefix the message with the project, by convention
git log -- dropper-pipeline/             # history touching only this project
git diff -- claude-account-switcher/     # diff only this project
```

There is no per-project branch or per-project push. You push the whole repo or nothing.

## 2. The iCloud-safe layout (why `.git` is a *file*)

iCloud corrupts live `.git` **directories** as it syncs them. So the real git directory lives **outside** iCloud:

```
working tree (iCloud):  .../02_CONTENT/collevity-tooling/
real git dir (local):   /Users/levi/dev/collevity/collevity-tooling.git
link:                   the .git file contains  →  gitdir: /Users/levi/dev/collevity/collevity-tooling.git
```

You don't have to do anything special day-to-day — git follows the pointer automatically. Just **never** delete `/Users/levi/dev/collevity/collevity-tooling.git` (that's your actual history) and **never** convert `.git` back into a folder.

## 3. Everyday commands

```sh
# where am I / what changed
git status

# stage + commit one project's work
git add claude-account-switcher/
git commit -m "switcher: add slot-creation script"

# stage everything
git add -A && git commit -m "..."

# send it up (first push needs -u to set the upstream)
git push -u origin main      # first time
git push                     # after that
```

Identity is already set globally (`Levi Hirsch <dorkingham@gmail.com>`), so commits are attributed correctly with no extra flags.

> When **Claude Code** makes a commit for you, it appends `Co-Authored-By:` / `Claude-Session:` footer lines. That's expected and only happens on Claude-authored commits — your own `git commit` won't add them.

## 4. How dropper-pipeline got here (for reference)

Migrated **with history** using a subtree import, so `git log -- dropper-pipeline/` still shows its full past:

```sh
git subtree add --prefix=dropper-pipeline /Users/levi/dev/collevity/dropper-pipeline.git main
```

You won't normally re-run this. The old standalone repo (`/Users/levi/dev/collevity/dropper-pipeline.git` + the `collevity-dropper-pipeline` GitHub repo) is kept as an **archive** until you say to remove it.

## 5. Publishing a public release repo (export model)

The public tool repo is built **clean** from a project's `deliverables/` — none of this private history is exposed. Outline (fill in when the first deliverable is ready):

```sh
# one-time: create the public repo on GitHub (e.g. claude-account-switcher), then:
PUB=~/dev/public/claude-account-switcher          # a separate clone of the PUBLIC repo
rsync -a --delete \
  "claude-account-switcher/deliverables/" "$PUB/" # copy only the deliverable
cd "$PUB" && git add -A && git commit -m "release: <version>" && git push
```

The public repo's name is the **tool** name (`claude-account-switcher`), never "deliverables". Because the public history is built by copy, there is zero risk of a private commit leaking through.

## 6. Safety rules

- Don't delete the external git dir under `/Users/levi/dev/collevity/`.
- Don't commit secrets/tokens — `.gitignore` already blocks `.env`, `.credentials.json`, `*.token`. Auth state belongs in `CLAUDE_CONFIG_DIR` slots, never in the repo.
- Verify before deleting any archive (old per-project repos) — they're your fallback until the monorepo is proven.
