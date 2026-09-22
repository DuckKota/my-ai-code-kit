# omp-codebase-memory-init Specification

## Purpose

Defines how `setup install` initializes codebase-memory-mcp for Oh My Pi: OMP owns its MCP server declaration and reminder extension, with no overlap with the opencode setup, reconciled against a user-level denylist.

## Requirements

### Requirement: OMP owns its MCP server declaration
When `setup install --agent omp` runs inside a git repository and the `codebase-memory-mcp` binary is available, setup SHALL declare the server in the project's OMP-native MCP config (`<repo>/.omp/mcp.json`) as `mcpServers.codebase-memory-mcp` with `enabled: true` and the resolved binary path as its `command`. Setup SHALL NOT add or rely on the server declaration in any opencode config for the OMP path.

#### Scenario: OMP install declares the server in .omp/mcp.json
- **WHEN** the user runs `setup install --agent omp` inside a git repository with `codebase-memory-mcp` available
- **THEN** `<repo>/.omp/mcp.json` contains a `codebase-memory-mcp` entry under `mcpServers` with `enabled: true`
- **AND** the entry's `command` is the resolved path of the `codebase-memory-mcp` binary

#### Scenario: OMP install does not touch opencode config
- **WHEN** the user runs `setup install --agent omp`
- **THEN** no opencode config file (`.opencode/opencode.json` or project `opencode.json`) is created or modified for this install

### Requirement: OMP reminder extension installed
When `setup install --agent omp` runs inside a git repository, setup SHALL install an OMP-format reminder extension into the project's OMP-native extension root (`<repo>/.omp/extensions/`). The extension SHALL be an OMP extension module (a default-exported factory binding `pi.on("tool_result", ...)`), not the opencode hook-object format.

#### Scenario: Extension present in .omp/extensions
- **WHEN** `setup install --agent omp` completes successfully
- **THEN** a reminder extension file exists under `<repo>/.omp/extensions/`
- **AND** the file is an OMP extension module using the `tool_result` event

### Requirement: Reminder behavior is preserved
The OMP reminder extension SHALL reproduce the codebase-memory-gate behavior for Oh My Pi: detected searches are never blocked; a `[codebase-memory]` reminder is prepended to search output on the same per-session throttle; the extension is inert when the `codebase-memory-mcp` binary is not in PATH or the workspace AGENTS.md lacks the graph marker.

#### Scenario: Search nudge fires in OMP
- **WHEN** an OMP agent runs a detected search (`grep`, `glob`, or a shell search command) in a marked workspace while the graph is active
- **THEN** the tool output carries the `[codebase-memory]` reminder and the search result remains usable

#### Scenario: OMP extension is inert without marker
- **WHEN** the workspace AGENTS.md lacks the codebase-memory graph marker
- **THEN** OMP searches produce no reminder

### Requirement: Graph runtime is shared
The OMP init SHALL prepend the codebase-memory instruction block to the repo `AGENTS.md` and SHALL run `codebase-memory-mcp config set auto_index auto_watch true`, exactly as the opencode init does, so both agents read the same repo-level graph.

#### Scenario: Runtime flags set for the shared graph
- **WHEN** `setup install --agent omp` completes successfully
- **THEN** `auto_index` and `auto_watch` are enabled for the repo's codebase-memory database
- **AND** the repo `AGENTS.md` begins with the codebase-memory instruction block

### Requirement: Stale user denylist is reconciled
When the user-level OMP MCP config (`~/.omp/agent/mcp.json`, default profile) lists `codebase-memory-mcp` in `disabledServers`, setup SHALL prompt to remove the entry (the prompt is never bypassed by `--yes`). If the user declines, setup SHALL report that the OMP graph is unavailable and continue without error.

#### Scenario: Denylist entry prompts for removal
- **WHEN** `~/.omp/agent/mcp.json` contains `codebase-memory-mcp` in `disabledServers` and `setup install --agent omp` runs
- **THEN** setup asks the user whether to remove the entry
- **AND** accepting removes it, leaving the project server declaration effective

#### Scenario: Declining denylist removal reports unavailability
- **WHEN** the user declines removing the denylist entry
- **THEN** setup reports that codebase-memory is unavailable for Oh My Pi in this project
- **AND** setup continues without error and does not modify the user config

### Requirement: OMP init is idempotent
Re-running `setup install --agent omp` SHALL leave `<repo>/.omp/mcp.json`, `<repo>/.omp/extensions/`, the AGENTS.md instruction block, and the runtime flags unchanged.

#### Scenario: Re-run leaves .omp unchanged
- **WHEN** `setup install --agent omp` runs a second time on an already-initialized repo
- **THEN** no `.omp/` file content or runtime flag changes
