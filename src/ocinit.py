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
# hung network fetch would otherwise block `oc install` indefinitely.
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


def _init_openspec(root: Path, openspec_bin: str) -> None:
    """Initialize OpenSpec in the project (idempotent)."""
    subprocess.run([openspec_bin, "init", "--tools", "opencode"], cwd=root, check=True)
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


def _install_plugin(root: Path, src_plugin: Path) -> None:
    """Copy the codebase-memory reminder plugin into the project."""
    dest_dir = root / ".opencode" / "plugins"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src_plugin.name
    dest.write_text(src_plugin.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  installed {dest}")


def _merge_mcp_config(root: Path, mcp_bin: str) -> None:
    """Register codebase-memory-mcp in the project's opencode.json (once)."""
    path = root / ".opencode" / "opencode.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    if path.exists() and path.read_text(encoding="utf-8").strip():
        data = json.loads(path.read_text(encoding="utf-8"))

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


def _init_codebase(
    root: Path,
    mcp_bin: str,
    src_instruction: Path,
    src_plugin: Path,
) -> None:
    """Run the per-project codebase-memory-mcp setup (idempotent)."""
    _prepend_instruction(root, src_instruction)
    _install_plugin(root, src_plugin)
    _merge_mcp_config(root, mcp_bin)

    # Runtime settings are a plain key write in a local sqlite db — idempotent.
    # cwd=root so subdirectory installs target the same project db as the
    # rest of the per-project setup.
    for key in ("auto_index", "auto_watch"):
        subprocess.run([mcp_bin, "config", "set", key, "true"], cwd=root, check=True)

    print("  codebase-memory-mcp initialized")


def init_project(
    cwd: Path,
    confirm: Callable[[str], bool],
    src_instruction: Path,
    src_plugin: Path,
) -> None:
    """
    Initialize OpenSpec and codebase-memory-mcp for the project containing cwd.

    Runs only when cwd is inside a git repository; both tools' setup is
    idempotent, so it is safe to run on every install.

    Args:
        cwd: The working directory (per-project root is resolved from it).
        confirm: Prompt callback for installing missing tools.
        src_instruction: Path to the codebase-memory-mcp agents instructions.
        src_plugin: Path to the CodebaseMemoryReminder plugin.
    """
    root = git_root(cwd)
    if root is None:
        print("  not a git repo; skipping per-project tool init")
        return

    print("Initializing per-project tools")

    openspec_bin = _ensure_tool("OpenSpec", "openspec", OPENSPEC_INSTALL, confirm)
    if openspec_bin:
        _init_openspec(root, openspec_bin)

    mcp_bin = _ensure_tool(
        "codebase-memory-mcp", "codebase-memory-mcp", CBM_INSTALL, confirm
    )
    if mcp_bin:
        _init_codebase(root, mcp_bin, src_instruction, src_plugin)
