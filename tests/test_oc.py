"""Tests for the My AI Code Kit python tooling."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

import config  # noqa: E402
import kit  # noqa: E402
import project  # noqa: E402
import manifest  # noqa: E402
import merge  # noqa: E402
import operations  # noqa: E402
import shell_rc  # noqa: E402

MANIFEST = REPO / "manifest.toml"


def git(*args, cwd=None):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _ok_run(cmd, **kw):
    # Stand-in for subprocess.run in tests that only assert on the command.
    class R:
        returncode = 0
        stdout = ""
        stderr = ""
    return R()


def git_out(*args, cwd=None) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


# ------------------------------------------------------------------ manifest
def test_manifest_loads_and_validates():
    m = manifest.load(MANIFEST)
    names = manifest.artifact_names(m)
    assert "grill-me" in names
    assert "caveman" in names
    assert "glab" in names


def test_set_sha_edits_correct_artifact(tmp_path):
    src = tmp_path / "m.toml"
    src.write_text(
        'version = 2\n'
        '[[artifacts]]\nname = "a"\noperation = "symlink"\n'
        'provenance = "original"\nagents = ["opencode"]\nsrc = "a"\ntarget = "a"\nsource_sha = ""\n'
        '[[artifacts]]\nname = "b"\noperation = "symlink"\n'
        'provenance = "original"\nagents = ["opencode"]\nsrc = "b"\ntarget = "b"\nsource_sha = ""\n'
    )
    manifest.set_sha(src, "b", "abc123")
    m = manifest.load(src)
    assert m["artifacts"][0]["source_sha"] == ""
    assert m["artifacts"][1]["source_sha"] == "abc123"


# ------------------------------------------------------------- config dir
def test_config_dir_env_override(monkeypatch):
    monkeypatch.setenv("OC_CONFIG_DIR", "/tmp/fake")
    assert config.config_dir("opencode", {}) == Path("/tmp/fake")


def test_config_dir_manifest_default(monkeypatch):
    monkeypatch.delenv("OC_CONFIG_DIR", raising=False)
    m = {"config": {"default_config_dir": "~/x"}}
    assert config.config_dir("opencode", m) == Path.home() / "x"


# ---------------------------------------------------------------- install
def test_install_symlinks_text_and_config(tmp_path, monkeypatch):
    monkeypatch.setenv("OC_CONFIG_DIR", str(tmp_path / "cfg"))
    cfg = config.config_dir("opencode", {})
    operations.install(manifest.load(MANIFEST), REPO, cfg)

    cmd = cfg / "commands" / "commit-message.md"
    # commit-message.md carries placeholder substitution, so it is installed
    # as a substituted copy, not a symlink.
    assert not cmd.is_symlink()
    assert "<VALIDATE_COMMIT_SCRIPT>" not in cmd.read_text()
    assert str(cfg / "scripts" / "verify-commit") in cmd.read_text()
    # the validator script entry stays a plain symlink
    assert (cfg / "scripts" / "verify-commit").is_symlink()

    agents = cfg / "AGENTS.md"
    text = agents.read_text()
    assert "caveman-begin" in text
    assert "file-edit-size-limits:start" in text

    tui = json.loads((cfg / "tui.json").read_text())
    assert tui["theme"] == "poimandres-turquoise-expanded"
    # codebase-memory-mcp is per-project now (see project), not global config.
    assert not (cfg / "opencode.json").exists()


def test_install_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("OC_CONFIG_DIR", str(tmp_path / "cfg"))
    cfg = config.config_dir("opencode", {})
    m = manifest.load(MANIFEST)
    operations.install(m, REPO, cfg)
    agents_before = (cfg / "AGENTS.md").read_text()
    operations.install(m, REPO, cfg)
    assert (cfg / "AGENTS.md").read_text() == agents_before
    assert (cfg / "AGENTS.md").read_text().count("caveman-begin") == 1


def test_uninstall_removes_text_blocks(tmp_path, monkeypatch):
    monkeypatch.setenv("OC_CONFIG_DIR", str(tmp_path / "cfg"))
    cfg = config.config_dir("opencode", {})
    m = manifest.load(MANIFEST)
    operations.install(m, REPO, cfg)

    # marker-delimited blocks are removed even when their interior drifted
    # (source edited after install, or hand-edited inside the tool's markers)
    agents = cfg / "AGENTS.md"
    agents.write_text(
        agents.read_text().replace(
            "Respond terse like smart caveman.", "RESPOND VERY VERBOSELY."
        )
    )

    operations.uninstall(m, REPO, cfg)
    final = agents.read_text()
    assert "caveman-begin" not in final
    assert "caveman-end" not in final
    assert "file-edit-size-limits:start" not in final
    assert "file-edit-size-limits:stop" not in final


def test_uninstall_notice_reports_project_init(tmp_path, capsys):
    # A project carrying codebase-memory-mcp per-project init gets a notice
    # that uninstall leaves it alone.
    repo = tmp_path / "proj"
    repo.mkdir()
    git("init", cwd=repo)
    (repo / "AGENTS.md").write_text("<!-- codebase-memory-mcp:start -->\nhi\n")
    (repo / ".opencode" / "plugins").mkdir(parents=True)
    (repo / ".opencode" / "plugins" / "CodebaseMemoryReminder.ts").write_text("x")
    project.uninstall_notice(repo)
    assert "codebase-memory-mcp" in capsys.readouterr().out


def test_uninstall_notice_reports_omp_project_init(tmp_path, capsys):
    # An Oh My Pi install leaves .omp/ artifacts; the notice must surface them.
    repo = tmp_path / "proj"
    repo.mkdir()
    git("init", cwd=repo)
    (repo / ".omp" / "extensions").mkdir(parents=True)
    (repo / ".omp" / "extensions" / "CodebaseMemoryReminder.ts").write_text("x")
    project.uninstall_notice(repo)
    out = capsys.readouterr().out
    assert "codebase-memory-mcp" in out
    assert ".omp" in out


def test_uninstall_notice_silent_without_init(tmp_path, capsys):
    # A clean project (and a non-git dir) triggers no notice.
    repo = tmp_path / "proj"
    repo.mkdir()
    git("init", cwd=repo)
    (repo / "AGENTS.md").write_text("plain\n")
    project.uninstall_notice(repo)
    assert capsys.readouterr().out == ""

    (tmp_path / "notgit").mkdir()
    project.uninstall_notice(tmp_path / "notgit")
    assert capsys.readouterr().out == ""


# -------------------------------------------------------------------- sync
def test_sync_removes_stale_keeps_user_file(tmp_path, monkeypatch):
    monkeypatch.setenv("OC_CONFIG_DIR", str(tmp_path / "cfg"))
    cfg = config.config_dir("opencode", {})
    m = manifest.load(MANIFEST)
    operations.install(m, REPO, cfg)

    stale = cfg / "commands" / "stale-ghost.md"
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.symlink_to(REPO / "src" / "commands" / "fix.md")

    user = cfg / "commands" / "my-own.md"
    user.write_text("user file")

    operations.sync(m, REPO, cfg)
    assert not stale.exists()
    assert user.exists()


def test_sync_prune_false_keeps_stale(tmp_path, monkeypatch):
    monkeypatch.setenv("OC_CONFIG_DIR", str(tmp_path / "cfg"))
    cfg = config.config_dir("opencode", {})
    m = manifest.load(MANIFEST)
    operations.install(m, REPO, cfg)

    stale = cfg / "commands" / "stale-ghost.md"
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.symlink_to(REPO / "src" / "commands" / "fix.md")

    operations.sync(m, REPO, cfg, prune=False)
    assert stale.exists()  # stale symlink left in place when pruning disabled


# ---------------------------------------------------------------- uninstall
def test_uninstall_removes_managed_only(tmp_path, monkeypatch):
    monkeypatch.setenv("OC_CONFIG_DIR", str(tmp_path / "cfg"))
    cfg = config.config_dir("opencode", {})
    m = manifest.load(MANIFEST)
    operations.install(m, REPO, cfg)
    user = cfg / "commands" / "my-own.md"
    user.write_text("keep me")
    operations.uninstall(m, REPO, cfg)
    assert user.exists()
    assert not (cfg / "commands" / "commit-message.md").exists()


def test_uninstall_removes_legacy_copy_of_plain_symlink(tmp_path, monkeypatch):
    # A plain symlink artifact installed as a real file copy by an earlier
    # tool (not a symlink) is a managed leftover: uninstall removes it when it
    # matches the source exactly, but keeps a user-edited file at the same
    # kind of target.
    monkeypatch.setenv("OC_CONFIG_DIR", str(tmp_path / "cfg"))
    cfg = config.config_dir("opencode", {})
    root = tmp_path / "root"

    src = root / "src" / "scripts" / "verify.sh"
    src.parent.mkdir(parents=True)
    src.write_text("#!/bin/sh\nmanaged\n")
    managed = {"name": "managed", "operation": "symlink", "agents": ["opencode"],
               "src": "src/scripts/verify.sh", "target": "scripts/verify.sh"}

    edited_src = root / "src" / "themes" / "theme.json"
    edited_src.parent.mkdir(parents=True)
    edited_src.write_text('{"name": "managed"}\n')
    edited = {"name": "edited", "operation": "symlink", "agents": ["opencode"],
              "src": "src/themes/theme.json", "target": "themes/theme.json"}

    manifest = {"version": 2, "artifacts": [managed, edited]}

    # Installed as real files (copies), not symlinks.
    target = cfg / "scripts" / "verify.sh"
    target.parent.mkdir(parents=True)
    target.write_text(src.read_text())
    edited_target = cfg / "themes" / "theme.json"
    edited_target.parent.mkdir(parents=True)
    edited_target.write_text('{"name": "USER EDITED"}\n')

    operations.uninstall(manifest, root, cfg)
    assert not target.exists()
    assert edited_target.exists()


# ------------------------------------------------------------------- merge
def _make_repo(path: Path, files: dict[str, str]) -> str:
    # Build a throwaway local git repo to stand in for a remote upstream.
    path.mkdir(parents=True, exist_ok=True)
    git("init", "-q", cwd=path)
    for rel, content in files.items():
        f = path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content)
    git("add", "-A", cwd=path)
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "c", cwd=path)
    return git_out("rev-parse", "HEAD", cwd=path)


def test_merge_file_clean(tmp_path):
    base = tmp_path / "base"
    ours = tmp_path / "ours"
    theirs = tmp_path / "theirs"
    base.write_text("header\nbase\nmiddle\nmiddle\nmiddle\nfooter\n")
    ours.write_text("header\nMY CHANGE\nmiddle\nmiddle\nmiddle\nfooter\n")
    theirs.write_text("header\nbase\nmiddle\nmiddle\nmiddle\nUPSTREAM\n")
    conflict = merge._merge_file(ours, base, theirs)
    assert conflict is False
    result = ours.read_text()
    assert "MY CHANGE" in result
    assert "UPSTREAM" in result
    assert "<<<<<<<" not in result


def test_merge_file_conflict(tmp_path):
    base = tmp_path / "base"
    ours = tmp_path / "ours"
    theirs = tmp_path / "theirs"
    base.write_text("line\n")
    ours.write_text("MINE\n")
    theirs.write_text("THEIRS\n")
    conflict = merge._merge_file(ours, base, theirs)
    assert conflict is True
    assert "<<<<<<<" in ours.read_text()


def test_vendor_update_overwrites_and_bumps(tmp_path, monkeypatch):
    upstream = tmp_path / "upstream"
    sha1 = _make_repo(upstream, {"f.md": "v1\n"})
    (upstream / "f.md").write_text("v2\n")
    git("add", "-A", cwd=upstream)
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "c2", cwd=upstream)
    head = git_out("rev-parse", "HEAD", cwd=upstream)

    root = tmp_path / "root"
    root.mkdir()
    src = root / "src" / "commands" / "f.md"
    src.parent.mkdir(parents=True)
    src.write_text("old\n")

    mp = tmp_path / "m.toml"
    mp.write_text(
        f'version = 2\n[[artifacts]]\nname = "f"\noperation = "symlink"\nagents = ["opencode"]\n'
        f'provenance = "vendor"\nsource_repo = "{upstream}"\n'
        f'source_path = "f.md"\nsource_sha = "{sha1}"\n'
        f'src = "src/commands/f.md"\ntarget = "commands/f.md"\n'
    )
    art = manifest.find(manifest.load(mp), "f")

    monkeypatch.setattr(
        merge, "_fetch_raw",
        lambda repo, spath, ref, dest: _local_fetch(Path(repo), spath, ref, Path(dest)),
    )
    assert merge.update_artifact(mp, root, art) == 0
    assert src.read_text().strip() == "v2"
    assert manifest.load(mp)["artifacts"][0]["source_sha"] == head


def _local_fetch(repo: Path, spath: str, ref: str, dest: Path) -> bool:
    # Offline stand-in for merge._fetch_raw: read the file straight from
    # the throwaway repo instead of hitting the network with curl.
    r = subprocess.run(
        ["git", "show", f"{ref}:{spath}"], cwd=repo, capture_output=True, text=True
    )
    if r.returncode != 0:
        return False
    dest.write_text(r.stdout)  # preserve exact bytes, incl. trailing newline
    return True


def test_fork_first_merge_pins_without_touching(tmp_path, monkeypatch):
    upstream = tmp_path / "upstream"
    head = _make_repo(upstream, {"f.md": "v1\n"})

    root = tmp_path / "root"
    root.mkdir()
    src = root / "src" / "commands" / "f.md"
    src.parent.mkdir(parents=True)
    src.write_text("MY CUSTOM\n")

    mp = tmp_path / "m.toml"
    mp.write_text(
        f'version = 2\n[[artifacts]]\nname = "f"\noperation = "symlink"\nagents = ["opencode"]\n'
        f'provenance = "fork"\nsource_repo = "{upstream}"\n'
        f'source_path = "f.md"\nsource_sha = ""\n'
        f'src = "src/commands/f.md"\ntarget = "commands/f.md"\n'
    )
    art = manifest.find(manifest.load(mp), "f")
    assert merge.update_artifact(mp, root, art) == 0
    assert src.read_text() == "MY CUSTOM\n"  # untouched
    assert manifest.load(mp)["artifacts"][0]["source_sha"] == head


def test_fork_merge_keeps_customization_and_merges(tmp_path, monkeypatch):
    upstream = tmp_path / "upstream"
    base_content = "header\nbase\nmiddle\nmiddle\nmiddle\nfooter\n"
    sha1 = _make_repo(upstream, {"f.md": base_content})
    # upstream changes the footer
    (upstream / "f.md").write_text(
        "header\nbase\nmiddle\nmiddle\nmiddle\nUPSTREAM footer\n"
    )
    git("add", "-A", cwd=upstream)
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "c2", cwd=upstream)
    head = git_out("rev-parse", "HEAD", cwd=upstream)

    root = tmp_path / "root"
    root.mkdir()
    src = root / "src" / "commands" / "f.md"
    src.parent.mkdir(parents=True)
    # our fork customized the base line
    src.write_text("header\nMY CUSTOMIZATION\nmiddle\nmiddle\nmiddle\nfooter\n")

    mp = tmp_path / "m.toml"
    mp.write_text(
        f'version = 2\n[[artifacts]]\nname = "f"\noperation = "symlink"\nagents = ["opencode"]\n'
        f'provenance = "fork"\nsource_repo = "{upstream}"\n'
        f'source_path = "f.md"\nsource_sha = "{sha1}"\n'
        f'src = "src/commands/f.md"\ntarget = "commands/f.md"\n'
    )
    art = manifest.find(manifest.load(mp), "f")
    monkeypatch.setattr(
        merge, "_fetch_raw",
        lambda repo, spath, ref, dest: _local_fetch(Path(repo), spath, ref, Path(dest)),
    )
    assert merge.update_artifact(mp, root, art) == 0
    result = src.read_text()
    assert "MY CUSTOMIZATION" in result
    assert "UPSTREAM footer" in result
    assert manifest.load(mp)["artifacts"][0]["source_sha"] == head


def test_fork_conflict_lifecycle_converges(tmp_path, monkeypatch):
    upstream = tmp_path / "upstream"
    sha1 = _make_repo(upstream, {"f.md": "a\nb\nc\n\n\n\n"})
    # upstream rewrites the tail region our fork also touches
    (upstream / "f.md").write_text("a\nb\nC\n")
    git("add", "-A", cwd=upstream)
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "c2", cwd=upstream)
    head = git_out("rev-parse", "HEAD", cwd=upstream)

    root = tmp_path / "root"
    src = root / "src" / "commands" / "f.md"
    src.parent.mkdir(parents=True)
    src.write_text("a\nb\nc\n\n\n\nOUR_EXTRA\n")

    mp = tmp_path / "m.toml"
    mp.write_text(
        f'version = 2\n[[artifacts]]\nname = "f"\noperation = "symlink"\nagents = ["opencode"]\n'
        f'provenance = "fork"\nsource_repo = "{upstream}"\n'
        f'source_path = "f.md"\nsource_sha = "{sha1}"\n'
        f'src = "src/commands/f.md"\ntarget = "commands/f.md"\n'
    )
    art = manifest.find(manifest.load(mp), "f")
    monkeypatch.setattr(
        merge, "_fetch_raw",
        lambda repo, spath, ref, dest: _local_fetch(Path(repo), spath, ref, Path(dest)),
    )

    # Pull conflicts: markers land and the base advances to upstream HEAD.
    assert merge.update_artifact(mp, root, art) == 0
    assert "<<<<<<<" in src.read_text()
    assert manifest.load(mp)["artifacts"][0]["source_sha"] == head

    # Unresolved markers must block further updates instead of re-merging the
    # marked file (which nests markers and never converges).
    art = manifest.find(manifest.load(mp), "f")  # each run reloads the manifest
    assert merge.update_artifact(mp, root, art, check_only=True) == merge.ERROR
    assert src.read_text().count("<<<<<<<") == 1

    # Resolve, keeping both the upstream change and our addition.
    src.write_text("a\nb\nC\n\nOUR_EXTRA\n")

    # The resolved file is based on upstream HEAD, so the re-run finalizes
    # cleanly rather than replaying the same merge.
    art = manifest.find(manifest.load(mp), "f")
    assert merge.update_artifact(mp, root, art) == 0
    assert "<<<<<<<" not in src.read_text()
    assert manifest.load(mp)["artifacts"][0]["source_sha"] == head


# ------------------------------------------------------------ check / shims
def test_check_valid_source_path_reports_behind(tmp_path, monkeypatch):
    upstream = tmp_path / "upstream"
    head = _make_repo(upstream, {"f.md": "v1\n"})
    root = tmp_path / "root"
    root.mkdir()
    mp = tmp_path / "m.toml"
    mp.write_text(
        f'version = 2\n[[artifacts]]\nname = "f"\noperation = "symlink"\nagents = ["opencode"]\n'
        f'provenance = "vendor"\nsource_repo = "{upstream}"\n'
        f'source_path = "f.md"\nsource_sha = ""\n'
        f'src = "src/f.md"\ntarget = "f.md"\n'
    )
    art = manifest.find(manifest.load(mp), "f")
    monkeypatch.setattr(
        merge, "_fetch_raw",
        lambda repo, spath, ref, dest: _local_fetch(Path(repo), spath, ref, Path(dest)),
    )
    assert merge.update_artifact(mp, root, art, check_only=True) == merge.DRIFT
    assert manifest.load(mp)["artifacts"][0]["source_sha"] == ""  # no mutation


# ---------------------------------------------------------------- entrypoint
def test_oc_entrypoint_paths_resolve_to_repo():
    import kit  # noqa: PLC0415

    # Guards the CLI entrypoint against ROOT/MANIFEST regressions: an off-by-one
    # ROOT or a wrong manifest filename makes every subcommand fail.
    assert kit.ROOT == REPO
    assert kit.MANIFEST == REPO / "manifest.toml"
    assert kit.MANIFEST.exists()


def test_oc_cli_install_dispatch(tmp_path, monkeypatch):
    monkeypatch.setenv("OC_CONFIG_DIR", str(tmp_path / "cfg"))
    import kit  # noqa: PLC0415

    # --no-init: keep this test hermetic. Per-project init (OpenSpec,
    # codebase-memory-mcp) would mutate the real working tree and PATH tools.
    assert kit.main(["install", "--yes", "--no-init", "--agent", "opencode"]) == 0
    cfg = tmp_path / "cfg"
    assert (cfg / "AGENTS.md").exists()
    assert (cfg / "commands" / "commit-message.md").exists()


def test_oc_cli_missing_manifest_returns_error(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("OC_CONFIG_DIR", str(tmp_path / "cfg"))
    import kit  # noqa: PLC0415

    # A manifest we cannot find must fail cleanly (exit 2), not traceback.
    original = kit.MANIFEST
    kit.MANIFEST = tmp_path / "nope.toml"
    try:
        assert kit.main(["install", "--yes"]) == 2
    finally:
        kit.MANIFEST = original
    assert "manifest not found" in capsys.readouterr().err


# --------------------------------------------------------- dir artifacts
def test_vendor_dir_update_prunes_deleted(tmp_path, monkeypatch):
    upstream = tmp_path / "upstream"
    _make_repo(upstream, {"skills/x/a.md": "a1\n", "skills/x/b.md": "b1\n"})
    # upstream deletes b.md and adds c.md
    (upstream / "skills" / "x" / "b.md").unlink()
    (upstream / "skills" / "x" / "c.md").write_text("c1\n")
    git("add", "-A", cwd=upstream)
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "c2", cwd=upstream)
    head = git_out("rev-parse", "HEAD", cwd=upstream)

    root = tmp_path / "root"
    src = root / "src" / "skills" / "x"
    src.mkdir(parents=True)
    (src / "a.md").write_text("old a\n")
    (src / "b.md").write_text("old b\n")  # deleted upstream — must be pruned

    mp = tmp_path / "m.toml"
    mp.write_text(
        f'version = 2\n[[artifacts]]\nname = "x"\noperation = "symlink"\nagents = ["opencode"]\n'
        f'provenance = "vendor"\nsource_repo = "{upstream}"\n'
        f'source_path = "skills/x"\nsource_sha = ""\n'
        f'src = "src/skills/x"\ntarget = "skills/x"\n'
    )
    art = manifest.find(manifest.load(mp), "x")
    assert merge.update_artifact(mp, root, art) == 0
    assert (src / "a.md").read_text().strip() == "a1"
    assert (src / "c.md").read_text().strip() == "c1"
    assert not (src / "b.md").exists()  # pruned
    assert manifest.load(mp)["artifacts"][0]["source_sha"] == head


def test_fork_dir_merge_applies_upstream_keeps_custom(tmp_path, monkeypatch):
    upstream = tmp_path / "upstream"
    sha1 = _make_repo(upstream, {"skills/x/f.md": "header\nbase\nmiddle\nfooter\n"})
    (upstream / "skills" / "x" / "f.md").write_text(
        "header\nbase\nmiddle\nUPSTREAM footer\n"
    )
    git("add", "-A", cwd=upstream)
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "c2", cwd=upstream)
    head = git_out("rev-parse", "HEAD", cwd=upstream)

    root = tmp_path / "root"
    src = root / "src" / "skills" / "x"
    src.mkdir(parents=True)
    (src / "f.md").write_text("header\nMY CUSTOM\nmiddle\nfooter\n")

    mp = tmp_path / "m.toml"
    mp.write_text(
        f'version = 2\n[[artifacts]]\nname = "x"\noperation = "symlink"\nagents = ["opencode"]\n'
        f'provenance = "fork"\nsource_repo = "{upstream}"\n'
        f'source_path = "skills/x"\nsource_sha = "{sha1}"\n'
        f'src = "src/skills/x"\ntarget = "skills/x"\n'
    )
    art = manifest.find(manifest.load(mp), "x")
    assert merge.update_artifact(mp, root, art) == 0
    result = (src / "f.md").read_text()
    assert "MY CUSTOM" in result
    assert "UPSTREAM footer" in result
    assert manifest.load(mp)["artifacts"][0]["source_sha"] == head


def test_fork_base_fetch_failure_does_not_clobber(tmp_path, monkeypatch):
    upstream = tmp_path / "upstream"
    sha1 = _make_repo(upstream, {"f.md": "base\n"})
    (upstream / "f.md").write_text("upstream new\n")
    git("add", "-A", cwd=upstream)
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "c2", cwd=upstream)

    root = tmp_path / "root"
    root.mkdir()
    src = root / "src" / "commands" / "f.md"
    src.parent.mkdir(parents=True)
    src.write_text("MY CUSTOM\n")

    mp = tmp_path / "m.toml"
    mp.write_text(
        f'version = 2\n[[artifacts]]\nname = "f"\noperation = "symlink"\nagents = ["opencode"]\n'
        f'provenance = "fork"\nsource_repo = "{upstream}"\n'
        f'source_path = "f.md"\nsource_sha = "{sha1}"\n'
        f'src = "src/commands/f.md"\ntarget = "commands/f.md"\n'
    )
    art = manifest.find(manifest.load(mp), "f")
    # base fetch always fails — update must fail cleanly and leave local intact
    monkeypatch.setattr(merge, "_fetch_raw", lambda repo, spath, ref, dest: False)
    assert merge.update_artifact(mp, root, art) == merge.ERROR
    assert src.read_text() == "MY CUSTOM\n"  # untouched
    assert manifest.load(mp)["artifacts"][0]["source_sha"] == sha1  # not bumped


# ------------------------------------------------------------ replace-copy
def _replace_artifact() -> dict:
    return {
        "name": "cmd",
        "operation": "symlink",
        "provenance": "original",
        "entries": [
            {
                "src": "src/commands/cmd.md",
                "target": "commands/cmd.md",
                "replace": {"<SCRIPT>": "{config_dir}/scripts/run.sh"},
            }
        ],
    }


def test_replace_upgrade_from_symlink_does_not_clobber_source(tmp_path, monkeypatch):
    monkeypatch.setenv("OC_CONFIG_DIR", str(tmp_path / "cfg"))
    cfg = config.config_dir("opencode", {})
    root = tmp_path / "root"
    src = root / "src" / "commands" / "cmd.md"
    src.parent.mkdir(parents=True)
    src.write_text("run <SCRIPT>\n")

    # old install left a plain symlink at the target
    target = cfg / "commands" / "cmd.md"
    target.parent.mkdir(parents=True)
    target.symlink_to(src)

    operations.symlink(root, cfg, _replace_artifact())
    # repo source placeholder is intact (not clobbered through the symlink)
    assert "<SCRIPT>" in src.read_text()
    # target is now a substituted copy, not a symlink
    assert not target.is_symlink()
    assert f"{cfg}/scripts/run.sh" in target.read_text()


def test_replace_copy_honors_force(tmp_path, monkeypatch):
    monkeypatch.setenv("OC_CONFIG_DIR", str(tmp_path / "cfg"))
    cfg = config.config_dir("opencode", {})
    root = tmp_path / "root"
    src = root / "src" / "commands" / "cmd.md"
    src.parent.mkdir(parents=True)
    src.write_text("run <SCRIPT>\n")

    target = cfg / "commands" / "cmd.md"
    target.parent.mkdir(parents=True)
    target.write_text("USER FILE\n")

    operations.symlink(root, cfg, _replace_artifact())
    assert target.read_text() == "USER FILE\n"  # kept without --force
    operations.symlink(root, cfg, _replace_artifact(), force=True)
    assert f"{cfg}/scripts/run.sh" in target.read_text()  # overwritten


def test_replace_copy_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("OC_CONFIG_DIR", str(tmp_path / "cfg"))
    cfg = config.config_dir("opencode", {})
    root = tmp_path / "root"
    src = root / "src" / "commands" / "cmd.md"
    src.parent.mkdir(parents=True)
    src.write_text("run <SCRIPT>\n")

    operations.symlink(root, cfg, _replace_artifact())
    content = (cfg / "commands" / "cmd.md").read_text()
    operations.symlink(root, cfg, _replace_artifact())
    assert (cfg / "commands" / "cmd.md").read_text() == content  # unchanged


def test_uninstall_keeps_user_file_at_replace_target(tmp_path, monkeypatch):
    monkeypatch.setenv("OC_CONFIG_DIR", str(tmp_path / "cfg"))
    cfg = config.config_dir("opencode", {})
    root = tmp_path / "root"
    src = root / "src" / "commands" / "cmd.md"
    src.parent.mkdir(parents=True)
    src.write_text("run <SCRIPT>\n")

    artifact = _replace_artifact()
    manifest = {"version": 2, "artifacts": [artifact]}

    # a user's real file (content differs from the managed copy) is kept
    target = cfg / "commands" / "cmd.md"
    target.parent.mkdir(parents=True)
    target.write_text("USER EDITED CONTENT\n")
    operations.uninstall(manifest, root, cfg)
    assert target.exists()

    # the managed copy is removed
    target.unlink()
    operations.symlink(root, cfg, artifact)
    assert target.exists()
    operations.uninstall(manifest, root, cfg)
    assert not target.exists()


def test_uninstall_removes_stale_substituted_copy(tmp_path, monkeypatch):
    # A substituted copy installed from an older source must still be removed
    # when the repo source drifted since install. It embeds the tool's
    # resolved config-dir path, which marks it as managed.
    monkeypatch.setenv("OC_CONFIG_DIR", str(tmp_path / "cfg"))
    cfg = config.config_dir("opencode", {})
    root = tmp_path / "root"
    src = root / "src" / "commands" / "cmd.md"
    src.parent.mkdir(parents=True)
    src.write_text("old run <SCRIPT> text\n")

    artifact = _replace_artifact()
    manifest = {"version": 2, "artifacts": [artifact]}

    operations.install(manifest, root, cfg)
    target = cfg / "commands" / "cmd.md"
    assert target.exists()

    # source drifts after install (e.g. the user edited the repo command)
    src.write_text("new run <SCRIPT> wording\n")
    operations.uninstall(manifest, root, cfg)
    assert not target.exists()


# ---------------------------------------------------- config_merge guards
def test_config_merge_refuses_unparseable_config(tmp_path, monkeypatch):
    monkeypatch.setenv("OC_CONFIG_DIR", str(tmp_path / "cfg"))
    cfg = config.config_dir("opencode", {})
    target = cfg / "opencode.json"
    target.parent.mkdir(parents=True)
    target.write_text("{ not json !! }\n")
    artifact = {"config_file": "opencode.json", "config_path": "a.b",
                "value": '"x"'}
    before = target.read_text()
    with pytest.raises(ValueError):
        operations.config_merge(tmp_path, cfg, artifact)
    assert target.read_text() == before  # untouched


def test_config_merge_refuses_non_object_config(tmp_path, monkeypatch):
    monkeypatch.setenv("OC_CONFIG_DIR", str(tmp_path / "cfg"))
    cfg = config.config_dir("opencode", {})
    target = cfg / "opencode.json"
    target.parent.mkdir(parents=True)
    target.write_text("[1, 2, 3]\n")
    artifact = {"config_file": "opencode.json", "config_path": "a.b",
                "value": '"x"'}
    with pytest.raises(ValueError):
        operations.config_merge(tmp_path, cfg, artifact)


# ------------------------------------------------------------ validation
def test_validate_rejects_non_string_replace_value():
    data = {
        "version": 2,
        "artifacts": [{
            "name": "x", "operation": "symlink", "provenance": "original", "agents": ["opencode"],
            "entries": [{"src": "a", "target": "b",
                         "replace": {"<X>": 123}}],
        }],
    }
    with pytest.raises(manifest.ManifestError):
        manifest.validate(data)


def test_validate_rejects_single_form_replace():
    data = {
        "version": 2,
        "artifacts": [{
            "name": "x", "operation": "symlink", "provenance": "original", "agents": ["opencode"],
            "src": "a", "target": "b", "replace": {"<X>": "y"},
        }],
    }
    with pytest.raises(manifest.ManifestError):
        manifest.validate(data)


def test_validate_accepts_empty_string_config_value():
    data = {
        "version": 2,
        "artifacts": [{
            "name": "x", "operation": "config-merge", "provenance": "original", "agents": ["opencode"],
            "config_file": "tui.json", "config_path": "theme", "value": "",
        }],
    }
    manifest.validate(data)  # must not raise


def test_validate_rejects_non_string_config_value():
    data = {
        "version": 2,
        "artifacts": [{
            "name": "x", "operation": "config-merge", "provenance": "original", "agents": ["opencode"],
            "config_file": "tui.json", "config_path": "theme", "value": 123,
        }],
    }
    with pytest.raises(manifest.ManifestError):
        manifest.validate(data)


def test_config_merge_yaml_sets_theme_and_is_idempotent(tmp_path):
    cfg = tmp_path / "omp"
    cfg.mkdir()
    target = cfg / "config.yml"
    target.write_text(
        "enabledModels:\n"
        "  - deepinfra/deepseek-ai/DeepSeek-V4-Flash-0731\n"
        "theme:\n"
        "  dark: other\n"
        "setupVersion: 2\n"
    )
    artifact = {"config_file": "config.yml", "config_path": "theme.dark",
                "value": '"github-dark"'}
    operations.config_merge(Path("."), cfg, artifact)
    assert target.read_text() == (
        "enabledModels:\n"
        "  - deepinfra/deepseek-ai/DeepSeek-V4-Flash-0731\n"
        "theme:\n"
        "  dark: github-dark\n"
        "setupVersion: 2\n"
    )
    # idempotent: a second run leaves the file unchanged
    before = target.read_text()
    operations.config_merge(Path("."), cfg, artifact)
    assert target.read_text() == before


def test_config_merge_yaml_inserts_missing_theme_block(tmp_path):
    cfg = tmp_path / "omp"
    cfg.mkdir()
    target = cfg / "config.yml"
    target.write_text("setupVersion: 2\n")
    operations.config_merge(Path("."), cfg, artifact := {
        "config_file": "config.yml", "config_path": "theme.dark",
        "value": '"github-dark"',
    })
    assert target.read_text() == (
        "setupVersion: 2\n"
        "\n"
        "theme:\n"
        "  dark: github-dark\n"
    )


# ------------------------------------------------------------------ project
def test_git_root_resolves_toplevel_from_subdir(tmp_path):
    git("init", cwd=tmp_path)
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    assert project.git_root(sub) == tmp_path.resolve()


def test_git_root_none_outside_repo(tmp_path):
    assert project.git_root(tmp_path) is None


def test_prepend_instruction_is_idempotent(tmp_path):
    src = tmp_path / "instruction.md"
    src.write_text(
        "<!-- codebase-memory-mcp:start -->\n# block\n<!-- codebase-memory-mcp:end -->\n"
    )
    root = tmp_path / "proj"
    root.mkdir()
    (root / "AGENTS.md").write_text("existing\n")

    project._prepend_instruction(root, src)
    first = (root / "AGENTS.md").read_text()
    assert first.startswith("<!-- codebase-memory-mcp:start -->")
    assert first.endswith("existing\n")

    project._prepend_instruction(root, src)
    assert (root / "AGENTS.md").read_text() == first


def test_install_plugin(tmp_path):
    src = tmp_path / "CodebaseMemoryReminder.oc.ts"
    src.write_text("// plugin")
    root = tmp_path / "proj"
    root.mkdir()
    project._install_plugin(root, Path(".opencode") / "plugins", src)
    assert (root / ".opencode" / "plugins" / "CodebaseMemoryReminder.ts").read_text() == (
        "// plugin"
    )


def test_merge_mcp_config_idempotent_keeps_existing(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    project._merge_mcp_config(root, "/bin/cbm")
    first = (root / ".opencode" / "opencode.json").read_text()
    assert json.loads(first)["mcp"]["codebase-memory-mcp"]["command"] == ["/bin/cbm"]

    project._merge_mcp_config(root, "/bin/cbm")
    assert (root / ".opencode" / "opencode.json").read_text() == first


def test_merge_mcp_config_preserves_user_entry(tmp_path):
    root = tmp_path / "proj"
    (root / ".opencode").mkdir(parents=True)
    (root / ".opencode" / "opencode.json").write_text(
        json.dumps({"mcp": {"codebase-memory-mcp": {"command": ["/custom"]}}})
    )
    project._merge_mcp_config(root, "/bin/cbm")
    data = json.loads((root / ".opencode" / "opencode.json").read_text())
    assert data["mcp"]["codebase-memory-mcp"]["command"] == ["/custom"]


def test_init_project_skips_outside_repo(tmp_path):
    # Not a git repo: init must no-op without invoking any tool.
    calls = []
    confirm = lambda prompt: calls.append(prompt) or True  # noqa: E731
    project.init_project(
        tmp_path, confirm, tmp_path / "no.md", tmp_path / "no.ts", tmp_path / "no.omp.ts", "opencode"
    )
    assert calls == []
    assert not (tmp_path / "AGENTS.md").exists()
    assert not (tmp_path / ".opencode").exists()


def test_init_openspec_uses_omp_tools(tmp_path, monkeypatch):
    # OpenSpec must be initialized for Oh My Pi with its own `--tools` value,
    # not the opencode one.
    root = tmp_path / "proj"
    root.mkdir()
    calls = []
    monkeypatch.setattr(
        project.subprocess, "run",
        lambda cmd, **kw: calls.append(cmd) or _ok_run(cmd, **kw),
    )
    project._init_openspec(root, "/bin/openspec", "omp")
    assert calls[0] == ["/bin/openspec", "init", "--tools", "oh-my-pi"]


def test_omp_install_dispatches_project_init(tmp_path, monkeypatch):
    # `setup install --agent omp` must reach per-project init (OpenSpec) for
    # Oh My Pi, not silently skip it.
    calls = []
    monkeypatch.setattr(kit.operations, "sync", lambda *a, **k: None)
    monkeypatch.setattr(kit.project, "init_project", lambda *a, **k: calls.append(a))
    monkeypatch.setattr(kit, "_bootstrap_shell_command", lambda: None)
    kit._run_install(
        manifest.load(MANIFEST), tmp_path, force=True, assume_yes=True,
        skip_init=False, agent="omp",
    )
    assert calls, "omp install must call per-project init"


def _write_instruction(tmp_path) -> Path:
    src = tmp_path / "instruction.md"
    src.write_text(
        "<!-- codebase-memory-mcp:start -->\n# block\n<!-- codebase-memory-mcp:end -->\n"
    )
    return src


def _write_omp_plugin(tmp_path) -> Path:
    plugin = tmp_path / "CodebaseMemoryReminder.omp.ts"
    plugin.write_text("// omp reminder extension\n")
    return plugin


def test_omp_init_writes_mcp_json(tmp_path, monkeypatch):
    root = tmp_path / "proj"
    root.mkdir()
    monkeypatch.setattr(project.subprocess, "run", _ok_run)
    monkeypatch.setattr(project, "OMP_USER_MCP", tmp_path / "user" / "mcp.json")
    project._init_codebase_omp(root, "/bin/cbm", _write_instruction(tmp_path), _write_omp_plugin(tmp_path), lambda p: True)
    data = json.loads((root / ".omp" / "mcp.json").read_text())
    assert data["mcpServers"]["codebase-memory-mcp"] == {
        "enabled": True,
        "command": "/bin/cbm",
    }


def test_omp_init_installs_extension_and_instruction(tmp_path, monkeypatch):
    root = tmp_path / "proj"
    root.mkdir()
    monkeypatch.setattr(project.subprocess, "run", _ok_run)
    monkeypatch.setattr(project, "OMP_USER_MCP", tmp_path / "user" / "mcp.json")
    project._init_codebase_omp(root, "/bin/cbm", _write_instruction(tmp_path), _write_omp_plugin(tmp_path), lambda p: True)
    assert (
        root / ".omp" / "extensions" / "CodebaseMemoryReminder.ts"
    ).read_text() == "// omp reminder extension\n"
    assert (root / "AGENTS.md").read_text().startswith("<!-- codebase-memory-mcp:start -->")


def test_omp_init_does_not_touch_opencode(tmp_path, monkeypatch):
    root = tmp_path / "proj"
    root.mkdir()
    monkeypatch.setattr(project.subprocess, "run", _ok_run)
    monkeypatch.setattr(project, "OMP_USER_MCP", tmp_path / "user" / "mcp.json")
    project._init_codebase_omp(root, "/bin/cbm", _write_instruction(tmp_path), _write_omp_plugin(tmp_path), lambda p: True)
    assert not (root / ".opencode").exists()


def test_omp_denylist_accept_removes_entry(tmp_path, monkeypatch, capsys):
    user_mcp = tmp_path / "user" / "mcp.json"
    user_mcp.parent.mkdir(parents=True)
    user_mcp.write_text(json.dumps({"disabledServers": ["codebase-memory-mcp"]}))
    root = tmp_path / "proj"
    root.mkdir()
    monkeypatch.setattr(project.subprocess, "run", _ok_run)
    monkeypatch.setattr(project, "OMP_USER_MCP", user_mcp)
    calls = []
    project._init_codebase_omp(
        root, "/bin/cbm", _write_instruction(tmp_path), _write_omp_plugin(tmp_path),
        lambda p: calls.append(p) or True,
    )
    assert calls, "denylist entry must prompt"
    data = json.loads(user_mcp.read_text())
    assert "codebase-memory-mcp" not in data["disabledServers"]


def test_omp_denylist_decline_reports_unavailable(tmp_path, monkeypatch, capsys):
    user_mcp = tmp_path / "user" / "mcp.json"
    user_mcp.parent.mkdir(parents=True)
    user_mcp.write_text(json.dumps({"disabledServers": ["codebase-memory-mcp"]}))
    root = tmp_path / "proj"
    root.mkdir()
    monkeypatch.setattr(project.subprocess, "run", _ok_run)
    monkeypatch.setattr(project, "OMP_USER_MCP", user_mcp)
    project._init_codebase_omp(
        root, "/bin/cbm", _write_instruction(tmp_path), _write_omp_plugin(tmp_path),
        lambda p: False,
    )
    data = json.loads(user_mcp.read_text())
    assert "codebase-memory-mcp" in data["disabledServers"]  # untouched
    assert "unavailable" in capsys.readouterr().out


def test_omp_init_is_idempotent(tmp_path, monkeypatch):
    root = tmp_path / "proj"
    root.mkdir()
    monkeypatch.setattr(project.subprocess, "run", _ok_run)
    monkeypatch.setattr(project, "OMP_USER_MCP", tmp_path / "user" / "mcp.json")
    plugin = _write_omp_plugin(tmp_path)
    instruction = _write_instruction(tmp_path)
    project._init_codebase_omp(root, "/bin/cbm", instruction, plugin, lambda p: True)
    mcp_before = (root / ".omp" / "mcp.json").read_text()
    ext_before = (root / ".omp" / "extensions" / "CodebaseMemoryReminder.ts").read_text()
    agents_before = (root / "AGENTS.md").read_text()
    project._init_codebase_omp(root, "/bin/cbm", instruction, plugin, lambda p: True)
    assert (root / ".omp" / "mcp.json").read_text() == mcp_before
    assert (root / ".omp" / "extensions" / "CodebaseMemoryReminder.ts").read_text() == ext_before
    assert (root / "AGENTS.md").read_text() == agents_before


def _R(code, stdout=""):
    return type("R", (), {"returncode": code, "stdout": stdout, "stderr": ""})()


def _index_subprocess(status_code, index_code):
    """Fake subprocess.run branching on index_status vs index_repository."""
    def run(cmd, **kw):
        code = index_code if "index_repository" in " ".join(cmd) else status_code
        return _R(code)
    return run


def test_initial_index_skips_when_indexed(tmp_path, monkeypatch, capsys):
    root = tmp_path / "proj"
    root.mkdir()
    calls = []
    monkeypatch.setattr(project.subprocess, "run", lambda cmd, **kw: calls.append(" ".join(cmd)) or _R(0))
    project._initial_index(root, "/bin/cbm")
    assert not any("index_repository" in c for c in calls)
    assert "already indexed" in capsys.readouterr().out


def test_initial_index_indexes_when_not_indexed(tmp_path, monkeypatch, capsys):
    root = tmp_path / "proj"
    root.mkdir()
    calls = []
    monkeypatch.setattr(
        project.subprocess, "run",
        lambda cmd, **kw: calls.append(" ".join(cmd)) or _index_subprocess(1, 0)(cmd, **kw),
    )
    project._initial_index(root, "/bin/cbm")
    index_calls = [c for c in calls if "index_repository" in c]
    assert index_calls
    assert "--mode full" in index_calls[0]
    status_calls = [c for c in calls if "index_status" in c]
    assert status_calls
    assert str(root.resolve()).lstrip("/").replace("/", "-") in status_calls[0]
    assert "indexed" in capsys.readouterr().out


def test_initial_index_warns_on_failure(tmp_path, monkeypatch, capsys):
    root = tmp_path / "proj"
    root.mkdir()
    monkeypatch.setattr(project.subprocess, "run", _index_subprocess(1, 1))
    project._initial_index(root, "/bin/cbm")  # must not raise
    assert "warning" in capsys.readouterr().out


def _fake_init_run(root, indexed):
    """Fake subprocess.run for init_project: handle git_root + index_status."""
    def run(cmd, **kw):
        argv = " ".join(cmd)
        if "rev-parse" in argv:
            return _R(0, str(root))
        return _R(0 if indexed else 1)
    return run


def test_init_project_indexes_shared_across_agents(tmp_path, monkeypatch):
    root = tmp_path / "proj"
    root.mkdir()
    git("init", cwd=root)
    calls = []
    monkeypatch.setattr(project, "_ensure_tool", lambda *a, **k: "/bin/cbm")
    monkeypatch.setattr(project, "_init_openspec", lambda *a, **k: None)
    monkeypatch.setattr(project, "_init_codebase", lambda *a, **k: None)
    monkeypatch.setattr(project, "_init_codebase_omp", lambda *a, **k: None)
    monkeypatch.setattr(
        project.subprocess, "run",
        lambda cmd, **kw: calls.append(" ".join(cmd)) or _fake_init_run(root, False)(cmd, **kw),
    )
    project.init_project(root, lambda p: True, tmp_path / "i.md", tmp_path / "oc.ts", tmp_path / "omp.ts", "opencode")
    project.init_project(root, lambda p: True, tmp_path / "i.md", tmp_path / "oc.ts", tmp_path / "omp.ts", "omp")
    assert sum(1 for c in calls if "index_status" in c) == 2  # reached for both agents


def test_init_project_idempotent_skips_index(tmp_path, monkeypatch):
    root = tmp_path / "proj"
    root.mkdir()
    git("init", cwd=root)
    calls = []
    monkeypatch.setattr(project, "_ensure_tool", lambda *a, **k: "/bin/cbm")
    monkeypatch.setattr(project, "_init_openspec", lambda *a, **k: None)
    monkeypatch.setattr(project, "_init_codebase", lambda *a, **k: None)
    monkeypatch.setattr(project, "_init_codebase_omp", lambda *a, **k: None)
    monkeypatch.setattr(
        project.subprocess, "run",
        lambda cmd, **kw: calls.append(" ".join(cmd)) or _fake_init_run(root, True)(cmd, **kw),
    )
    project.init_project(root, lambda p: True, tmp_path / "i.md", tmp_path / "oc.ts", tmp_path / "omp.ts", "opencode")
    assert not any("index_repository" in c for c in calls)


def test_ensure_tool_prompts_with_command_and_skips_on_decline(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))  # ensure the bin is "not installed"
    calls = []
    confirm = lambda prompt: calls.append(prompt) or False  # noqa: E731 decline
    result = project._ensure_tool("FakeTool", "fake-bin-xyz", "echo install it", confirm)
    assert result is None
    assert calls, "must ask before installing"
    # the exact install command is shown so the user knows what will run
    assert "echo install it" in calls[0]


# ------------------------------------------------------------- multi-agent
def test_detect_agents_both(monkeypatch):
    monkeypatch.setattr(
        shutil, "which",
        lambda name: f"/usr/bin/{name}" if name in ("opencode", "omp") else None,
    )
    assert config.detect_agents() == ["opencode", "omp"]


def test_detect_agents_none(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    assert config.detect_agents() == []


def test_config_dir_omp_fallback(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    assert config.config_dir("omp", {}) == Path.home() / ".omp" / "agent"


def test_config_dir_unknown_agent():
    with pytest.raises(ValueError):
        config.config_dir("nope", {})


def test_select_agents_force_flag(monkeypatch):
    monkeypatch.setattr(
        shutil, "which",
        lambda name: f"/x/{name}" if name in ("opencode", "omp") else None,
    )
    assert kit.select_agents("omp") == "omp"


def test_select_agents_single_detected(monkeypatch):
    monkeypatch.setattr(
        shutil, "which", lambda name: "/x/opencode" if name == "opencode" else None
    )
    assert kit.select_agents(None) == "opencode"


def test_select_agents_none_detected(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    assert kit.select_agents(None) is None


def test_select_agents_multiple_prompts(monkeypatch):
    monkeypatch.setattr(
        shutil, "which",
        lambda name: f"/x/{name}" if name in ("opencode", "omp") else None,
    )
    # explicit single choice
    monkeypatch.setattr("builtins.input", lambda prompt: "1")
    assert kit.select_agents(None) == "opencode"
    monkeypatch.setattr("builtins.input", lambda prompt: "2")
    assert kit.select_agents(None) == "omp"


def test_select_agents_prompt_rejects_invalid(monkeypatch):
    monkeypatch.setattr(
        shutil, "which",
        lambda name: f"/x/{name}" if name in ("opencode", "omp") else None,
    )
    replies = iter(["abc", "9", "1"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(replies))
    assert kit.select_agents(None) == "opencode"


def test_select_agents_prompt_uses_command_verb(monkeypatch):
    # The multi-agent prompt must name the operation being run, so `uninstall`
    # asks "Uninstall for which?" rather than the install-specific text.
    monkeypatch.setattr(
        shutil, "which",
        lambda name: f"/x/{name}" if name in ("opencode", "omp") else None,
    )
    prompts = []
    monkeypatch.setattr("builtins.input", lambda prompt: prompts.append(prompt) or "1")
    kit.select_agents(None, command="uninstall")
    assert any("Uninstall for which?" in p for p in prompts)
    prompts.clear()
    kit.select_agents(None, command="install")
    assert any("Install for which?" in p for p in prompts)


def test_install_scopes_artifacts_by_agent(tmp_path, monkeypatch):
    monkeypatch.setenv("OC_CONFIG_DIR", str(tmp_path / "oc"))
    oc_dir = config.config_dir("opencode", {})
    omp_dir = tmp_path / "omp"
    root = tmp_path / "root"
    src = root / "src" / "commands" / "cmd.md"
    src.parent.mkdir(parents=True)
    src.write_text("shared\n")
    oc_src = root / "src" / "themes" / "t.json"
    oc_src.parent.mkdir(parents=True)
    oc_src.write_text('{"a": 1}\n')

    manifest = {
        "version": 2,
        "artifacts": [
            {"name": "shared", "operation": "symlink", "provenance": "original",
             "agents": ["opencode", "omp"], "src": "src/commands/cmd.md",
             "target": "commands/cmd.md"},
            {"name": "oconly", "operation": "symlink", "provenance": "original",
             "agents": ["opencode"], "src": "src/themes/t.json",
             "target": "themes/t.json"},
        ],
    }
    operations.install(manifest, root, oc_dir)
    operations.install(manifest, root, omp_dir, agent="omp")

    # shared installed into both
    assert (oc_dir / "commands" / "cmd.md").is_symlink()
    assert (omp_dir / "commands" / "cmd.md").is_symlink()
    # opencode-only theme in opencode dir but NOT omp dir
    assert (oc_dir / "themes" / "t.json").is_symlink()
    assert not (omp_dir / "themes" / "t.json").exists()


def test_validate_requires_agents():
    data = {
        "version": 2,
        "artifacts": [{
            "name": "x", "operation": "symlink", "provenance": "original",
            "src": "a", "target": "b",
        }],
    }
    with pytest.raises(manifest.ManifestError):
        manifest.validate(data)


def test_validate_rejects_unknown_agent():
    data = {
        "version": 2,
        "artifacts": [{
            "name": "x", "operation": "symlink", "provenance": "original",
            "agents": ["claude"], "src": "a", "target": "b",
        }],
    }
    with pytest.raises(manifest.ManifestError):
        manifest.validate(data)


def test_validate_rejects_version_1():
    data = {
        "version": 1,
        "artifacts": [{
            "name": "x", "operation": "symlink", "provenance": "original",
            "agents": ["opencode"], "src": "a", "target": "b",
        }],
    }
    with pytest.raises(manifest.ManifestError):
        manifest.validate(data)


def test_vendor_accepts_agent_flag():
    # --agent is accepted for symmetry but vendor ignores it (no config-dir work).
    args = kit.build_parser().parse_args(["vendor", "--agent", "opencode"])
    assert args.command == "vendor"
    assert args.agent == "opencode"
    args2 = kit.build_parser().parse_args(["vendor", "--agent", "omp"])
    assert args2.agent == "omp"


# ----------------------------------------------------------- shell rc bootstrap
def test_rc_path_mapping():
    assert shell_rc.rc_path("zsh") == Path.home() / ".zshrc"
    assert shell_rc.rc_path("bash") == Path.home() / ".bashrc"
    assert shell_rc.rc_path("fish") == Path.home() / ".config" / "fish" / "config.fish"
    assert shell_rc.rc_path("tcsh") is None
    assert shell_rc.rc_path(None) is None
    assert shell_rc.rc_path("") is None


def test_login_shell_unknown(monkeypatch):
    monkeypatch.delenv("SHELL", raising=False)
    assert shell_rc.login_shell() is None
    monkeypatch.setenv("SHELL", "/bin/tcsh")
    assert shell_rc.login_shell() is None
    monkeypatch.setenv("SHELL", "/bin/zsh")
    assert shell_rc.login_shell() == "zsh"


def test_bootstrap_block_fish():
    b = shell_rc.bootstrap_block(Path("/kit/bin/setup"), "fish")
    assert "function my-ai-code-kit" in b
    assert "/kit/bin/setup $argv" in b


def test_bootstrap_block_posix():
    b = shell_rc.bootstrap_block(Path("/kit/bin/setup"), "zsh")
    assert 'my-ai-code-kit() { /kit/bin/setup "$@"; }' in b


def test_add_block_idempotent(tmp_path):
    rc = tmp_path / ".zshrc"
    block = shell_rc.bootstrap_block(Path("/kit/bin/setup"), "zsh")
    assert shell_rc.add_block(rc, block) is True
    assert shell_rc.add_block(rc, block) is False
    assert rc.read_text().count("my-ai-code-kit begin") == 1


def test_remove_block(tmp_path):
    rc = tmp_path / ".zshrc"
    rc.write_text("export FOO=1\n")
    block = shell_rc.bootstrap_block(Path("/kit/bin/setup"), "zsh")
    shell_rc.add_block(rc, block)
    assert shell_rc.remove_block(rc) is True
    assert shell_rc.remove_block(rc) is False
    text = rc.read_text()
    assert "my-ai-code-kit" not in text
    assert "export FOO=1" in text


def test_bootstrap_prompt_decline_writes_nothing(tmp_path, monkeypatch, capsys):
    rc = tmp_path / ".zshrc"
    monkeypatch.setattr(shell_rc, "login_shell", lambda: "zsh")
    monkeypatch.setattr(shell_rc, "rc_path", lambda shell: rc)
    monkeypatch.setattr(kit, "_confirm", lambda prompt, assume_yes=False: False)
    kit._bootstrap_shell_command()
    assert not rc.exists()
    assert "skipped" in capsys.readouterr().out


def test_bootstrap_accept_writes_block(tmp_path, monkeypatch, capsys):
    rc = tmp_path / ".zshrc"
    monkeypatch.setattr(shell_rc, "login_shell", lambda: "zsh")
    monkeypatch.setattr(shell_rc, "rc_path", lambda shell: rc)
    monkeypatch.setattr(kit, "_confirm", lambda prompt, assume_yes=False: True)
    kit._bootstrap_shell_command()
    assert "my-ai-code-kit()" in rc.read_text()
    assert "registered" in capsys.readouterr().out


def test_bootstrap_runs_even_with_yes(tmp_path, monkeypatch):
    # The rc bootstrap is a persistent user-controlled change: it is never
    # bypassed by --yes, so install invokes it regardless of assume_yes.
    calls = []
    monkeypatch.setattr(kit.operations, "sync", lambda *a, **k: None)
    monkeypatch.setattr(kit.project, "init_project", lambda *a, **k: None)
    monkeypatch.setattr(kit, "_bootstrap_shell_command", lambda: calls.append(1))
    kit._run_install(
        manifest.load(MANIFEST), tmp_path, force=True, assume_yes=True,
        skip_init=False, agent="opencode",
    )
    assert calls == [1]
