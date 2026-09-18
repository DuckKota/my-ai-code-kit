"""
Shell rc bootstrap: register a `my-ai-code-kit` shell function in the user's
rc file so the setup command is reachable from any directory.

The function embeds the absolute path to this repo's `bin/setup`. A marker
block makes the bootstrap idempotent (no double-append) and lets `uninstall`
remove exactly what `install` added.
"""
from __future__ import annotations

import os
from pathlib import Path

COMMAND_NAME = "my-ai-code-kit"

MARKER_START = f"# >>> {COMMAND_NAME} begin >>>"
MARKER_END = f"# <<< {COMMAND_NAME} end <<<"

# Login-shell basename -> rc file. Paths are relative to $HOME.
RC_FILES = {
    "zsh": "~/.zshrc",
    "bash": "~/.bashrc",
    "fish": "~/.config/fish/config.fish",
}


def login_shell() -> str | None:
    """Return the basename of the login shell, or None when unset/unsupported."""
    name = Path(os.environ.get("SHELL", "")).name
    return name if name in RC_FILES else None


def rc_path(shell: str | None) -> Path | None:
    """Resolve the rc file for a shell basename, or None for unknown."""
    rel = RC_FILES.get(shell or "")
    return Path(rel).expanduser() if rel else None


def bootstrap_block(script_path: Path, shell: str) -> str:
    """Return the marker-delimited block registering the command for `shell`."""
    if shell == "fish":
        body = f"function {COMMAND_NAME}\n    {script_path} $argv\nend"
    else:
        body = f'{COMMAND_NAME}() {{ {script_path} "$@"; }}'
    return f"{MARKER_START}\n{body}\n{MARKER_END}\n"


def block_present(rc_file: Path) -> bool:
    """Return True when the marker block already exists in the rc file."""
    if not rc_file.exists():
        return False
    text = rc_file.read_text()
    return MARKER_START in text or MARKER_END in text


def add_block(rc_file: Path, block: str) -> bool:
    """Append the block idempotently. Returns True if appended, False if already present."""
    if block_present(rc_file):
        return False
    if rc_file.exists():
        content = rc_file.read_text()
        if content and not content.endswith("\n"):
            content += "\n"
        content += "\n" + block
    else:
        content = block
    rc_file.parent.mkdir(parents=True, exist_ok=True)
    rc_file.write_text(content)
    return True


def remove_block(rc_file: Path) -> bool:
    """Remove the marker block. Returns True if removed, False if absent."""
    if not rc_file.exists():
        return False
    text = rc_file.read_text()
    start = text.find(MARKER_START)
    end = text.find(MARKER_END)
    if start == -1 or end == -1:
        return False
    end += len(MARKER_END)
    # swallow the trailing newline after the end marker, if present
    if end < len(text) and text[end] == "\n":
        end += 1
    new = text[:start] + text[end:]
    # collapse any double blank line left at the removal boundary
    while "\n\n\n" in new:
        new = new.replace("\n\n\n", "\n\n")
    rc_file.write_text(new)
    return True
