## 1. Implement the initial index

- [x] 1.1 Add `_initial_index(root: Path, mcp_bin: str) -> None` in `src/project.py`: gate on `index_status --project <root.name>` (exit 0 → skip with "already indexed"), else print a progress line and run `index_repository --repo-path <root> --mode full`
- [x] 1.2 On index success print "codebase-memory graph indexed"; on non-zero exit print a warning with the re-run hint and continue (no exception)
- [x] 1.3 Call `_initial_index` once in `init_project` after `if not mcp_bin: return`, before the opencode/omp branch (agent-agnostic, shared)

## 2. Tests

- [x] 2.1 `_initial_index` skips when `index_status` exits 0 (no `index_repository` call, "already indexed" printed)
- [x] 2.2 `_initial_index` indexes when `index_status` exits 1 (calls `index_repository --repo-path <root> --mode full`)
- [x] 2.3 `_initial_index` warns and does not raise when `index_repository` exits non-zero
- [x] 2.4 `init_project` invokes `_initial_index` once for both `opencode` and `omp` (monkeypatched `_ensure_tool`/`subprocess.run`)
- [x] 2.5 Idempotency: a second `init_project` run skips indexing (status exit 0)

## 3. Verification

- [x] 3.1 Full test suite + mypy + pylint pass
- [x] 3.2 Live: temp git repo → `setup install --agent omp` → `codebase-memory-mcp cli index_status --project <name>` reports indexed
- [x] 3.3 Live: re-running `setup install` prints "already indexed" and returns fast
- [x] 3.4 `openspec validate --changes` + `openspec doctor` pass
