## Why

`setup install --agent omp` initializes OpenSpec but leaves codebase-memory-mcp out entirely: `init_project` returns before the codebase-memory path for any agent other than opencode. When an Oh My Pi user happens to see the graph MCP tools, they only appear because OMP auto-discovers the server from the project's opencode config — shared, overlapping wiring that OMP does not own and that `setup` never reconciles. Oh My Pi agents get neither the knowledge graph nor the reminder that nudges them toward it.

## What Changes

- Port the `CodebaseMemoryReminder` reminder plugin to OMP's extension format: a default-exported `(pi) => void` factory binding `pi.on("tool_result", ...)`, typed against `@oh-my-pi/pi-coding-agent/extensibility/hooks`. The search-detection, throttle, and arming logic carries over unchanged.
- Install the OMP reminder extension into the project's OMP-native extension root (`<repo>/.omp/extensions/`), so OMP auto-discovers it. It is not placed in `.opencode/` — no config overlap with opencode.
- Declare the codebase-memory-mcp server in OMP's own config file (`<repo>/.omp/mcp.json`, the top-priority OMP-native MCP source), `enabled: true`, with the resolved binary path. OMP stops relying on opencode.json discovery for this server.
- Reconcile a stale user-level denylist: if `~/.omp/agent/mcp.json` lists `codebase-memory-mcp` in `disabledServers` (which outranks every source), setup prompts to remove it; declining leaves it and reports the graph unavailable for OMP.
- Keep the shared, agent-agnostic pieces as-is: the AGENTS.md instruction prepend and `auto_index`/`auto_watch` runtime flags, both of which already target the repo-level graph database shared by both agents.

## Capabilities

### New Capabilities
- `omp-codebase-memory-init`: Defines how `setup install` initializes codebase-memory-mcp for Oh My Pi — OMP-owned MCP server config, an OMP-format reminder extension, and denylist reconciliation — with no overlap with the opencode setup.

### Modified Capabilities
<!-- No existing spec-level requirements change. The `codebase-memory-gate` spec is agent-agnostic and continues to govern the reminder behavior; the OMP port preserves it. -->

## Impact

- `src/project.py`: split the codebase-memory init into opencode and OMP paths; add `.omp/mcp.json` writer and `.omp/extensions/` installer; denylist reconciliation with the existing `confirm` callback.
- `src/plugins/CodebaseMemoryReminder.omp.ts`: new OMP-format extension (port of `CodebaseMemoryReminder.oc.ts`).
- `src/kit.py`: `init_project` already receives `agent` and `confirm`; OMP init now proceeds past the openspec step. No dispatch change.
- `tests/test_oc.py`: new tests for `.omp/mcp.json` writing, `.omp/extensions/` install, and denylist reconciliation.
- No changes to OpenSpec init, the opencode plugin, or the codebase-memory-mcp server itself.
