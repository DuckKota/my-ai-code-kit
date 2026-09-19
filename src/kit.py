#!/usr/bin/env python3
"""
Manifest-driven setup for multiple coding agents (OpenCode, Oh My Pi).

Subcommands:
    install: Install managed files and remove stale symlinks (prompts first).
    uninstall: Tear down managed symlinks, keep your own config.
    vendor: Re-vendor upstream artifacts (report drift, pull changes; prompts first).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifest.toml"

# pylint: disable=wrong-import-position
import config  # noqa: E402
import manifest  # noqa: E402
import merge  # noqa: E402
import operations  # noqa: E402
import project  # noqa: E402
import shell_rc  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    """
    Build and return the command-line argument parser.

    Returns:
        A configured ArgumentParser covering every subcommand.
    """
    parser = argparse.ArgumentParser(
        prog="setup",
        description="Manifest-driven multi-agent setup and updater.",
        epilog="Run `setup <subcommand> --help` for details.",
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
    install_parser.add_argument(
        "--agent",
        choices=config.AGENTS,
        help="install for this agent only (skip detection/prompt)",
    )

    uninstall_parser = subparsers.add_parser(
        "uninstall", help="tear down managed files and text blocks, keep your own config"
    )
    uninstall_parser.add_argument(
        "--agent",
        choices=config.AGENTS,
        help="uninstall for this agent only (skip detection/prompt)",
    )

    vendor_parser = subparsers.add_parser(
        "vendor", help="re-vendor upstream artifacts (report drift, pull changes)"
    )
    vendor_parser.add_argument(
        "--yes", action="store_true", help="pull changes without prompting"
    )
    vendor_parser.add_argument(
        "--agent",
        choices=config.AGENTS,
        help="accepted for symmetry; vendor operates on the repo, not config dirs",
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


def select_agents(agent_flag: str | None, command: str = "install") -> str | None:
    """
    Resolve the agent to operate on.

    Precedence:
        --agent flag, then a single detected agent (no prompt), then a prompt
        when multiple are detected. Returns None when no agent is detected and
        none was forced (caller aborts).

    Args:
        agent_flag: The --agent CLI value, or None.
        command: The subcommand being run ("install" or "uninstall"), used to
            word the multi-agent prompt.

    Returns:
        The selected agent id, or None to abort.
    """
    if agent_flag:
        return agent_flag

    detected = config.detect_agents()
    if not detected:
        return None
    if len(detected) == 1:
        return detected[0]

    # Both installed — ask which one to target, in detection order.
    verb = "Install" if command == "install" else "Uninstall"
    for i, agent in enumerate(detected, 1):
        print(f"  {i}. {config.AGENT_LABELS[agent]}")
    while True:
        reply = input(f"{verb} for which? [1-{len(detected)}] ").strip()
        try:
            choice = int(reply)
        except ValueError:
            choice = 0
        if 1 <= choice <= len(detected):
            return detected[choice - 1]
        print(f"  enter a number between 1 and {len(detected)}")


def _bootstrap_shell_command() -> None:
    """
    Offer to register a `my-ai-code-kit` shell function in the user's rc file.

    Shell-gated and idempotent: unsupported shells are skipped, and an
    existing marker block is reported rather than duplicated. The prompt is
    never bypassed by --yes (an rc edit is a persistent user-controlled
    change).
    """
    shell = shell_rc.login_shell()
    rc = shell_rc.rc_path(shell)
    if rc is None:
        print(f"  skipped shell command bootstrap (unsupported shell: {shell or 'unset'})")
        return
    script = ROOT / "bin" / "setup"
    if shell_rc.block_present(rc):
        print(f"  {shell_rc.COMMAND_NAME} already registered in {rc}")
        return
    if not _confirm(
        f"Add a '{shell_rc.COMMAND_NAME}' command to {rc} so you can run setup from any directory?",
        assume_yes=False,
    ):
        print("  skipped shell command bootstrap")
        return
    if shell_rc.add_block(rc, shell_rc.bootstrap_block(script, shell)):
        print(f"  registered '{shell_rc.COMMAND_NAME}' in {rc}")


def _unbootstrap_shell_command() -> None:
    """Remove the `my-ai-code-kit` shell function installed by `install`."""
    shell = shell_rc.login_shell()
    rc = shell_rc.rc_path(shell)
    if rc is None:
        return
    if shell_rc.remove_block(rc):
        print(f"  removed '{shell_rc.COMMAND_NAME}' from {rc}")
    else:
        print(f"  no '{shell_rc.COMMAND_NAME}' command registered in {rc}")


def _run_install(
    manifest_data: dict,
    config_dir: Path,
    force: bool,
    assume_yes: bool,
    skip_init: bool = False,
    *,
    agent: str,
) -> None:
    """
    Install managed files and remove stale symlinks for one agent, prompting first.

    Args:
        manifest_data: The parsed manifest dictionary.
        agent: The agent id being installed.
        config_dir: The agent config directory.
        force: Overwrite conflicting files.
        assume_yes: Remove stale symlinks without prompting.
        skip_init: Skip per-project OpenSpec / codebase-memory-mcp init.
    """
    expected = operations.expected_symlink_targets(manifest_data, agent)

    # Collect managed symlinks no longer declared in the manifest, so the
    # prune pass can remove the ones that the sync no longer maintains.
    stale = [
        relative
        for _, relative in operations.managed_symlinks(config_dir, ROOT)
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
    operations.sync(manifest_data, ROOT, config_dir, force, prune=prune, agent=agent)

    # Per-project tool init (OpenSpec, codebase-memory-mcp). OpenCode-only for
    # now; OMP per-project init is deferred. Only runs when the working
    # directory is inside a git repository; both tools' setup is idempotent.
    if agent == "opencode" and not skip_init:
        project.init_project(
            Path.cwd(),
            # Never bypassed by --yes: installing a binary is a system-level
            # change that must always be an explicit user choice.
            lambda prompt: _confirm(prompt, False),
            ROOT / "src" / "instructions" / "codebase-memory-mcp-agents.md",
            ROOT / "src" / "plugins" / "CodebaseMemoryReminder.ts",
        )

    # Optional shell command bootstrap. Persistent user-controlled change,
    # never bypassed by --yes.
    _bootstrap_shell_command()


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
    targets = names if names else manifest.artifact_names(manifest_data)

    # Pass 1: report drift and collect the artifacts that are behind.
    behind = []
    exit_code = 0
    for artifact_name in targets:
        artifact = manifest.find(manifest_data, artifact_name)
        if artifact is None:
            print(f"  unknown artifact: {artifact_name}")
            exit_code = 1
            continue
        result = merge.update_artifact(MANIFEST, ROOT, artifact, check_only=True)
        if result == merge.DRIFT:
            behind.append(artifact_name)
        elif result != 0:
            exit_code = 1

    if not behind:
        # Unresolved forks report an error without drift, so only claim
        # everything is current when nothing failed.
        if exit_code == 0:
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
        artifact = manifest.find(manifest_data, artifact_name)
        if artifact is None:
            continue
        if merge.update_artifact(MANIFEST, ROOT, artifact, check_only=False) != 0:
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
        manifest_data = manifest.load(MANIFEST)
    except manifest.ManifestError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    try:
        if args.command in ("install", "uninstall"):
            agent = select_agents(getattr(args, "agent", None), command=args.command)
            if agent is None:
                print(
                    "error: no supported agent detected (opencode, omp); "
                    "pass --agent to force one",
                    file=sys.stderr,
                )
                return 2
            config_dir = config.config_dir(agent, manifest_data)
            if args.command == "install":
                _run_install(
                    manifest_data,
                    config_dir,
                    args.force,
                    args.yes,
                    args.no_init,
                    agent=agent,
                )
            else:
                operations.uninstall(manifest_data, ROOT, config_dir, agent=agent)
                _unbootstrap_shell_command()
                if agent == "opencode":
                    # Per-project codebase-memory-mcp init is opencode-only and
                    # lives in the project, not the config dir; uninstall leaves
                    # it alone, so surface its presence.
                    project.uninstall_notice(Path.cwd())
        elif args.command == "vendor":
            return _run_vendor(manifest_data, args.names, args.yes)
    except Exception as error:  # pylint: disable=broad-except
        print(f"error: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
