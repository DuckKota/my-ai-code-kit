"""
Load and validate the manifest.toml file.
"""
from __future__ import annotations

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib  # type: ignore[no-redef]
from pathlib import Path

import config

OPERATIONS = ("symlink", "config-merge", "text-insert")
PROVENANCES = ("original", "vendor", "fork")
# Version 2 requires every artifact to declare an explicit `agents` list.
MIN_VERSION = 2


class ManifestError(Exception):
    """
    Raised when the manifest is missing or invalid.
    """


def load(path: str | Path) -> dict:
    """
    Load, validate, and return the manifest from path.

    Args:
        path: The manifest file path.

    Returns:
        The parsed manifest dictionary.

    Raises:
        ManifestError: If the manifest is missing or invalid.
    """
    path = Path(path)

    if not path.exists():
        raise ManifestError(f"manifest not found: {path}")

    with open(path, "rb") as manifest_file:
        try:
            data = tomllib.load(manifest_file)
        except tomllib.TOMLDecodeError as error:
            raise ManifestError(f"invalid manifest {path}: {error}") from error

    validate(data)

    return data


def validate(data: dict) -> None:
    """
    Validate the manifest structure, raising ManifestError on problems.

    Args:
        data: The parsed manifest dictionary.

    Raises:
        ManifestError: If a required field is missing or invalid.
    """
    if "artifacts" not in data:
        raise ManifestError("manifest missing `artifacts`")

    if "version" not in data:
        raise ManifestError("manifest missing `version`")

    if data["version"] != MIN_VERSION:
        version = data["version"]
        raise ManifestError(
            f"unsupported manifest version {version!r}; "
            f"expected {MIN_VERSION}"
        )

    if not isinstance(data["artifacts"], list) or not all(
        isinstance(artifact, dict) for artifact in data["artifacts"]
    ):
        raise ManifestError("`artifacts` must be a list of tables")

    for artifact in data["artifacts"]:
        name = artifact.get("name")

        if not name:
            raise ManifestError("artifact missing `name`")

        agents = artifact.get("agents")
        valid_agents = ", ".join(config.AGENTS)
        if (
            not isinstance(agents, list)
            or not agents
            or not all(agent in config.AGENTS for agent in agents)
        ):
            raise ManifestError(
                f"{name}: must declare a non-empty `agents` list of {valid_agents}"
            )

        operation = artifact.get("operation")
        if operation not in OPERATIONS:
            raise ManifestError(f"{name}: bad operation {operation!r}")

        # Provenance defaults to "original" (a user-owned, never-overwritten file).
        provenance = artifact.get("provenance", "original")
        if provenance not in PROVENANCES:
            raise ManifestError(f"{name}: bad provenance {provenance!r}")

        if provenance in ("vendor", "fork") and not artifact.get("source_repo"):
            raise ManifestError(f"{name}: vendor/fork needs `source_repo`")

        if operation == "symlink":
            entries = artifact.get("entries")
            if entries:
                if not all(
                    isinstance(entry, dict)
                    and entry.get("src")
                    and entry.get("target")
                    for entry in entries
                ):
                    raise ManifestError(
                        f"{name}: symlink `entries` need `src`/`target`"
                    )
                if any(
                    "replace" in entry
                    and not isinstance(entry["replace"], dict)
                    for entry in entries
                ):
                    raise ManifestError(
                        f"{name}: symlink entry `replace` must be a table"
                    )
                if any(
                    "replace" in entry
                    and not all(
                        isinstance(key, str) and isinstance(val, str)
                        for key, val in entry["replace"].items()
                    )
                    for entry in entries
                ):
                    raise ManifestError(
                        f"{name}: symlink entry `replace` must map strings "
                        "to strings"
                    )
            elif "replace" in artifact:
                raise ManifestError(
                    f"{name}: symlink `replace` requires the `entries` form"
                )
            elif not (artifact.get("src") and artifact.get("target")):
                raise ManifestError(f"{name}: symlink needs `src`/`target`")
        elif operation == "text-insert":
            if not (
                artifact.get("src")
                and artifact.get("target")
                and artifact.get("anchor")
            ):
                raise ManifestError(f"{name}: text-insert needs src/target/anchor")
        elif operation == "config-merge":
            if not (
                isinstance(artifact.get("config_file"), str)
                and artifact.get("config_file")
                and isinstance(artifact.get("config_path"), str)
                and artifact.get("config_path")
            ):
                raise ManifestError(
                    f"{name}: config-merge needs config_file/config_path (strings)"
                )
            if "value" not in artifact or not isinstance(artifact["value"], str):
                raise ManifestError(f"{name}: config-merge needs string `value`")


def find(
    data: dict,
    name: str,
) -> dict | None:
    """
    Return the named artifact, or None if not present.

    Args:
        data: The parsed manifest dictionary.
        name: The artifact name to find.

    Returns:
        The matching artifact dictionary, or None.
    """
    for artifact in data["artifacts"]:
        if artifact.get("name") == name:
            return artifact

    return None


def artifact_names(data: dict) -> list[str]:
    """
    Return the names of all artifacts in order.

    Args:
        data: The parsed manifest dictionary.

    Returns:
        The list of artifact names.
    """
    return [artifact["name"] for artifact in data["artifacts"]]


def set_sha(
    path: str | Path,
    name: str,
    value: str,
) -> None:
    """
    Set the source_sha of a named artifact in manifest.toml, in place.

    Args:
        path: The manifest file path.
        name: The artifact whose source_sha to update.
        value: The new source_sha value.
    """
    path = Path(path)
    lines = path.read_text(encoding="utf-8").splitlines()

    # Textual TOML edit: track which [[artifacts]] block (by its `name` line)
    # the current line belongs to, then rewrite source_sha only inside the
    # block for the requested artifact.
    current = None
    updated = False
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[[artifacts]]"):
            current = None
            out.append(line)
            continue
        if current is None and stripped.startswith("name ="):
            # Strip either quote style and any trailing comment.
            current = stripped.split("=", 1)[1].strip().strip("'\"").split("#")[0].strip()
            out.append(line)
            continue
        if current == name and stripped.startswith("source_sha"):
            # Preserve the original indentation when replacing the value.
            indent = line[: len(line) - len(line.lstrip())]
            out.append(f'{indent}source_sha = "{value}"')
            updated = True
            continue
        out.append(line)

    if not updated:
        raise ManifestError(f"no source_sha found for artifact {name!r}")

    path.write_text("\n".join(out) + "\n", encoding="utf-8")
