"""
Update vendor and fork artifacts from their upstream repositories.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import ocmanifest

UP_TO_DATE = 0
ERROR = 1
DRIFT = 2

# Bounded wait for any network subprocess; a hung call would otherwise stall
# the whole sync with no way to abort.
NETWORK_TIMEOUT = 60


def _run(
    *args,
    check=False,
    timeout=None,
) -> subprocess.CompletedProcess:
    """
    Run a subprocess and capture its output.

    Args:
        *args: The command and its arguments.
        check: Raise CalledProcessError on a non-zero exit code.
        timeout: Abort the subprocess after this many seconds.

    Returns:
        The CompletedProcess result of the run.
    """
    try:
        return subprocess.run(
            [str(a) for a in args],
            capture_output=True,
            text=True,
            check=check,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        # A timed-out command is a failed command. Report it as a non-zero
        # result (or a CalledProcessError under check=True) rather than
        # letting the exception escape and crash the caller.
        if check:
            raise subprocess.CalledProcessError(-1, [str(a) for a in args]) from None
        return subprocess.CompletedProcess([str(a) for a in args], -1)


def head_sha(repo: str) -> str | None:
    """
    Return the upstream HEAD commit sha for a repository.

    Args:
        repo: The upstream repository URL.

    Returns:
        The HEAD commit sha, or None if it cannot be resolved.
    """
    result = _run("git", "ls-remote", repo, "HEAD", timeout=NETWORK_TIMEOUT)
    if result.returncode != 0 or not result.stdout.strip():
        return None

    # ls-remote prints "<sha>\tHEAD"; take the sha on the first line.
    return result.stdout.splitlines()[0].split()[0]


def raw_base(repo: str) -> str:
    """
    Map a GitHub repository URL to its raw.githubusercontent.com base.

    Args:
        repo: The repository URL.

    Returns:
        The corresponding raw file-serving base URL.
    """
    normalized = repo.rstrip("/")

    # Strip a trailing ".git" so the URL rewrites cleanly.
    if normalized.endswith(".git"):
        normalized = normalized[:-4]

    prefix = "https://github.com/"
    if normalized.startswith(prefix):
        # github.com/<owner>/<repo> -> raw.githubusercontent.com/<owner>/<repo>
        return "https://raw.githubusercontent.com/" + normalized[len(prefix):]

    # Non-GitHub repo (e.g. a local path in tests) — use it as-is.
    return normalized


def _fetch_raw(
    repo: str,
    source_path: str,
    ref: str,
    dest: Path,
) -> bool:
    """
    Fetch a raw upstream file to a destination path.

    Args:
        repo: The upstream repository URL.
        source_path: The path of the file within the repository.
        ref: The git ref (commit sha or HEAD) to fetch.
        dest: The local destination file path.

    Returns:
        True if the file was fetched successfully.
    """
    url = f"{raw_base(repo)}/{ref}/{source_path}"
    result = _run("curl", "-fsSL", url, "-o", dest, timeout=NETWORK_TIMEOUT)
    return result.returncode == 0


def _clone(
    repo: str,
    dest: Path,
    ref: str,
) -> None:
    """
    Clone a repository at a specific ref into a destination directory.

    Args:
        repo: The upstream repository URL.
        dest: The destination directory.
        ref: The commit sha, or HEAD for the default branch.
    """
    if ref == "HEAD":
        # Default branch: a shallow clone gives us upstream HEAD directly.
        _run("git", "clone", "--depth", "1", repo, dest,
             check=True, timeout=NETWORK_TIMEOUT)
    else:
        # Pinned sha: init an empty repo and fetch just that commit.
        dest.mkdir(parents=True, exist_ok=True)
        _run("git", "-C", dest, "init", "-q", check=True)
        _run("git", "-C", dest, "remote", "add", "origin", repo, check=True)
        _run(
            "git", "-C", dest, "fetch", "-q", "--depth", "1", "origin", ref,
            check=True, timeout=NETWORK_TIMEOUT,
        )
        _run("git", "-C", dest, "checkout", "-q", "FETCH_HEAD", check=True)


def _copy_tree(
    from_dir: Path,
    to_dir: Path,
) -> None:
    """
    Mirror the contents of from_dir into to_dir.

    Copies and overwrites upstream items, and removes local entries that no
    longer exist upstream so the vendor tree stays a faithful mirror.

    Args:
        from_dir: The source directory to copy from.
        to_dir: The destination directory to copy into.
    """
    to_dir.mkdir(parents=True, exist_ok=True)
    upstream: set[str] = set()
    for item in from_dir.iterdir():
        dest = to_dir / item.name
        upstream.add(item.name)
        if item.is_dir():
            _copy_tree(item, dest)
        else:
            shutil.copy2(item, dest)
    # Remove local entries absent upstream (files deleted upstream must not
    # linger as stale copies).
    for item in list(to_dir.iterdir()):
        if item.name not in upstream:
            if item.is_dir() and not item.is_symlink():
                shutil.rmtree(item)
            else:
                item.unlink()


def _merge_file(
    ours_path: Path,
    base_path: Path,
    theirs_path: Path,
) -> bool:
    """
    3-way merge a single file via `git merge-file`.

    Args:
        ours_path: Our customized file, updated in place.
        base_path: The merge base (upstream at the pinned sha).
        theirs_path: The upstream file at HEAD.

    Returns:
        True if conflicts remain after the merge.
    """
    # No recorded base sha yet — merge against an empty file so all upstream
    # content lands as additions instead of a bogus conflict.
    if not base_path.exists():
        base_path.write_text("")
    result = _run("git", "merge-file", "-p", ours_path, base_path, theirs_path)
    # git merge-file: 0 = clean merge, 1 = conflicts, 2+ = hard error (e.g. a
    # non-regular input path). Only 0/1 produce mergeable stdout; on a hard
    # error stdout is empty, so writing it would truncate our customized file
    # to zero bytes. Preserve the local file and fail loudly instead.
    if result.returncode > 1:
        raise OSError(
            f"git merge-file failed (exit {result.returncode}) for {ours_path}; "
            "local customization preserved"
        )
    ours_path.write_text(result.stdout)
    return result.returncode != 0


def _merge_tree(
    local_path: Path,
    base_path: Path,
    theirs_path: Path,
) -> bool:
    """
    3-way merge a directory tree of files.

    Args:
        local_path: Our customized directory, updated in place.
        base_path: The merge base directory.
        theirs_path: The upstream directory at HEAD.

    Returns:
        True if any file left conflicts.
    """
    conflict = False
    for theirs_file in theirs_path.rglob("*"):
        if not theirs_file.is_file():
            continue
        relative = theirs_file.relative_to(theirs_path)
        local_file = local_path / relative
        base_file = local_file if base_path == local_path else base_path / relative
        local_file.parent.mkdir(parents=True, exist_ok=True)
        # New upstream file with no local counterpart — copy it in, nothing
        # of ours to merge.
        if not local_file.exists():
            shutil.copyfile(theirs_file, local_file)
            continue
        if _merge_file(local_file, base_file, theirs_file):
            conflict = True
    return conflict


def _apply_vendor(
    artifact: dict,
    local_path: Path,
) -> None:
    """
    Overwrite a vendor artifact with its upstream content.

    Args:
        artifact: The manifest artifact describing the vendor source.
        local_path: The managed local file or directory to update.

    Raises:
        RuntimeError: If the upstream file cannot be fetched.
    """
    name = artifact["name"]
    repo = artifact["source_repo"]
    source_path = artifact["source_path"]
    if local_path.is_file():
        with tempfile.NamedTemporaryFile(suffix=".up") as temp_file:
            if not _fetch_raw(repo, source_path, "HEAD", Path(temp_file.name)):
                raise RuntimeError(f"{name}: failed to fetch upstream file")
            shutil.copyfile(temp_file.name, local_path)
    else:
        # Directory artifact: clone upstream and copy the source tree over
        # the local one, wholesale.
        with tempfile.TemporaryDirectory() as temp_dir:
            _clone(repo, Path(temp_dir) / "upstream", "HEAD")
            _copy_tree(Path(temp_dir) / "upstream" / source_path, local_path)
    print(f"  {name}: updated from upstream")


def _apply_fork(
    artifact: dict,
    local_path: Path,
) -> bool:
    """
    3-way merge upstream into a fork artifact.

    Args:
        artifact: The manifest artifact describing the fork source.
        local_path: The managed local file or directory to merge into.

    Returns:
        True if conflicts remain after the merge.
    """
    repo = artifact["source_repo"]
    source_path = artifact["source_path"]
    sha = artifact.get("source_sha", "")
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        _clone(repo, temp_path / "upstream", "HEAD")
        theirs_path = temp_path / "upstream" / source_path
        if local_path.is_file():
            base_path = temp_path / "base_file"
            if not _fetch_raw(repo, source_path, sha, base_path):
                # Without the pinned base we cannot do a correct 3-way merge.
                # Fail loudly rather than reuse local as the base, which would
                # silently discard local customizations.
                name = artifact["name"]
                raise RuntimeError(
                    f"{name}: failed to fetch pinned base {sha} for 3-way merge"
                )
            conflict = _merge_file(local_path, base_path, theirs_path)
        else:
            _clone(repo, temp_path / "base", sha)
            conflict = _merge_tree(
                local_path, temp_path / "base" / source_path, theirs_path
            )
    return conflict


def update_artifact(
    manifest_path: Path,
    root: Path,
    artifact: dict,
    check_only: bool = False,
) -> int:
    """
    Update one artifact from its upstream repository.

    Args:
        manifest_path: Path to the manifest file (to record new SHAs).
        root: The repository root.
        artifact: The manifest artifact to update.
        check_only: Report drift without mutating anything.

    Returns:
        0 on success, non-zero on error.
    """
    name = artifact["name"]
    provenance = artifact.get("provenance", "original")
    # "original" artifacts are user-owned files we never touch.
    if provenance == "original":
        print(f"  {name}: original — skipped")
        return 0

    repo = artifact["source_repo"]
    sha = artifact.get("source_sha", "")
    local_path = root / artifact["src"]

    head = head_sha(repo)
    if not head:
        # Upstream unreachable — fail rather than guess at drift.
        print(f"  {name}: cannot resolve upstream HEAD ({repo})")
        return ERROR

    if check_only:
        # Pinned sha matches upstream HEAD — nothing to pull.
        if sha == head:
            print(f"  {name}: up to date")
            return UP_TO_DATE
        pinned = sha or "none"
        print(f"  {name}: behind (pinned {pinned} -> {head})")
        return DRIFT

    if provenance == "vendor":
        try:
            _apply_vendor(artifact, local_path)
        except Exception as error:  # pylint: disable=broad-exception-caught
            print(f"  {name}: update failed: {error}")
            return ERROR
        ocmanifest.set_sha(manifest_path, name, head)
        return 0

    # fork
    # No sha pinned yet — this is the first fork sync: record HEAD as the new
    # base without touching local customizations.
    if not sha:
        print(f"  {name}: first fork update — pinning base, keeping customizations")
        ocmanifest.set_sha(manifest_path, name, head)
        return 0
    try:
        conflict = _apply_fork(artifact, local_path)
    except Exception as error:  # pylint: disable=broad-exception-caught
        print(f"  {name}: update failed: {error}")
        return ERROR
    if conflict:
        # Leave conflict markers for the user to resolve by hand; the sha
        # is not bumped until they fix it and re-run.
        local_target = artifact["src"]
        print(
            f"  {name}: MERGE CONFLICTS — resolve markers in {local_target}, "
            "then re-run to bump sha"
        )
        return 0
    ocmanifest.set_sha(manifest_path, name, head)
    return 0
