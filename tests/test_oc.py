"""Tests for the my-opencode-setup python tooling."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

import occonfig  # noqa: E402
import ocinit  # noqa: E402
import ocmanifest  # noqa: E402
import ocmerge  # noqa: E402
import ocops  # noqa: E402

MANIFEST = REPO / "manifest.toml"


def git(*args, cwd=None):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def git_out(*args, cwd=None) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


# ------------------------------------------------------------------ manifest
def test_manifest_loads_and_validates():
    m = ocmanifest.load(MANIFEST)
    names = ocmanifest.artifact_names(m)
    assert "grill-me" in names
    assert "caveman" in names
    assert "glab" in names


def test_manifest_three_provenances_present():
    m = ocmanifest.load(MANIFEST)
    provs = {a["provenance"] for a in m["artifacts"]}
    assert provs == {"original", "vendor", "fork"}


def test_set_sha_edits_correct_artifact(tmp_path):
    src = tmp_path / "m.toml"
    src.write_text(
        'version = 1\n'
        '[[artifacts]]\nname = "a"\noperation = "symlink"\n'
        'provenance = "original"\nsrc = "a"\ntarget = "a"\nsource_sha = ""\n'
        '[[artifacts]]\nname = "b"\noperation = "symlink"\n'
        'provenance = "original"\nsrc = "b"\ntarget = "b"\nsource_sha = ""\n'
    )
    ocmanifest.set_sha(src, "b", "abc123")
    m = ocmanifest.load(src)
    assert m["artifacts"][0]["source_sha"] == ""
    assert m["artifacts"][1]["source_sha"] == "abc123"


# ------------------------------------------------------------- config dir
def test_config_dir_env_override(monkeypatch):
    monkeypatch.setenv("OC_CONFIG_DIR", "/tmp/fake")
    assert occonfig.config_dir({}) == Path("/tmp/fake")


def test_config_dir_manifest_default(monkeypatch):
    monkeypatch.delenv("OC_CONFIG_DIR", raising=False)
    m = {"config": {"default_config_dir": "~/x"}}
    assert occonfig.config_dir(m) == Path.home() / "x"


# ---------------------------------------------------------------- install
def test_install_symlinks_text_and_config(tmp_path, monkeypatch):
    monkeypatch.setenv("OC_CONFIG_DIR", str(tmp_path / "cfg"))
    cfg = occonfig.config_dir({})
    ocops.install(ocmanifest.load(MANIFEST), REPO, cfg)

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
    assert tui["theme"] == "github-dark-default"
    # codebase-memory-mcp is per-project now (see ocinit), not global config.
    assert not (cfg / "opencode.json").exists()


def test_install_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("OC_CONFIG_DIR", str(tmp_path / "cfg"))
    cfg = occonfig.config_dir({})
    m = ocmanifest.load(MANIFEST)
    ocops.install(m, REPO, cfg)
    agents_before = (cfg / "AGENTS.md").read_text()
    ocops.install(m, REPO, cfg)
    assert (cfg / "AGENTS.md").read_text() == agents_before
    assert (cfg / "AGENTS.md").read_text().count("caveman-begin") == 1


def test_uninstall_removes_text_blocks(tmp_path, monkeypatch):
    monkeypatch.setenv("OC_CONFIG_DIR", str(tmp_path / "cfg"))
    cfg = occonfig.config_dir({})
    m = ocmanifest.load(MANIFEST)
    ocops.install(m, REPO, cfg)

    # a user-edited block is kept, a pristine one is removed
    agents = cfg / "AGENTS.md"
    agents.write_text(
        agents.read_text().replace(
            "Respond terse like smart caveman.", "RESPOND VERY VERBOSELY."
        )
    )

    ocops.uninstall(m, REPO, cfg)
    final = agents.read_text()
    assert "caveman-begin" in final  # edited block kept
    assert "file-edit-size-limits:start" not in final  # pristine block removed


# -------------------------------------------------------------------- sync
def test_sync_removes_stale_keeps_user_file(tmp_path, monkeypatch):
    monkeypatch.setenv("OC_CONFIG_DIR", str(tmp_path / "cfg"))
    cfg = occonfig.config_dir({})
    m = ocmanifest.load(MANIFEST)
    ocops.install(m, REPO, cfg)

    stale = cfg / "commands" / "stale-ghost.md"
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.symlink_to(REPO / "src" / "commands" / "fix.md")

    user = cfg / "commands" / "my-own.md"
    user.write_text("user file")

    ocops.sync(m, REPO, cfg)
    assert not stale.exists()
    assert user.exists()


def test_sync_prune_false_keeps_stale(tmp_path, monkeypatch):
    monkeypatch.setenv("OC_CONFIG_DIR", str(tmp_path / "cfg"))
    cfg = occonfig.config_dir({})
    m = ocmanifest.load(MANIFEST)
    ocops.install(m, REPO, cfg)

    stale = cfg / "commands" / "stale-ghost.md"
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.symlink_to(REPO / "src" / "commands" / "fix.md")

    ocops.sync(m, REPO, cfg, prune=False)
    assert stale.exists()  # stale symlink left in place when pruning disabled


# ---------------------------------------------------------------- uninstall
def test_uninstall_removes_managed_only(tmp_path, monkeypatch):
    monkeypatch.setenv("OC_CONFIG_DIR", str(tmp_path / "cfg"))
    cfg = occonfig.config_dir({})
    m = ocmanifest.load(MANIFEST)
    ocops.install(m, REPO, cfg)
    user = cfg / "commands" / "my-own.md"
    user.write_text("keep me")
    ocops.uninstall(m, REPO, cfg)
    assert user.exists()
    assert not (cfg / "commands" / "commit-message.md").exists()


def test_uninstall_removes_legacy_copy_of_plain_symlink(tmp_path, monkeypatch):
    # A plain symlink artifact installed as a real file copy by an earlier
    # tool (not a symlink) is a managed leftover: uninstall removes it when it
    # matches the source exactly, but keeps a user-edited file at the same
    # kind of target.
    monkeypatch.setenv("OC_CONFIG_DIR", str(tmp_path / "cfg"))
    cfg = occonfig.config_dir({})
    root = tmp_path / "root"

    src = root / "src" / "scripts" / "verify.sh"
    src.parent.mkdir(parents=True)
    src.write_text("#!/bin/sh\nmanaged\n")
    managed = {"name": "managed", "operation": "symlink",
               "src": "src/scripts/verify.sh", "target": "scripts/verify.sh"}

    edited_src = root / "src" / "themes" / "theme.json"
    edited_src.parent.mkdir(parents=True)
    edited_src.write_text('{"name": "managed"}\n')
    edited = {"name": "edited", "operation": "symlink",
              "src": "src/themes/theme.json", "target": "themes/theme.json"}

    manifest = {"version": 1, "artifacts": [managed, edited]}

    # Installed as real files (copies), not symlinks.
    target = cfg / "scripts" / "verify.sh"
    target.parent.mkdir(parents=True)
    target.write_text(src.read_text())
    edited_target = cfg / "themes" / "theme.json"
    edited_target.parent.mkdir(parents=True)
    edited_target.write_text('{"name": "USER EDITED"}\n')

    ocops.uninstall(manifest, root, cfg)
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
    conflict = ocmerge._merge_file(ours, base, theirs)
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
    conflict = ocmerge._merge_file(ours, base, theirs)
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
        f'version = 1\n[[artifacts]]\nname = "f"\noperation = "symlink"\n'
        f'provenance = "vendor"\nsource_repo = "{upstream}"\n'
        f'source_path = "f.md"\nsource_sha = "{sha1}"\n'
        f'src = "src/commands/f.md"\ntarget = "commands/f.md"\n'
    )
    art = ocmanifest.find(ocmanifest.load(mp), "f")

    monkeypatch.setattr(
        ocmerge, "_fetch_raw",
        lambda repo, spath, ref, dest: _local_fetch(Path(repo), spath, ref, Path(dest)),
    )
    assert ocmerge.update_artifact(mp, root, art) == 0
    assert src.read_text().strip() == "v2"
    assert ocmanifest.load(mp)["artifacts"][0]["source_sha"] == head


def _local_fetch(repo: Path, spath: str, ref: str, dest: Path) -> bool:
    # Offline stand-in for ocmerge._fetch_raw: read the file straight from
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
        f'version = 1\n[[artifacts]]\nname = "f"\noperation = "symlink"\n'
        f'provenance = "fork"\nsource_repo = "{upstream}"\n'
        f'source_path = "f.md"\nsource_sha = ""\n'
        f'src = "src/commands/f.md"\ntarget = "commands/f.md"\n'
    )
    art = ocmanifest.find(ocmanifest.load(mp), "f")
    assert ocmerge.update_artifact(mp, root, art) == 0
    assert src.read_text() == "MY CUSTOM\n"  # untouched
    assert ocmanifest.load(mp)["artifacts"][0]["source_sha"] == head


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
        f'version = 1\n[[artifacts]]\nname = "f"\noperation = "symlink"\n'
        f'provenance = "fork"\nsource_repo = "{upstream}"\n'
        f'source_path = "f.md"\nsource_sha = "{sha1}"\n'
        f'src = "src/commands/f.md"\ntarget = "commands/f.md"\n'
    )
    art = ocmanifest.find(ocmanifest.load(mp), "f")
    monkeypatch.setattr(
        ocmerge, "_fetch_raw",
        lambda repo, spath, ref, dest: _local_fetch(Path(repo), spath, ref, Path(dest)),
    )
    assert ocmerge.update_artifact(mp, root, art) == 0
    result = src.read_text()
    assert "MY CUSTOMIZATION" in result
    assert "UPSTREAM footer" in result
    assert ocmanifest.load(mp)["artifacts"][0]["source_sha"] == head


# ------------------------------------------------------------ check / shims
def test_check_valid_source_path_reports_behind(tmp_path, monkeypatch):
    upstream = tmp_path / "upstream"
    head = _make_repo(upstream, {"f.md": "v1\n"})
    root = tmp_path / "root"
    root.mkdir()
    mp = tmp_path / "m.toml"
    mp.write_text(
        f'version = 1\n[[artifacts]]\nname = "f"\noperation = "symlink"\n'
        f'provenance = "vendor"\nsource_repo = "{upstream}"\n'
        f'source_path = "f.md"\nsource_sha = ""\n'
        f'src = "src/f.md"\ntarget = "f.md"\n'
    )
    art = ocmanifest.find(ocmanifest.load(mp), "f")
    monkeypatch.setattr(
        ocmerge, "_fetch_raw",
        lambda repo, spath, ref, dest: _local_fetch(Path(repo), spath, ref, Path(dest)),
    )
    assert ocmerge.update_artifact(mp, root, art, check_only=True) == ocmerge.DRIFT
    assert ocmanifest.load(mp)["artifacts"][0]["source_sha"] == ""  # no mutation


# ---------------------------------------------------------------- entrypoint
def test_oc_entrypoint_paths_resolve_to_repo():
    import oc  # noqa: PLC0415

    # Guards the CLI entrypoint against ROOT/MANIFEST regressions: an off-by-one
    # ROOT or a wrong manifest filename makes every subcommand fail.
    assert oc.ROOT == REPO
    assert oc.MANIFEST == REPO / "manifest.toml"
    assert oc.MANIFEST.exists()


def test_oc_cli_install_dispatch(tmp_path, monkeypatch):
    monkeypatch.setenv("OC_CONFIG_DIR", str(tmp_path / "cfg"))
    import oc  # noqa: PLC0415

    # --no-init: keep this test hermetic. Per-project init (OpenSpec,
    # codebase-memory-mcp) would mutate the real working tree and PATH tools.
    assert oc.main(["install", "--yes", "--no-init"]) == 0
    cfg = tmp_path / "cfg"
    assert (cfg / "AGENTS.md").exists()
    assert (cfg / "commands" / "commit-message.md").exists()


def test_oc_cli_missing_manifest_returns_error(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("OC_CONFIG_DIR", str(tmp_path / "cfg"))
    import oc  # noqa: PLC0415

    # A manifest we cannot find must fail cleanly (exit 2), not traceback.
    original = oc.MANIFEST
    oc.MANIFEST = tmp_path / "nope.toml"
    try:
        assert oc.main(["install", "--yes"]) == 2
    finally:
        oc.MANIFEST = original
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
        f'version = 1\n[[artifacts]]\nname = "x"\noperation = "symlink"\n'
        f'provenance = "vendor"\nsource_repo = "{upstream}"\n'
        f'source_path = "skills/x"\nsource_sha = ""\n'
        f'src = "src/skills/x"\ntarget = "skills/x"\n'
    )
    art = ocmanifest.find(ocmanifest.load(mp), "x")
    assert ocmerge.update_artifact(mp, root, art) == 0
    assert (src / "a.md").read_text().strip() == "a1"
    assert (src / "c.md").read_text().strip() == "c1"
    assert not (src / "b.md").exists()  # pruned
    assert ocmanifest.load(mp)["artifacts"][0]["source_sha"] == head


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
        f'version = 1\n[[artifacts]]\nname = "x"\noperation = "symlink"\n'
        f'provenance = "fork"\nsource_repo = "{upstream}"\n'
        f'source_path = "skills/x"\nsource_sha = "{sha1}"\n'
        f'src = "src/skills/x"\ntarget = "skills/x"\n'
    )
    art = ocmanifest.find(ocmanifest.load(mp), "x")
    assert ocmerge.update_artifact(mp, root, art) == 0
    result = (src / "f.md").read_text()
    assert "MY CUSTOM" in result
    assert "UPSTREAM footer" in result
    assert ocmanifest.load(mp)["artifacts"][0]["source_sha"] == head


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
        f'version = 1\n[[artifacts]]\nname = "f"\noperation = "symlink"\n'
        f'provenance = "fork"\nsource_repo = "{upstream}"\n'
        f'source_path = "f.md"\nsource_sha = "{sha1}"\n'
        f'src = "src/commands/f.md"\ntarget = "commands/f.md"\n'
    )
    art = ocmanifest.find(ocmanifest.load(mp), "f")
    # base fetch always fails — update must fail cleanly and leave local intact
    monkeypatch.setattr(ocmerge, "_fetch_raw", lambda repo, spath, ref, dest: False)
    assert ocmerge.update_artifact(mp, root, art) == ocmerge.ERROR
    assert src.read_text() == "MY CUSTOM\n"  # untouched
    assert ocmanifest.load(mp)["artifacts"][0]["source_sha"] == sha1  # not bumped


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
    cfg = occonfig.config_dir({})
    root = tmp_path / "root"
    src = root / "src" / "commands" / "cmd.md"
    src.parent.mkdir(parents=True)
    src.write_text("run <SCRIPT>\n")

    # old install left a plain symlink at the target
    target = cfg / "commands" / "cmd.md"
    target.parent.mkdir(parents=True)
    target.symlink_to(src)

    ocops.symlink(root, cfg, _replace_artifact())
    # repo source placeholder is intact (not clobbered through the symlink)
    assert "<SCRIPT>" in src.read_text()
    # target is now a substituted copy, not a symlink
    assert not target.is_symlink()
    assert f"{cfg}/scripts/run.sh" in target.read_text()


def test_replace_copy_honors_force(tmp_path, monkeypatch):
    monkeypatch.setenv("OC_CONFIG_DIR", str(tmp_path / "cfg"))
    cfg = occonfig.config_dir({})
    root = tmp_path / "root"
    src = root / "src" / "commands" / "cmd.md"
    src.parent.mkdir(parents=True)
    src.write_text("run <SCRIPT>\n")

    target = cfg / "commands" / "cmd.md"
    target.parent.mkdir(parents=True)
    target.write_text("USER FILE\n")

    ocops.symlink(root, cfg, _replace_artifact())
    assert target.read_text() == "USER FILE\n"  # kept without --force
    ocops.symlink(root, cfg, _replace_artifact(), force=True)
    assert f"{cfg}/scripts/run.sh" in target.read_text()  # overwritten


def test_replace_copy_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("OC_CONFIG_DIR", str(tmp_path / "cfg"))
    cfg = occonfig.config_dir({})
    root = tmp_path / "root"
    src = root / "src" / "commands" / "cmd.md"
    src.parent.mkdir(parents=True)
    src.write_text("run <SCRIPT>\n")

    ocops.symlink(root, cfg, _replace_artifact())
    content = (cfg / "commands" / "cmd.md").read_text()
    ocops.symlink(root, cfg, _replace_artifact())
    assert (cfg / "commands" / "cmd.md").read_text() == content  # unchanged


def test_uninstall_keeps_user_file_at_replace_target(tmp_path, monkeypatch):
    monkeypatch.setenv("OC_CONFIG_DIR", str(tmp_path / "cfg"))
    cfg = occonfig.config_dir({})
    root = tmp_path / "root"
    src = root / "src" / "commands" / "cmd.md"
    src.parent.mkdir(parents=True)
    src.write_text("run <SCRIPT>\n")

    artifact = _replace_artifact()
    manifest = {"version": 1, "artifacts": [artifact]}

    # a user's real file (content differs from the managed copy) is kept
    target = cfg / "commands" / "cmd.md"
    target.parent.mkdir(parents=True)
    target.write_text("USER EDITED CONTENT\n")
    ocops.uninstall(manifest, root, cfg)
    assert target.exists()

    # the managed copy is removed
    target.unlink()
    ocops.symlink(root, cfg, artifact)
    assert target.exists()
    ocops.uninstall(manifest, root, cfg)
    assert not target.exists()


# ---------------------------------------------------- config_merge guards
def test_config_merge_refuses_unparseable_config(tmp_path, monkeypatch):
    monkeypatch.setenv("OC_CONFIG_DIR", str(tmp_path / "cfg"))
    cfg = occonfig.config_dir({})
    target = cfg / "opencode.json"
    target.parent.mkdir(parents=True)
    target.write_text("{ not json !! }\n")
    artifact = {"config_file": "opencode.json", "config_path": "a.b",
                "value": '"x"'}
    before = target.read_text()
    with pytest.raises(ValueError):
        ocops.config_merge(tmp_path, cfg, artifact)
    assert target.read_text() == before  # untouched


def test_config_merge_refuses_non_object_config(tmp_path, monkeypatch):
    monkeypatch.setenv("OC_CONFIG_DIR", str(tmp_path / "cfg"))
    cfg = occonfig.config_dir({})
    target = cfg / "opencode.json"
    target.parent.mkdir(parents=True)
    target.write_text("[1, 2, 3]\n")
    artifact = {"config_file": "opencode.json", "config_path": "a.b",
                "value": '"x"'}
    with pytest.raises(ValueError):
        ocops.config_merge(tmp_path, cfg, artifact)


# ------------------------------------------------------------ validation
def test_validate_rejects_non_string_replace_value():
    data = {
        "version": 1,
        "artifacts": [{
            "name": "x", "operation": "symlink", "provenance": "original",
            "entries": [{"src": "a", "target": "b",
                         "replace": {"<X>": 123}}],
        }],
    }
    with pytest.raises(ocmanifest.ManifestError):
        ocmanifest.validate(data)


def test_validate_rejects_single_form_replace():
    data = {
        "version": 1,
        "artifacts": [{
            "name": "x", "operation": "symlink", "provenance": "original",
            "src": "a", "target": "b", "replace": {"<X>": "y"},
        }],
    }
    with pytest.raises(ocmanifest.ManifestError):
        ocmanifest.validate(data)


def test_validate_accepts_empty_string_config_value():
    data = {
        "version": 1,
        "artifacts": [{
            "name": "x", "operation": "config-merge", "provenance": "original",
            "config_file": "tui.json", "config_path": "theme", "value": "",
        }],
    }
    ocmanifest.validate(data)  # must not raise


def test_validate_rejects_non_string_config_value():
    data = {
        "version": 1,
        "artifacts": [{
            "name": "x", "operation": "config-merge", "provenance": "original",
            "config_file": "tui.json", "config_path": "theme", "value": 123,
        }],
    }
    with pytest.raises(ocmanifest.ManifestError):
        ocmanifest.validate(data)


# ------------------------------------------------------------------ ocinit
def test_git_root_resolves_toplevel_from_subdir(tmp_path):
    git("init", cwd=tmp_path)
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    assert ocinit.git_root(sub) == tmp_path.resolve()


def test_git_root_none_outside_repo(tmp_path):
    assert ocinit.git_root(tmp_path) is None


def test_prepend_instruction_is_idempotent(tmp_path):
    src = tmp_path / "instruction.md"
    src.write_text(
        "<!-- codebase-memory-mcp:start -->\n# block\n<!-- codebase-memory-mcp:end -->\n"
    )
    root = tmp_path / "proj"
    root.mkdir()
    (root / "AGENTS.md").write_text("existing\n")

    ocinit._prepend_instruction(root, src)
    first = (root / "AGENTS.md").read_text()
    assert first.startswith("<!-- codebase-memory-mcp:start -->")
    assert first.endswith("existing\n")

    ocinit._prepend_instruction(root, src)
    assert (root / "AGENTS.md").read_text() == first


def test_install_plugin(tmp_path):
    src = tmp_path / "CodebaseMemoryReminder.ts"
    src.write_text("// plugin")
    root = tmp_path / "proj"
    root.mkdir()
    ocinit._install_plugin(root, src)
    assert (root / ".opencode" / "plugins" / "CodebaseMemoryReminder.ts").read_text() == (
        "// plugin"
    )


def test_merge_mcp_config_idempotent_keeps_existing(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    ocinit._merge_mcp_config(root, "/bin/cbm")
    first = (root / ".opencode" / "opencode.json").read_text()
    assert json.loads(first)["mcp"]["codebase-memory-mcp"]["command"] == ["/bin/cbm"]

    ocinit._merge_mcp_config(root, "/bin/cbm")
    assert (root / ".opencode" / "opencode.json").read_text() == first


def test_merge_mcp_config_preserves_user_entry(tmp_path):
    root = tmp_path / "proj"
    (root / ".opencode").mkdir(parents=True)
    (root / ".opencode" / "opencode.json").write_text(
        json.dumps({"mcp": {"codebase-memory-mcp": {"command": ["/custom"]}}})
    )
    ocinit._merge_mcp_config(root, "/bin/cbm")
    data = json.loads((root / ".opencode" / "opencode.json").read_text())
    assert data["mcp"]["codebase-memory-mcp"]["command"] == ["/custom"]


def test_init_project_skips_outside_repo(tmp_path):
    # Not a git repo: init must no-op without invoking any tool.
    calls = []
    confirm = lambda prompt: calls.append(prompt) or True  # noqa: E731
    ocinit.init_project(tmp_path, confirm, tmp_path / "no.md", tmp_path / "no.ts")
    assert calls == []
    assert not (tmp_path / "AGENTS.md").exists()
    assert not (tmp_path / ".opencode").exists()


def test_ensure_tool_prompts_with_command_and_skips_on_decline(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))  # ensure the bin is "not installed"
    calls = []
    confirm = lambda prompt: calls.append(prompt) or False  # noqa: E731 decline
    result = ocinit._ensure_tool("FakeTool", "fake-bin-xyz", "echo install it", confirm)
    assert result is None
    assert calls, "must ask before installing"
    # the exact install command is shown so the user knows what will run
    assert "echo install it" in calls[0]
