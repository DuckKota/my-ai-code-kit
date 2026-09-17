"""
Resolve the opencode global configuration directory.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

FALLBACK = Path.home() / ".config" / "opencode"


def config_dir(manifest: dict) -> Path:
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

    if shutil.which("opencode"):
        try:
            result = subprocess.run(
                ["opencode", "debug", "paths"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )

            # `opencode debug paths` prints lines like "config <path>";
            # find the one whose label is `config`.
            for line in result.stdout.splitlines():
                parts = line.split()
                if parts and parts[0] == "config" and len(parts) > 1:
                    return Path(parts[1]).expanduser()
        except (OSError, subprocess.SubprocessError):
            # opencode missing or failed — fall through to the default.
            pass

    return FALLBACK
