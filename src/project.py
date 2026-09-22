"""
Per-project tool initialization: OpenSpec and codebase-memory-mcp.

Run inside a git working tree (any depth — the repo root is resolved via
`git rev-parse --show-toplevel`, so subdirectories behave the same as the
root). Every step is idempotent: safe to re-run as often as `setup install`
is. Both tools are per-project; nothing here touches the global config.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

# Marker line that opens the codebase-memory AGENTS.md instruction block;
# used to keep the prepend idempotent.
INSTRUCTION_MARKER = "<!-- codebase-memory-mcp:start -->"

OPENSPEC_INSTALL = "sudo npm install -g @fission-ai/openspec@latest"
CBM_INSTALL = (
    "curl -fsSL "
    "https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh "
    "| bash -s -- --skip-config"
)

# Bounded wait for a binary install (`npm install -g` or `curl | bash`). A
# hung network fetch would otherwise block `setup install` indefinitely.
INSTALL_TIMEOUT = 300


def git_root(cwd: Path) -> Path | None:
    """
    Return the git repository root containing cwd, or None if cwd is not
    inside a repository.

    Args:
        cwd: The working directory to resolve.

    Returns:
        The resolved repo root path, or None.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None

    return Path(result.stdout.strip()).resolve()


def _ensure_tool(
    name: str,
    bin_name: str,
    install_cmd: str,
    confirm: Callable[[str], bool],
) -> str | None:
    """
    Return the binary path for a tool, installing it (with a prompt) if
    missing.

    Args:
        name: Display name of the tool.
        bin_name: Executable name on PATH.
        install_cmd: Shell command that installs the tool.
        confirm: Prompt callback returning True to proceed.

    Returns:
        The resolved binary path, or None if unavailable.
    """
    path = shutil.which(bin_name)
    if path:
        return path

    print(f"{name} is not installed.")

    # Always ask explicitly — installing a binary is a system-level change.
    # The exact command is shown so the user knows what will run.
    if not confirm(
        f"{name} is not installed.\n"
        f"Install it with:\n  {install_cmd}\n"
        f"Install now?"
    ):
        print(f"Skipping {name}; its init was skipped.")
        return None

    # The command may pipe (e.g. `curl | bash`), so run it through a shell.
    result = subprocess.run(
        install_cmd,
        shell=True,
        check=False,
        capture_output=True,
        text=True,
        timeout=INSTALL_TIMEOUT,
    )
    if result.returncode != 0:
        tail = (result.stderr or result.stdout).strip().splitlines()[-3:]
        print(f"Failed to install {name} (exit {result.returncode}).")
        if tail:
            print("  " + "\n  ".join(tail))
        print("Install it manually and re-run.")
        return None

    path = shutil.which(bin_name)
    if not path:
        print(f"{name} installed but not on PATH. Refresh your shell and re-run.")
        return None

    return path


# The `--tools` value OpenSpec init is configured for, per agent id.
OPENSPEC_TOOLS = {"opencode": "opencode", "omp": "oh-my-pi"}

# Default-profile user-level OMP MCP config; `disabledServers` there outranks
# every other MCP source, including the project's .omp/mcp.json.
OMP_USER_MCP = Path.home() / ".omp" / "agent" / "mcp.json"


def _init_openspec(root: Path, openspec_bin: str, agent: str) -> None:
    """Initialize OpenSpec in the project (idempotent)."""
    tools = OPENSPEC_TOOLS[agent]
    subprocess.run([openspec_bin, "init", "--tools", tools], cwd=root, check=True)
    print("  openspec initialized")


def _prepend_instruction(root: Path, src_instruction: Path) -> None:
    """Prepend the codebase-memory instructions to AGENTS.md once."""
    target = root / "AGENTS.md"
    content = src_instruction.read_text(encoding="utf-8").strip()
    target.parent.mkdir(parents=True, exist_ok=True)
    existing = target.read_text(encoding="utf-8") if target.exists() else ""
    if INSTRUCTION_MARKER in existing:
        return  # already inserted

    target.write_text(content + "\n\n" + existing, encoding="utf-8")
    print(f"  added codebase-memory instructions to {target}")


def _install_plugin(root: Path, rel_dir: Path, src_plugin: Path) -> None:
    """Copy the codebase-memory reminder plugin into the project under rel_dir.

    The installed file keeps the canonical name CodebaseMemoryReminder.ts
    regardless of the source variant (.oc.ts / .omp.ts), so the harness sees
    one clean plugin file and re-installs overwrite the same path.
    """
    dest_dir = root / rel_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "CodebaseMemoryReminder.ts"
    dest.write_text(src_plugin.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  installed {dest}")


def _read_json(path: Path) -> dict:
    """Return the parsed JSON at path, or {} when absent or empty."""
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8").strip()
    return json.loads(text) if text else {}


def _merge_mcp_config(root: Path, mcp_bin: str) -> None:
    """Register codebase-memory-mcp in the project's opencode.json (once)."""
    path = root / ".opencode" / "opencode.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _read_json(path)

    payload = {
        "codebase-memory-mcp": {
            "enabled": True,
            "type": "local",
            "command": [mcp_bin],
        }
    }

    # Only set when absent so a user's existing entry is left alone.
    data.setdefault("mcp", {}).setdefault(
        "codebase-memory-mcp", payload["codebase-memory-mcp"]
    )

    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"  merged {path}")


def _merge_omp_mcp_config(root: Path, mcp_bin: str) -> None:
    """Declare codebase-memory-mcp in the project's OMP-native mcp.json (once)."""
    path = root / ".omp" / "mcp.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _read_json(path)

    # OMP's native MCP format (mcp-schema.json): stdio server, enabled.
    data.setdefault("mcpServers", {}).setdefault(
        "codebase-memory-mcp",
        {
            "enabled": True,
            "command": mcp_bin,
        },
    )

    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"  merged {path}")


def _set_runtime_flags(root: Path, mcp_bin: str) -> None:
    """Enable the repo-level codebase-memory runtime flags (idempotent)."""
    # Runtime settings are a plain key write in a local sqlite db — idempotent.
    # cwd=root so subdirectory installs target the same project db as the
    # rest of the per-project setup.
    for key in ("auto_index", "auto_watch"):
        subprocess.run([mcp_bin, "config", "set", key, "true"], cwd=root, check=True)


def _initial_index(root: Path, mcp_bin: str) -> None:
    """Index the repo graph on first init (idempotent, best-effort)."""
    # Skip when the project is already indexed, keeping re-runs a no-op. The
    # project name mirrors the tool's derivation: resolved full path, leading
    # slash stripped, '/' -> '-'. A mismatch on unusual paths only causes a
    # redundant re-index, which is safe.
    project_name = str(root.resolve()).lstrip("/").replace("/", "-")
    status = subprocess.run(
        [mcp_bin, "cli", "index_status", "--project", project_name],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if status.returncode == 0:
        print("  codebase-memory graph already indexed")
        return

    print("  indexing codebase-memory graph (full mode)...")
    result = subprocess.run(
        [mcp_bin, "cli", "index_repository", "--repo-path", str(root), "--mode", "full"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        print("  codebase-memory graph indexed")
    else:
        print("  warning: codebase-memory initial index failed; graph may be empty")
        print("    re-run `setup install` to retry")


def _reconcile_omp_denylist(confirm: Callable[[str], bool]) -> None:
    """
    Prompt to remove a stale user-level denylist entry for codebase-memory-mcp.

    The project's .omp/mcp.json declares the server, but a `disabledServers`
    entry in the user-level OMP config outranks every source. That file is a
    persistent user-controlled change, so removal is always prompted, never
    bypassed by --yes.
    """
    if not OMP_USER_MCP.exists():
        return
    try:
        data = _read_json(OMP_USER_MCP)
    except json.JSONDecodeError:
        print(f"  warning: could not read {OMP_USER_MCP}; leaving it alone")
        return

    denied = data.get("disabledServers", [])
    if "codebase-memory-mcp" not in denied:
        return

    if confirm(
        "codebase-memory-mcp is disabled in your Oh My Pi user config "
        f"({OMP_USER_MCP}).\nRemove it from disabledServers so this project's "
        "codebase-memory server can load?"
    ):
        data["disabledServers"] = [name for name in denied if name != "codebase-memory-mcp"]
        OMP_USER_MCP.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"  removed codebase-memory-mcp from {OMP_USER_MCP}")
    else:
        print(
            "  codebase-memory unavailable for Oh My Pi in this project "
            f"(denylisted in {OMP_USER_MCP})"
        )


def _init_codebase(
    root: Path,
    mcp_bin: str,
    src_instruction: Path,
    src_plugin: Path,
) -> None:
    """Run the per-project codebase-memory-mcp setup for opencode (idempotent)."""
    _prepend_instruction(root, src_instruction)
    _install_plugin(root, Path(".opencode") / "plugins", src_plugin)
    _merge_mcp_config(root, mcp_bin)
    _set_runtime_flags(root, mcp_bin)
    print("  codebase-memory-mcp initialized")


def _init_codebase_omp(
    root: Path,
    mcp_bin: str,
    src_instruction: Path,
    src_plugin: Path,
    confirm: Callable[[str], bool],
) -> None:
    """Run the per-project codebase-memory-mcp setup for Oh My Pi (idempotent)."""
    _prepend_instruction(root, src_instruction)
    _install_plugin(root, Path(".omp") / "extensions", src_plugin)
    _merge_omp_mcp_config(root, mcp_bin)
    _set_runtime_flags(root, mcp_bin)
    _reconcile_omp_denylist(confirm)
    print("  codebase-memory-mcp initialized (omp)")


def init_project(  # pylint: disable=too-many-positional-arguments
    cwd: Path,
    confirm: Callable[[str], bool],
    src_instruction: Path,
    src_plugin: Path,
    src_omp_plugin: Path,
    agent: str,
) -> None:
    """
    Initialize OpenSpec and codebase-memory-mcp for the project containing cwd.

    Runs only when cwd is inside a git repository; both tools' setup is
    idempotent, so it is safe to run on every install.

    OpenSpec is initialized for every agent. codebase-memory-mcp is
    initialized for both agents: opencode writes .opencode/ config, Oh My Pi
    writes .omp/ config (its own MCP server declaration and reminder
    extension, with no overlap). The AGENTS.md instruction block and the
    repo-level runtime flags are shared.

    Args:
        cwd: The working directory (per-project root is resolved from it).
        confirm: Prompt callback for installing missing tools.
        src_instruction: Path to the codebase-memory-mcp agents instructions.
        src_plugin: Path to the opencode CodebaseMemoryReminder plugin.
        src_omp_plugin: Path to the OMP CodebaseMemoryReminder extension.
        agent: The agent id being installed.
    """
    root = git_root(cwd)
    if root is None:
        print("  not a git repo; skipping per-project tool init")
        return

    print("Initializing per-project tools")

    openspec_bin = _ensure_tool("OpenSpec", "openspec", OPENSPEC_INSTALL, confirm)
    if openspec_bin:
        _init_openspec(root, openspec_bin, agent)

    mcp_bin = _ensure_tool(
        "codebase-memory-mcp", "codebase-memory-mcp", CBM_INSTALL, confirm
    )
    if not mcp_bin:
        return

    if agent == "opencode":
        _init_codebase(root, mcp_bin, src_instruction, src_plugin)
    else:
        _init_codebase_omp(root, mcp_bin, src_instruction, src_omp_plugin, confirm)

    _initial_index(root, mcp_bin)


def uninstall_notice(cwd: Path) -> None:
    """
    Notify when the project containing cwd carries per-project
    codebase-memory-mcp init that `setup uninstall` deliberately leaves alone.

    Install writes a reminder block into AGENTS.md, a reminder plugin plus an
    mcp entry into the agent's per-project config (.opencode/ for opencode,
    .omp/ for Oh My Pi) — all in the project `setup install` was run from.
    Uninstall is scoped to the agent config dir and never touches these;
    surface their presence so the user can remove them by hand if they want a
    full teardown.
    """
    root = git_root(cwd)
    if root is None:
        return

    agents = root / "AGENTS.md"
    has_block = agents.exists() and INSTRUCTION_MARKER in agents.read_text(
        encoding="utf-8"
    )
    plugin = root / ".opencode" / "plugins" / "CodebaseMemoryReminder.ts"
    has_plugin = plugin.exists()
    has_mcp_entry = False
    config_path = root / ".opencode" / "opencode.json"
    if config_path.exists():
        data = json.loads(config_path.read_text(encoding="utf-8") or "{}")
        has_mcp_entry = (
            "codebase-memory-mcp" in data.get("mcp", {})
        )
    has_omp = (
        (root / ".omp" / "extensions" / "CodebaseMemoryReminder.ts").exists()
        or (root / ".omp" / "mcp.json").exists()
    )

    if not (has_block or has_plugin or has_mcp_entry or has_omp):
        return

    print(
        "note: this project has per-project codebase-memory-mcp init "
        "(AGENTS.md instructions, .opencode/plugins/CodebaseMemoryReminder.ts, "
        "an opencode.json mcp entry, and/or .omp/ files for Oh My Pi). "
        "`setup uninstall` does not remove these; delete .opencode/ and .omp/ "
        "and strip the AGENTS.md block to do so manually."
    )
