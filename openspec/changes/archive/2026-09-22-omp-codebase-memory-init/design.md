## Context

`src/project.py:init_project` initializes per-project tools for `setup install`. Today, after OpenSpec init, the codebase-memory path runs only for `agent == "opencode"`: it prepends the instruction block to `AGENTS.md`, copies `CodebaseMemoryReminder.oc.ts` to `.opencode/plugins/`, merges the MCP server into `.opencode/opencode.json`, and runs `codebase-memory-mcp config set auto_index auto_watch true` (a repo-level sqlite, shared across agents). For `omp`, `init_project` returns after OpenSpec, so Oh My Pi gets no codebase-memory wiring.

Oh My Pi (OMP, v18+) has its own extension and MCP systems:

- Extensions are modules in `<cwd>/.omp/extensions/*.{ts,js}` (native auto-discovery) that default-export a factory `(pi) => void` binding events with `pi.on(...)`. The post-tool mutation event is `tool_result` (analogue of opencode's `tool.execute.after`); a handler returns `{ content?: ..., details?: ..., isError?: ... }` to override tool output, and receives `event.toolName`, `event.input`, `event.content`, `event.isError`, and `ctx.cwd`.
- MCP servers are declared OMP-natively in `<cwd>/.omp/mcp.json` (top discovery priority) as `mcpServers.<name> = { enabled, command }`. OMP also *discovers* servers from opencode.json, but the user-level `~/.omp/agent/mcp.json` `disabledServers` denylist outranks every source. The user's machine currently denies `codebase-memory-mcp` there.

## Goals / Non-Goals

**Goals:**
- Give Oh My Pi its own, OMP-native codebase-memory initialization: a ported reminder extension in `.omp/extensions/` and an OMP-owned MCP server declaration in `.omp/mcp.json`.
- Keep zero config overlap with the opencode setup: no OMP wiring written into `.opencode/`, no reliance on opencode.json discovery for OMP's server.
- Reconcile the user-level denylist that would otherwise hide the server, with a prompt (user-global change).
- Preserve the shared repo-level graph: AGENTS.md instruction prepend and `auto_index`/`auto_watch` flags stay shared, since both agents read the same repo AGENTS.md and the same graph database.

**Non-Goals:**
- Rewriting the opencode plugin or its config path.
- Moving the shared graph database per agent (one knowledge graph per repo is the point).
- Package-publishing the OMP extension to npm / `omp plugin install`; a project-local file suffices.
- Handling OMP profiles (`--profile`) beyond the default agent dir; project `.omp/mcp.json` is profile-independent by OMP design.

## Decisions

**Decision: OMP declares the MCP server in `<repo>/.omp/mcp.json`.**
Write `mcpServers.codebase-memory-mcp = { enabled: true, command: <resolved mcp bin path> }`, idempotently merging like the opencode path does. Rationale: `.omp/mcp.json` is OMP-native and the highest-precedence MCP source, so OMP owns the definition and never needs opencode.json for it. Alternative considered: enabling via `enabledServers` in the user file — rejected, it is a user-global edit and still depends on the opencode-discovered entry (overlap).

**Decision: OMP reminder extension installs to `<repo>/.omp/extensions/CodebaseMemoryReminder.ts`.**
The ported extension is installed there (auto-discovered by OMP at launch) under the canonical name `CodebaseMemoryReminder.ts`, regardless of the source variant. It is a distinct source file (`.omp.ts`) sharing the detection/throttle/arming logic with the opencode plugin. Rationale: `.omp/extensions/` is the native project root; placing it there (not `.opencode/plugins/`) keeps the two agents' config fully separate, and the canonical install name keeps the harness-facing plugin file clean.

**Decision: Port uses the `tool_result` hook.**
`pi.on("tool_result", ...)` prepends the reminder by returning `{ content: [chunk, ...original] }` for detected `grep`/`glob`/`bash` calls, using `ctx.cwd` for the AGENTS.md arming check. This mirrors the opencode `tool.execute.after` behavior. Rationale: it is OMP's documented post-execution mutation point; the opencode hook-object shape is not loadable by OMP.

**Decision: Denylist reconciliation is prompted, user-global.**
When `~/.omp/agent/mcp.json` (default profile) lists `codebase-memory-mcp` in `disabledServers`, setup prompts to remove it using the existing `confirm` callback (never bypassed by `--yes`). Declining skips and reports that OMP's graph is unavailable. Rationale: a denylist entry silently outranks the project declaration, so without handling it the feature is inert on this machine; but it is a user-global file, so it must be an explicit choice. Alternative considered: writing to the user file silently — rejected (persistent user-controlled change).

**Decision: AGENTS.md prepend and runtime flags stay shared.**
The instruction block and `config set auto_index auto_watch true` run for OMP exactly as for opencode. Rationale: AGENTS.md is a repo file both agents read, and the graph database is repo-level; duplicating per agent would fork the graph.

## Risks / Trade-offs

- The ported extension is unverified against OMP's exact `tool_result` content chunk shape → mitigation: verify live in an OMP session during implementation (tasks.md); the return-shape contract is documented and stable.
- `ctx.cwd` may not equal the repo root in multi-workspace (`--add-dir`) sessions → mitigation: accept the documented `ctx.cwd`/`process.cwd()` behavior; the arming check tolerates a missing AGENTS.md by staying inert, same as the opencode plugin.
- The user-level denylist file may be profile-specific on this machine → mitigation: target the default `~/.omp/agent/mcp.json`, the documented default profile path; note that a custom profile requires manual removal.
- `.omp/mcp.json` gets a literal absolute binary path; if the mcp binary moves, the entry goes stale → mitigation: same trade-off already accepted in the opencode `.opencode/opencode.json` entry.

## Migration Plan

Add `src/plugins/CodebaseMemoryReminder.omp.ts` (OMP-format port). In `src/project.py`, restructure `init_project` so the mcp binary is ensured for both agents, then branch: opencode keeps today's path; OMP prepends AGENTS.md, installs the extension to `.omp/extensions/`, writes `.omp/mcp.json`, runs the runtime flags, and reconciles the denylist. Verify in a real OMP session: `/mcp list` shows codebase-memory-mcp from `.omp/mcp.json`, a search triggers the reminder nudge, and re-running `setup install` is a no-op. No rollback concerns — per-project files, idempotent writes.
