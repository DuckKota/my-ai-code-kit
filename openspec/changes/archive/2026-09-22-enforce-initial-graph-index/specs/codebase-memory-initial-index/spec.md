# codebase-memory-initial-index Specification

## ADDED Requirements

### Requirement: Initial graph index on first install
When `setup install` runs inside a git repository and the `codebase-memory-mcp` binary is available, setup SHALL index the repository's codebase-memory graph synchronously in `full` mode. Setup SHALL skip the index when the project is already indexed. Setup SHALL NOT fail or abort `setup install` when the index fails.

#### Scenario: First install indexes the repo
- **WHEN** the user runs `setup install` in a git repository whose codebase-memory graph is not yet indexed and the `codebase-memory-mcp` binary is available
- **THEN** setup prints an indexing progress line
- **AND** setup runs `index_repository` in `full` mode against the repository root
- **AND** on success, `index_status` reports the project as indexed

#### Scenario: Re-run skips when already indexed
- **WHEN** `setup install` runs again on a project whose codebase-memory graph is already indexed
- **THEN** setup does not re-run `index_repository`
- **AND** setup reports that the graph is already indexed

#### Scenario: Index failure does not fail install
- **WHEN** `index_repository` exits non-zero during `setup install`
- **THEN** setup prints a warning that the index failed
- **AND** setup continues and completes the install without error

### Requirement: Index is shared across agents
The initial graph index SHALL run once per repository and SHALL be shared by both the opencode and Oh My Pi installs, since the graph database is repo-level.

#### Scenario: One index serves both agents
- **WHEN** `setup install` is run for the opencode agent and then for the Oh My Pi agent in the same repository
- **THEN** the index runs on the first install
- **AND** the second agent's install skips the index because the graph is already indexed
