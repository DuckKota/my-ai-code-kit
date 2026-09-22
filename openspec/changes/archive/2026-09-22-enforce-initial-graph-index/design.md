## Context

`src/project.py:init_project` initializes per-project tools for `setup install`. For codebase-memory-mcp it prepends the AGENTS.md instruction block, installs the reminder plugin (opencode → `.opencode/plugins/`, omp → `.omp/extensions/`), registers the MCP server (`.opencode/opencode.json` or `.omp/mcp.json`), and runs `codebase-memory-mcp config set auto_index auto_watch true`. It never invokes `index_repository`, so the graph stays empty until something indexes it.

Verified CLI facts:
- `codebase-memory-mcp cli index_repository --repo-path <path> [--mode full|moderate|fast]` builds the graph; `auto_index`/`auto_watch` flags alone do not index.
- `codebase-memory-mcp cli index_status --project <name>` exits **0 when indexed, 1 when not** — a usable gate signal.
- The project name passed to `index_status` is the repo basename (`root.name`), matching `index_repository`'s derived name for normal paths.
- Indexing can fail mid-run (observed `index.supervisor.worker_failed`, exit 1, contained) — the index must be best-effort.

## Goals / Non-Goals

**Goals:**
- Build the graph on first `setup install`, so agents get a usable graph immediately.
- Keep `setup install` idempotent: re-runs skip the index when already indexed.
- Index once per repo, shared by both agents (repo-level DB).
- Fail soft: an index error warns and continues.

**Non-Goals:**
- Adding `--persistence`/`--name` flags (YAGNI; name is derived from repo path).
- Adding a timeout knob for the index (settled: no timeout).
- Changing the reminder plugins, MCP config, or denylist logic.
- Triggering an index for cross-repo intelligence.

## Decisions

**Decision: Synchronous, with a progress line.**
`setup install` runs `index_repository` to completion before finishing, printing "indexing codebase-memory graph (full mode)..." first. Rationale: "enforce" only means anything if the index actually runs; background/deferred both make the graph racy when the first session searches. The progress line keeps a long index from looking hung.

**Decision: Gate on `index_status` (only-if-absent).**
Run `index_status --project <root.name>`; exit 0 → skip ("already indexed"); exit 1 → index. Rationale: preserves the current idempotent/no-op contract of `setup install`; "initial" literally means first time.

**Decision: Best-effort failure (warn + continue).**
If `index_repository` exits non-zero, print a warning (with the re-run hint) and continue; install still succeeds. Rationale: matches the existing `project.py` report-and-continue convention, and the error is recoverable by re-running install.

**Decision: `full` mode.**
Pass `--mode full`, parity with the graph normal usage builds. If real-world big-repo time becomes a complaint, drop to `moderate` as a later knob.

**Decision: Shared, agent-agnostic call.**
Call `_initial_index` once in `init_project` after the mcp binary is ensured, before the opencode/omp branch. Rationale: the graph DB is repo-level and shared; one index serves both agents, and the `index_status` gate makes the second agent's install skip.

**Decision: No timeout on the index.**
The sync index waits it out. Rationale: a timeout that kills a slow-but-healthy index defeats enforcement and leaves a partial graph; a genuinely stuck index is surfaced by the warn-and-continue path.

## Risks / Trade-offs

- A `full` index on a large repo can take minutes, making `setup install` slow → mitigation: progress line; if it becomes a real problem, move to `moderate` or background with a completion check.
- `index_status` project-name derivation could mismatch `index_repository` on unusual paths (non-ASCII/unsafe chars) → worst case is one redundant re-index, which is safe.
- A stuck (never-completing) index could hold install indefinitely → accepted per the no-timeout decision; surfaced only by user observation. Revisit with a generous timeout if this materializes.
- An index that crashes leaves a partial graph → best-effort warn + continue; re-running install retries.

## Migration Plan

Add `_initial_index(root, mcp_bin)` in `src/project.py` and call it once in `init_project` after the per-agent init (opencode/omp) completes, so the AGENTS.md and per-agent config files are part of the indexed graph. Add unit tests. Verify live: temp git repo → `setup install --agent omp` → `index_status` reports indexed; re-run install prints "already indexed" and returns fast. No rollback concerns — the index is idempotent and additive.
