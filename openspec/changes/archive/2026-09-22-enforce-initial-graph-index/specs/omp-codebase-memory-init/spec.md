# omp-codebase-memory-init Specification

## MODIFIED Requirements

### Requirement: Graph runtime is shared
The OMP init SHALL prepend the codebase-memory instruction block to the repo `AGENTS.md` and SHALL run `codebase-memory-mcp config set auto_index auto_watch true`, exactly as the opencode init does, so both agents read the same repo-level graph.

#### Scenario: Runtime flags set for the shared graph
- **WHEN** `setup install --agent omp` completes successfully
- **THEN** `auto_index` and `auto_watch` are enabled for the repo's codebase-memory database
- **AND** the repo `AGENTS.md` begins with the codebase-memory instruction block

#### Scenario: Shared graph is indexed once on first init
- **WHEN** `setup install --agent omp` runs on a project whose codebase-memory graph is not yet indexed
- **THEN** the repo-level graph is indexed (per the `codebase-memory-initial-index` capability)
- **AND** a subsequent `setup install --agent opencode` on the same repo skips indexing because the graph is already indexed
