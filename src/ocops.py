"""
Operations for the setup tool: symlink, text-insert, and config-merge.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path


def _substituted_content(root: Path, entry: dict, config_dir: Path) -> str:
    """
    Render the substituted copy content for a `replace` symlink entry.

    Args:
        root: The repository root containing the source file.
        entry: The symlink entry declaring `src` and `replace`.
        config_dir: The opencode config directory (resolves `{config_dir}`).

    Returns:
        The source file content with each placeholder replaced.
    """
    content = (root / entry["src"]).read_text(encoding="utf-8")
    for placeholder, value in entry.get("replace", {}).items():
        content = content.replace(
            placeholder, value.replace("{config_dir}", str(config_dir))
        )
    return content


def symlink(
    root: Path,
    config_dir: Path,
    artifact: dict,
    force: bool = False,
) -> None:
    """
    Symlink managed file or directory artifacts into the config directory.

    Args:
        root: The repository root containing the managed files.
        config_dir: The opencode config directory to link into.
        artifact: The manifest artifact describing the symlink.
        force: Overwrite an existing conflicting file or symlink.
    """
    entries = artifact.get("entries") or [
        {"src": artifact["src"], "target": artifact["target"]}
    ]
    for entry in entries:
        source_path = (root / entry["src"]).resolve()
        target_path = config_dir / entry["target"]

        # Create the destination's parent directories (e.g. commands/) if absent.
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # An entry with a `replace` table is written as a substituted copy (a
        # symlink cannot be edited in place). A leftover symlink from an older
        # install is unlinked first, since write_text would follow it and
        # clobber the repo source; a conflicting real file honours --force.
        replace = entry.get("replace")
        if replace:
            if target_path.is_symlink():
                if target_path.resolve() == source_path or force:
                    target_path.unlink()
                else:
                    print(
                        f"  skip {target_path}: differs from managed (use --force)"
                    )
                    continue
            elif target_path.exists():
                if not force:
                    # Idempotent: our copy is already in place.
                    if target_path.read_text(
                        encoding="utf-8"
                    ) == _substituted_content(root, entry, config_dir):
                        continue
                    print(f"  skip {target_path}: exists (use --force)")
                    continue
            target_path.write_text(
                _substituted_content(root, entry, config_dir), encoding="utf-8"
            )
            print(f"  installed {target_path}")
            continue

        if target_path.is_symlink():
            # Already a symlink: skip if it points where we want (idempotent);
            # otherwise only replace it when the user passed --force.
            if target_path.resolve() == source_path:
                continue
            if force:
                target_path.unlink()
            else:
                print(f"  skip {target_path}: differs from managed (use --force)")
                continue
        elif target_path.exists():
            # A real file (not a symlink) is in the way — only displace it
            # with --force, and remove directories recursively.
            if force:
                if target_path.is_dir():
                    shutil.rmtree(target_path)
                else:
                    target_path.unlink()
            else:
                print(f"  skip {target_path}: exists (use --force)")
                continue

        target_path.symlink_to(source_path)
        print(f"  linked {target_path}")


def text_insert(
    root: Path,
    config_dir: Path,
    artifact: dict,
) -> None:
    """
    Insert a text block into a target file, prepending or appending.

    Args:
        root: The repository root containing the source text.
        config_dir: The opencode config directory containing the target.
        artifact: The manifest artifact describing the insertion.
    """
    content = (root / artifact["src"]).read_text(encoding="utf-8").strip()
    target_path = config_dir / artifact["target"]
    target_path.parent.mkdir(parents=True, exist_ok=True)
    existing = (
        target_path.read_text(encoding="utf-8") if target_path.exists() else ""
    )

    # Anchor text already present — the block was inserted before; don't
    # duplicate it (keeps install idempotent).
    if artifact["anchor"] in existing:
        return
    if artifact.get("mode", "append") == "prepend":
        new_content = content + "\n\n" + existing
    else:
        new_content = existing.rstrip() + "\n\n" + content + "\n"

    target_path.write_text(new_content, encoding="utf-8")
    print(f"  inserted text block into {target_path}")


def _text_remove(
    root: Path,
    config_dir: Path,
    artifact: dict,
) -> None:
    """
    Remove a previously inserted text block from its target file.

    Only removes the block when it is still byte-identical to what the tool
    wrote (the source content, delimited by its own start/end markers). If the
    user edited the block, it is left in place.

    Args:
        root: The repository root containing the source text.
        config_dir: The opencode config directory containing the target.
        artifact: The manifest artifact describing the insertion.
    """
    content = (root / artifact["src"]).read_text(encoding="utf-8").strip()
    target_path = config_dir / artifact["target"]
    if not target_path.exists():
        return
    existing = target_path.read_text(encoding="utf-8")
    start = existing.find(content)
    if start == -1:
        return  # not inserted, or the user edited the block
    end = start + len(content)
    new_content = (existing[:start] + existing[end:]).strip("\n") + "\n"
    if new_content == existing:
        return
    target_path.write_text(new_content, encoding="utf-8")


def config_merge(
    _root: Path,
    config_dir: Path,
    artifact: dict,
    mcp_bin: str = "",
) -> None:
    """
    Merge a JSON config entry into a target config file.

    Args:
        config_dir: The opencode config directory containing the target.
        artifact: The manifest artifact describing the merge.
        mcp_bin: The codebase-memory-mcp binary path to substitute.
    """
    target_path = config_dir / artifact["config_file"]
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Substitute the resolved mcp binary path before parsing the value.
    raw_value = artifact["value"].replace("<MCP_BIN>", mcp_bin)
    try:
        value = json.loads(raw_value)
    except json.JSONDecodeError:
        # Value isn't JSON — store it as a raw string instead.
        value = raw_value

    data: dict = {}
    if target_path.exists():
        raw = target_path.read_text(encoding="utf-8")
        if raw.strip():
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"refusing to merge into unparseable {target_path}; "
                    "fix or remove it first"
                ) from error
            if not isinstance(data, dict):
                raise ValueError(
                    f"refusing to merge into non-object {target_path}"
                )

    # Walk the dotted config_path (e.g. "mcp.servers.foo"), creating any
    # intermediate dicts, then set the final leaf key to the value.
    node = data
    for key in artifact["config_path"].split(".")[:-1]:
        existing = node.setdefault(key, {})
        if not isinstance(existing, dict):
            raise ValueError(f"{target_path}: config key {key!r} is not a table")
        node = existing
    leaf = artifact["config_path"].split(".")[-1]
    # Idempotent only when the key is actually present with the target value.
    # `node.get(leaf) == value` would also return True for an absent key when
    # value is JSON null, skipping the write.
    if leaf in node and node[leaf] == value:
        return  # idempotent: already merged
    node[leaf] = value
    target_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"  merged {target_path}")


def install(
    manifest: dict,
    root: Path,
    config_dir: Path,
    force: bool = False,
) -> None:
    """
    Bring the managed config farm up, idempotently.

    Args:
        manifest: The parsed manifest dictionary.
        root: The repository root.
        config_dir: The opencode config directory.
        force: Overwrite conflicting files.
    """
    mcp_bin = shutil.which("codebase-memory-mcp") or "codebase-memory-mcp"
    config_dir.mkdir(parents=True, exist_ok=True)
    for artifact in manifest["artifacts"]:
        operation = artifact["operation"]
        if operation == "symlink":
            symlink(root, config_dir, artifact, force)
        elif operation == "text-insert":
            text_insert(root, config_dir, artifact)
        elif operation == "config-merge":
            config_merge(root, config_dir, artifact, mcp_bin)
        else:  # pragma: no cover
            raise ValueError(f"unknown operation {operation}")


def expected_symlink_targets(manifest: dict) -> set[str]:
    """
    Return the set of managed symlink targets declared in the manifest.

    Args:
        manifest: The parsed manifest dictionary.

    Returns:
        The set of relative symlink target paths.
    """
    targets: set[str] = set()

    for artifact in manifest["artifacts"]:
        if artifact["operation"] != "symlink":
            continue
        entries = artifact.get("entries") or [{"target": artifact["target"]}]
        for entry in entries:
            targets.add(entry["target"])

    return targets


def managed_symlinks(
    config_dir: Path,
    root: Path,
):
    """
    Yield managed symlinks under config_dir that point into root/src.

    Args:
        config_dir: The opencode config directory to scan.
        root: The repository root.

    Yields:
        Tuples of (symlink_path, relative_target).
    """
    src_prefix = str((root / "src").resolve())
    for path in config_dir.rglob("*"):
        if path.is_symlink():
            try:
                resolved = path.resolve()
            except OSError:
                continue
            # Only treat symlinks that point into this repo's src/ as managed;
            # user-created links elsewhere are left alone.
            if str(resolved).startswith(src_prefix):
                yield path, str(path.relative_to(config_dir))


def sync(
    manifest: dict,
    root: Path,
    config_dir: Path,
    force: bool = False,
    prune: bool = True,
) -> None:
    """
    Install and remove stale managed symlinks.

    Args:
        manifest: The parsed manifest dictionary.
        root: The repository root.
        config_dir: The opencode config directory.
        force: Overwrite conflicting files.
        prune: Remove stale managed symlinks (default True).
    """
    install(manifest, root, config_dir, force)

    if not prune:
        return

    # Prune: remove managed symlinks no longer declared in the manifest
    # (e.g. after an artifact was renamed or dropped). Replace-substituted
    # copies are NOT pruned here: once an artifact is dropped, its copy is
    # indistinguishable from a user file, so deleting it would be unsafe.
    # (uninstall() handles in-manifest teardown by content comparison.)
    expected = expected_symlink_targets(manifest)
    for path, relative_target in list(managed_symlinks(config_dir, root)):
        if relative_target not in expected:
            print(f"  removing stale managed symlink: {path}")
            path.unlink()


def uninstall(
    manifest: dict,
    root: Path,
    config_dir: Path,
) -> None:
    """
    Tear down managed symlinks, substituted copies, and inserted text blocks,
    keeping user files.

    Args:
        manifest: The parsed manifest dictionary.
        root: The repository root.
        config_dir: The opencode config directory.
    """
    for path, _ in list(managed_symlinks(config_dir, root)):
        print(f"  removing managed symlink: {path}")
        path.unlink()
    # Replace-substituted entries are written as copies, so the symlink scan
    # above misses them; remove them here for a complete teardown. Plain
    # symlink entries that were installed as copies by an earlier tool (rather
    # than as symlinks) are also real files, so they need the same handling.
    # Only a file that still matches exactly the content the tool would write
    # is removed — a user's own file at the same path is kept.
    for artifact in manifest["artifacts"]:
        if artifact["operation"] != "symlink":
            continue
        entries = artifact.get("entries") or [
            {"src": artifact["src"], "target": artifact["target"]}
        ]
        for entry in entries:
            target = config_dir / entry["target"]
            if target.is_symlink() or target.is_dir() or not target.exists():
                continue
            if target.read_text(encoding="utf-8") == _substituted_content(
                root, entry, config_dir
            ):
                print(f"  removing managed file: {target}")
                target.unlink()
    # text-insert artifacts inject a block into a target file (e.g. AGENTS.md);
    # tear them down too, keeping any user-edited block in place.
    for artifact in manifest["artifacts"]:
        if artifact["operation"] == "text-insert":
            target = config_dir / artifact["target"]
            if target.exists() and artifact["anchor"] in target.read_text(
                encoding="utf-8"
            ):
                print(f"  removing managed text block: {target}")
                _text_remove(root, config_dir, artifact)
