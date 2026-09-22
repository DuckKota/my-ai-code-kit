## 1. Port the reminder plugin to OMP format

- [x] 1.1 Create `src/plugins/CodebaseMemoryReminder.omp.ts`: default-exported `(pi: HookAPI) => void` factory, `pi.on("tool_result", ...)`, typed against `@oh-my-pi/pi-coding-agent/extensibility/hooks`
- [x] 1.2 Reuse detection logic unchanged: native `grep`/`glob` tool names plus shell search detection (`isShellSearchCommand`), armed only when the binary is in PATH and the workspace AGENTS.md carries the graph marker (resolve AGENTS.md from `ctx.cwd`)
- [x] 1.3 Implement the nudge: return `{ content: [...] }` with the `[codebase-memory]` reminder prepended to the first text chunk
- [x] 1.4 Preserve the per-session throttle (first 2, then every 10th search); skip error results (`event.isError`)

## 2. Wire OMP codebase-memory init into `init_project`

- [x] 2.1 Restructure `init_project` to ensure the mcp binary for both agents before branching (opencode vs omp)
- [x] 2.2 For OMP: prepend the AGENTS.md instruction block (shared with opencode)
- [x] 2.3 For OMP: install `CodebaseMemoryReminder.omp.ts` to `<repo>/.omp/extensions/`
- [x] 2.4 For OMP: write `<repo>/.omp/mcp.json` declaring `mcpServers.codebase-memory-mcp = { enabled: true, command: <resolved bin> }`, idempotently preserving an existing user entry
- [x] 2.5 For OMP: run `codebase-memory-mcp config set auto_index auto_watch true` (repo-level, shared)
- [x] 2.6 For OMP: if `~/.omp/agent/mcp.json` denies `codebase-memory-mcp` in `disabledServers`, prompt to remove it via the `confirm` callback (never bypassed by `--yes`); on decline, report the graph unavailable for OMP

## 3. Tests

- [x] 3.1 Unit test: OMP init writes `.omp/mcp.json` with the enabled server and the resolved binary command
- [x] 3.2 Unit test: OMP init installs the extension under `.omp/extensions/`
- [x] 3.3 Unit test: OMP init does not touch `.opencode/` (no overlap)
- [x] 3.4 Unit test: denylist entry in `~/.omp/agent/mcp.json` triggers a prompt; accept removes it, decline leaves it and reports unavailability
- [x] 3.5 Idempotency: a second `setup install --agent omp` leaves `.omp/` unchanged

## 4. Verification

- [x] 4.1 Full test suite + mypy + pylint pass
- [x] 4.2 Live OMP session: `/mcp list` shows codebase-memory-mcp sourced from `.omp/mcp.json`, not opencode.json
- [x] 4.3 Live OMP session: a `grep`/`glob`/shell search on a marked repo produces the reminder nudge with the throttle applied
- [x] 4.4 Confirm opencode config is untouched after an OMP install
