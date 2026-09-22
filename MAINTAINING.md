# MAINTAINING.md — tribal knowledge & provenance ledger

This document is the human record of *why* this setup exists and how it stays
current. It complements `openspec/` (which records the *design rationale* of
the setup tool itself). Here we record the *content* decisions: what each
artifact is, where it came from, what we customized on top, and how to merge
upstream changes back in.

## Usage

| Command | What it does |
| --- | --- |
| `setup install` | install managed files; remove stale symlinks; init OpenSpec + codebase-memory-mcp in a git repo (prompts first) |
| `setup install --no-init` | config farm only, skip per-project tool init |
| `setup uninstall` | tear down managed symlinks, keep your own config |

`install` prompts before removing stale symlinks (`--yes` skips the prompt,
`--force` overwrites conflicting files). `vendor` prompts before pulling
upstream changes (`--yes` skips). `uninstall` does **not** prompt: it only
removes what the tool installed (managed symlinks, exact-content copies, and
matched text blocks), so it never touches your own config. In a non-interactive
shell the prompts default to **no**.

**Keep up to date** — pull the latest release, then re-apply:

```bash
git pull
./bin/setup install --force
```

The machine-readable source of truth is `manifest.toml`. Every artifact in
that file has a `provenance` of `original`, `vendor`, or `fork`:

- **original** — ours, no upstream. `setup vendor` skips.
- **vendor** — stolen, pristine, untouched. `setup vendor` overwrites from upstream.
- **fork** — stolen + customized on top. `setup vendor` 3-way merges + reviews.

---

## Upstream index

| Upstream repo | What we take | Relationship |
| --- | --- | --- |
| [mattpocock/skills](https://github.com/mattpocock/skills) | **Commands:**<br>`/grill-me`, `/handoff`<br><br>**Skills:**<br>`diagnosing-bugs`, `codebase-design`, `domain-modeling`, `improve-codebase-architecture`, `grilling`, `writing-for-agents` | vendor |
| [obra/superpowers](https://github.com/obra/superpowers) | **Skills:**<br>`using-git-worktrees`, `verification-before-completion` | vendor |
| [shir-danishyar/humanize](https://github.com/shir-danishyar/humanize) | **Command:**<br>`/humanizer`<br><br>**Skill:**<br>`humanize-writing` | vendor |

---

## How to pull upstream changes

```bash
./bin/setup vendor   # report drift, then pull changes (prompts first)
```

`vendor` alone is enough: every vendored artifact is a plain symlink into
`src/`, so pulling updates propagates to the live config automatically. No
reinstall needed.

The non-symlink artifacts (`commit-message`'s substituted copy, the `caveman`
/ `file-edit-limits` text-inserts into AGENTS.md, `theme-default`'s
config-merge) are all `original` and never vendored. If you edit one by hand,
a plain `install` won't refresh it — use `--force`, or uninstall then install.

Behavior by provenance:

- **original** — skipped.
- **vendor** — overwritten from upstream HEAD, `source_sha` bumped.
- **fork** — 3-way merge (`git merge-file`): base = upstream at pinned
  `source_sha`, ours = our file, theirs = upstream HEAD.
  - Clean merge → applied, `source_sha` bumped.
  - Conflict → conflict markers written into the file and `source_sha` bumped
    to upstream HEAD (the revision the resolved file will be based on). A file
    that still carries markers is never re-merged — `setup vendor` reports it
    as unresolved and refuses — so repeated runs cannot nest markers. Resolve
    the markers; the next `setup vendor` then sees the artifact as up to date.
  - First fork update (no `source_sha` yet) → **pins** upstream as base and
    leaves our file untouched. This is deliberate: it never clobbers
    customizations on first run.

Rule (hard): after any successful update, `source_sha` must be bumped, or the
merge base drifts and future merges lie.

---

## Per-artifact notes

### Commands

#### grill-me — `vendor` (mattpocock)
Stolen verbatim; used as `/grill-me`. Upstream already delegates to the
`/grilling` skill rather than embedding the interview logic, so there is
nothing local to protect. See `grilling` below.

#### handoff — `vendor` (mattpocock)
Stolen verbatim; used as `/handoff`. No local changes.

#### humanizer — `vendor` (shir-danishyar/humanize)
Single-file command; cleanly vendorable. Pulls `commands/humanizer.md`
verbatim.

#### commit-message — `original`
Our `/commit-message` command + `verify-commit` validation script. The command
references the installed script path at install time.

#### fix — `original`
Our `/fix` command (renamed from `/debug`).

#### glab-mr — `original`
Our `/glab-mr` command for creating merge requests.

### Skills

#### grilling — `vendor` (mattpocock)
The interview engine `/grill-me` invokes. When upstream changes wording, the
merge should carry it in.

#### diagnosing-bugs / codebase-design / domain-modeling / improve-codebase-architecture / writing-for-agents — `vendor` (mattpocock)
Pristine copies. Nothing local to protect; overwrite freely.

#### using-git-worktrees / verification-before-completion — `vendor` (obra/superpowers)
Pristine copies.

#### glab — `original`
Our own skill for working with GitLab via `glab` CLI (mirrors the `glab-mr`
command). No upstream.

#### humanize-writing — `vendor` (shir-danishyar/humanize)
The upstream repo keeps `SKILL.md` at the repo root, so the skill can't live
in one vendorable subdir. Instead it's assembled from three vendor artifacts,
each mirroring one upstream path into `src/skills/humanize-writing/`:

- `humanize-writing` → `SKILL.md`
- `humanize-writing-references` → `references/`
- `humanize-writing-scripts` → `scripts/`

Together they install as the `skills/humanize-writing/` skill directory.
Pulling upstream changes is a plain `setup vendor`; the skill's own `tests/`
stay upstream (we don't vendor them).

#### humanizer — `vendor` (shir-danishyar/humanize)
The `/humanizer` command (`commands/humanizer.md`); installs as a slash
command. Vendored as its own single-file artifact (see Commands above).

### Themes & instructions

#### caveman — `original`
The terse "smart caveman" speaking rules, prepended to the global `AGENTS.md`.

#### file-edit-limits — `original`
The chunked-assembly rule for large file writes, appended to `AGENTS.md`.

#### oc-github-dark — `original`
Our own GitHub-dark theme. Not the default anymore; kept as a fallback theme
(`themes/oc-github-dark.json`).

#### poimandres / poimandres-turquoise-expanded / poimandres-accessible — `vendor`
Vendored from [ajaxdude/opencode-ai-poimandres-theme](https://github.com/ajaxdude/opencode-ai-poimandres-theme)
(`.opencode/themes/*.json`). `poimandres-turquoise-expanded` is the default
and sets `theme` in `tui.json`. The Oh My Pi equivalent
is `omp-github-dark` (installed as `themes/github-dark.json`; selected via a
`config-merge` into `config.yml`).

### Per-project

#### OpenSpec — `original`
Per-project, set up by `ocinit` (not the manifest — see `setup install`
running inside a git repo). `ocinit.py` runs `openspec init --tools opencode`
in the repo root. Idempotent.

#### codebase-memory-reminder / codebase-memory-mcp — `original`
Both are per-project, set up by `ocinit` (not the manifest — see
`setup install` running inside a git repo). `ocinit.py` prepends the
codebase-memory instructions to `AGENTS.md`, copies
`CodebaseMemoryReminder.ts` into `.opencode/plugins`, and merges the MCP
server into `.opencode/opencode.json`, then sets `auto_index` / `auto_watch`.
