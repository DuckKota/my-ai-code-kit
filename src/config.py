"""
Resolve per-agent global configuration directories and detect installed agents.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

# The coding agents this tool can install into.
AGENTS = ("opencode", "omp")

# Display names for the agent-selection prompt.
AGENT_LABELS = {
    "opencode": "OpenCode",
    "omp": "Oh My Pi",
}

OPENCODE_FALLBACK = Path.home() / ".config" / "opencode"
OMP_FALLBACK = Path.home() / ".omp" / "agent"


def detect_agents() -> list[str]:
    """
    Return the agents whose executables are on PATH, in AGENTS order.

    Returns:
        The list of detected agent ids (subset of AGENTS).
    """
    return [agent for agent in AGENTS if shutil.which(agent)]


def _probe(
    binary: str,
    args: list[str],
    parse: Callable[[str], str],
    fallback: Path,
) -> Path:
    """
    Run a binary's config-path command and return the resolved path.

    Returns fallback when the binary is missing, the command fails, or the
    parser yields nothing usable.

    Args:
        binary: The executable name to look up on PATH.
        args: The command arguments that print the config path.
        parse: Extracts the path string from the command's stdout.
        fallback: The default path when probing fails.

    Returns:
        The resolved config directory path.
    """
    if not shutil.which(binary):
        return fallback
    try:
        result = subprocess.run(
            [binary, *args],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        # Binary missing or failed — fall through to the default.
        return fallback
    path = parse(result.stdout) if result.returncode == 0 else ""
    return Path(path).expanduser() if path else fallback


def _parse_opencode_path(stdout: str) -> str:
    """
    Extract the config path from `opencode debug paths` output.

    The command prints lines like "config <path>"; return the path from the
    line whose label is `config`.

    Args:
        stdout: The command's stdout.

    Returns:
        The config path, or "" if not found.
    """
    for line in stdout.splitlines():
        parts = line.split()
        if parts and parts[0] == "config" and len(parts) > 1:
            return parts[1]
    return ""


def opencode_config_dir(manifest: dict) -> Path:
    """
    Resolve the opencode config directory.

    Precedence:
        OC_CONFIG_DIR env var, then manifest config.default_config_dir,
        then `opencode debug paths`, then ~/.config/opencode.

    Args:
        manifest: The parsed manifest dictionary.

    Returns:
        The resolved config directory path.
    """
    env_dir = os.environ.get("OC_CONFIG_DIR")
    if env_dir:
        return Path(env_dir).expanduser()

    default_dir = manifest.get("config", {}).get("default_config_dir")
    if default_dir:
        return Path(default_dir).expanduser()

    return _probe("opencode", ["debug", "paths"], _parse_opencode_path, OPENCODE_FALLBACK)


def omp_config_dir() -> Path:
    """
    Resolve the Oh My Pi config directory.

    Precedence:
        `omp config path`, then ~/.omp/agent.

    Returns:
        The resolved config directory path.
    """
    return _probe("omp", ["config", "path"], lambda s: s.strip(), OMP_FALLBACK)


def config_dir(agent: str, manifest: dict) -> Path:
    """
    Resolve the config directory for the given agent.

    Args:
        agent: The agent id (one of AGENTS).
        manifest: The parsed manifest dictionary.

    Returns:
        The resolved config directory path.

    Raises:
        ValueError: If agent is not a known agent id.
    """
    if agent == "opencode":
        return opencode_config_dir(manifest)
    if agent == "omp":
        return omp_config_dir()
    raise ValueError(f"unknown agent {agent!r}")
