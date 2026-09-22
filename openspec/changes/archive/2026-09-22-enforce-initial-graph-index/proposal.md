## Why

`setup install` never builds the codebase-memory graph. It writes the AGENTS.md instructions, installs the reminder plugin, registers the MCP server, and sets `auto_index`/`auto_watch=true` — but nothing calls `index_repository`. `index_status` confirms the result: a freshly initialized project reports "No projects indexed yet. Call index_repository first." Agents get the graph *tools* with an empty graph until something indexes the repo, so the first `search_graph`/`trace_path` calls are useless or silent.

## What Changes

- On first `setup install` in a repo, synchronously index the codebase-memory graph once, in `full` mode.
- Gate on `index_status`: skip the index when the project is already indexed, keeping re-runs of `setup install` a cheap no-op.
- Run the index once per project, shared by both agents (the graph DB is repo-level).
- Make the index best-effort: a failed index warns and continues; install still succeeds.
- Print a progress line so a long synchronous index doesn't look hung.

## Capabilities

### New Capabilities
- `codebase-memory-initial-index`: Governs the initial codebase-memory graph index performed by `setup install` — synchronous, idempotent, best-effort, and shared across agents.

### Modified Capabilities
- `omp-codebase-memory-init` (*Graph runtime is shared*): extended to state that the repo-level graph is indexed once on first init and shared by both agents.

## Impact

- `src/project.py`: add `_initial_index(root, mcp_bin)` and call it once in `init_project` after the mcp binary is ensured (agent-agnostic).
- `tests/test_oc.py`: tests for the skip/already-indexed gate, the index invocation, the failure path, and the shared-across-agents call.
- No changes to the reminder plugins, `.omp/mcp.json`, denylist reconciliation, or the codebase-memory-mcp server itself.
