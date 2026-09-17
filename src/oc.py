#!/usr/bin/env python3
"""
Manifest-driven OpenCode setup and updater.

Subcommands:
    install: Install managed files and remove stale symlinks (prompts first).
    uninstall: Tear down managed symlinks, keep your own occonfig.
    vendor: Re-vendor upstream artifacts (report drift, pull changes; prompts first).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifest.toml"

# pylint: disable=wrong-import-position
import occonfig  # noqa: E402
import ocinit  # noqa: E402
import ocmanifest  # noqa: E402
import ocmerge  # noqa: E402
import ocops  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    """
    Build and return the command-line argument parser.

    Returns:
        A configured ArgumentParser covering every subcommand.
    """
    parser = argparse.ArgumentParser(
        prog="oc",
        description="Manifest-driven OpenCode setup and updater.",
        epilog="Run `oc <subcommand> --help` for details.",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="SUBCOMMAND")

    install_parser = subparsers.add_parser(
        "install", help="install managed files and remove stale symlinks"
    )
    install_parser.add_argument(
        "--force", action="store_true", help="overwrite conflicting files"
    )
    install_parser.add_argument(
        "--yes", action="store_true", help="remove stale symlinks without prompting"
    )
    install_parser.add_argument(
        "--no-init", action="store_true", help="skip per-project tool init"
    )

    subparsers.add_parser(
        "uninstall", help="tear down managed files and text blocks, keep your own config"
    )

    vendor_parser = subparsers.add_parser(
        "vendor", help="re-vendor upstream artifacts (report drift, pull changes)"
    )
    vendor_parser.add_argument(
        "--yes", action="store_true", help="pull changes without prompting"
    )
    vendor_parser.add_argument(
        "names",
        nargs="*",
        metavar="NAME",
        help="artifact names to vendor (default: all)",
    )

    return parser


def _confirm(prompt: str, assume_yes: bool) -> bool:
    """
    Ask the user to confirm an action.

    Args:
        prompt: The confirmation question.
        assume_yes: Skip the prompt and assume yes.

    Returns:
        True if the action should proceed.
    """
    if assume_yes:
        return True
    # Non-interactive stdin (e.g. piped input): never block on a prompt,
    # treat it as a "no".
    if not sys.stdin.isatty():
        return False

    reply = input(f"{prompt} [y/N] ").strip().lower()
    return reply in ("y", "yes")


def _run_install(
    manifest_data: dict,
    config_dir: Path,
    force: bool,
    assume_yes: bool,
    skip_init: bool = False,
) -> None:
    """
    Install managed files and remove stale symlinks, prompting first.

    Args:
        manifest_data: The parsed manifest dictionary.
        config_dir: The opencode config directory.
        force: Overwrite conflicting files.
        assume_yes: Remove stale symlinks without prompting.
        skip_init: Skip per-project OpenSpec / codebase-memory-mcp init.
    """
    expected = ocops.expected_symlink_targets(manifest_data)

    # Collect managed symlinks no longer declared in the manifest, so the
    # prune pass can remove the ones that the sync no longer maintains.
    stale = [
        relative
        for _, relative in ocops.managed_symlinks(config_dir, ROOT)
        if relative not in expected
    ]

    # Only prompt about pruning when there are stale symlinks and the user
    # didn't already approve removal via --yes.
    if stale and not assume_yes:
        prune = _confirm(
            f"Remove {len(stale)} stale managed symlink(s)?", assume_yes=False
        )
    else:
        prune = True

    # sync installs all managed files, then (unless prune=False) removes
    # stale symlinks that point into src/ but are no longer in the manifest.
    ocops.sync(manifest_data, ROOT, config_dir, force, prune=prune)

    # Per-project tool init (OpenSpec, codebase-memory-mcp). Only runs when
    # the working directory is inside a git repository; both tools' setup is
    # idempotent, so re-running install is safe.
    if not skip_init:
        ocinit.init_project(
            Path.cwd(),
            # Never bypassed by --yes: installing a binary is a system-level
            # change that must always be an explicit user choice.
            lambda prompt: _confirm(prompt, False),
            ROOT / "src" / "instructions" / "codebase-memory-mcp-agents.md",
            ROOT / "src" / "plugins" / "CodebaseMemoryReminder.ts",
        )


def _run_vendor(
    manifest_data: dict,
    names: list[str],
    assume_yes: bool,
) -> int:
    """
    Report upstream drift and pull changes for vendor/fork artifacts.

    Args:
        manifest_data: The parsed manifest dictionary.
        names: Artifact names to vendor; empty vendors all.
        assume_yes: Pull changes without prompting.

    Returns:
        0 on success, non-zero if any artifact failed.
        """
    # No explicit names given — vendor every artifact declared in the manifest.
    targets = names if names else ocmanifest.artifact_names(manifest_data)

    # Pass 1: report drift and collect the artifacts that are behind.
    behind = []
    exit_code = 0
    for artifact_name in targets:
        artifact = ocmanifest.find(manifest_data, artifact_name)
        if artifact is None:
            print(f"  unknown artifact: {artifact_name}")
            exit_code = 1
            continue
        result = ocmerge.update_artifact(MANIFEST, ROOT, artifact, check_only=True)
        if result == ocmerge.DRIFT:
            behind.append(artifact_name)
        elif result != 0:
            exit_code = 1

    if not behind:
        print("  all artifacts up to date")
        return exit_code

    if not _confirm(
        f"Pull upstream changes for {len(behind)} artifact(s)?",
        assume_yes,
    ):
        print("  update skipped")
        return exit_code

    # Pass 2: pull upstream for the artifacts that drifted.
    for artifact_name in behind:
        artifact = ocmanifest.find(manifest_data, artifact_name)
        if artifact is None:
            continue
        if ocmerge.update_artifact(MANIFEST, ROOT, artifact, check_only=False) != 0:
            exit_code = 1

    return exit_code


def main(argv: list[str] | None = None) -> int:
    """
    Parse arguments and dispatch to the requested subcommand.

    Args:
        argv: The argument list, or None to use sys.argv.

    Returns:
        The process exit code.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    # No subcommand given — print usage to stderr and exit 2
    if not args.command:
        parser.print_help(sys.stderr)
        return 2

    try:
        manifest_data = ocmanifest.load(MANIFEST)
    except ocmanifest.ManifestError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    try:
        if args.command == "install":
            config_dir = occonfig.config_dir(manifest_data)
            _run_install(manifest_data, config_dir, args.force, args.yes, args.no_init)
        elif args.command == "uninstall":
            config_dir = occonfig.config_dir(manifest_data)
            ocops.uninstall(manifest_data, ROOT, config_dir)
        elif args.command == "vendor":
            return _run_vendor(manifest_data, args.names, args.yes)
    except Exception as error:  # pylint: disable=broad-except
        print(f"error: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
