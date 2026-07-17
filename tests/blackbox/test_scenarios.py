"""Black-box P0 scenarios from tests/blackbox/test_plan.md."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.blackbox.conftest import setup_diverged_repo, setup_repo_behind_remote

pytestmark = pytest.mark.blackbox


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


def test_l1_full_lifecycle_track_save_restore(sandbox_factory):
    """L1: track → save (push) → restore on fresh HOME."""
    sb = sandbox_factory(with_bare=True, with_home2=True)
    sb.write_home(".zshrc", "export ZSH=1\n")
    sb.write_home(".vimrc", "set number\n")

    assert sb.run_dotsync("track", ".zshrc", "shell").returncode == 0
    assert sb.run_dotsync("track", ".vimrc", "editor").returncode == 0
    assert (sb.repo / ".git").is_dir()
    filelist = (sb.repo / "filelist").read_text()
    assert ".zshrc" in filelist
    assert ".vimrc" in filelist

    sb.add_origin()
    result = sb.run_dotsync("save", "-m", "initial dotfiles")
    assert result.returncode == 0, result.combined
    assert sb.git_cmd("log", "-1", cwd=sb.repo).returncode == 0
    assert sb.ls_remote_head()

    assert sb.mirror_path("shell", ".zshrc").read_text() == "export ZSH=1\n"
    assert sb.mirror_path("editor", ".vimrc").read_text() == "set number\n"

    post_save_sha = sb.head_sha()

    # Fresh machine restore.
    home2 = sb.home2
    home2_repo = home2 / ".dotfiles"
    result = sb.run_dotsync(
        "restore",
        "--remote", sb.bare_url(),
        "--categories", "shell,editor",
        "--yes",
        "--conflict", "overwrite",
        cwd=home2,
        home=home2,
        repo=home2_repo,
    )
    assert result.returncode == 0, result.combined
    assert (home2 / ".zshrc").read_text() == "export ZSH=1\n"
    assert (home2 / ".vimrc").read_text() == "set number\n"
    assert not sb.symlinks_pointing_into_repo(home2)
    assert home2_repo.is_dir()
    assert sb.head_sha(cwd=home2_repo) == post_save_sha


# ---------------------------------------------------------------------------
# Mirror-only
# ---------------------------------------------------------------------------


def test_m1_home_never_becomes_repo_symlink(sandbox_factory):
    """M1: After save + restore, home files stay regular files (SC1)."""
    sb = sandbox_factory()
    sb.init_repo(".bashrc:shell\n")
    sb.write_home(".bashrc", "shell config v1\n")

    assert sb.save_no_push("shell").returncode == 0
    bashrc = sb.home / ".bashrc"
    assert bashrc.is_file() and not bashrc.is_symlink()

    assert sb.restore("shell", skip_pull=True, conflict="overwrite").returncode == 0
    assert bashrc.is_file() and not bashrc.is_symlink()
    assert bashrc.read_text() == sb.mirror_path("shell", ".bashrc").read_text()
    assert not sb.symlinks_pointing_into_repo()


# ---------------------------------------------------------------------------
# Restore pull
# ---------------------------------------------------------------------------


def test_rp1_pull_runs_before_home_copy(sandbox_factory):
    """RP1: restore pulls remote HEAD before copying to home (SC7)."""
    sb = sandbox_factory(with_bare=True)
    remote_sha = setup_repo_behind_remote(
        sb, ".file:common\n", "remote-version\n",
    )
    assert not (sb.home / ".file").exists()

    result = sb.restore("common", conflict="overwrite")
    assert result.returncode == 0, result.combined
    assert f"Restoring from commit {remote_sha}" in result.stdout
    assert (sb.home / ".file").read_text() == "remote-version\n"


def test_rp2_diverged_repo_aborts_restore(sandbox_factory):
    """RP2: diverged local/remote aborts with no home writes (SC7)."""
    sb = sandbox_factory(with_bare=True)
    setup_diverged_repo(sb, ".file:common\n")
    assert not (sb.home / ".file").exists()

    result = sb.restore("common", conflict="overwrite")
    assert result.returncode != 0
    assert "Failed to pull latest changes" in result.combined
    assert not (sb.home / ".file").exists()


# ---------------------------------------------------------------------------
# Conflicts
# ---------------------------------------------------------------------------


def test_c1_unified_diff_cancel_aborts_entire_restore(sandbox_factory):
    """C1: diff shown; cancel aborts entire restore (SC6)."""
    sb = sandbox_factory()
    sb.init_repo(".file1:common\n.file2:common\n")
    sb.write_home(".file1", "repo-one\n")
    sb.write_home(".file2", "repo-two\n")
    assert sb.save_no_push("common").returncode == 0

    sb.write_home(".file1", "home-one\n")
    sb.write_home(".file2", "home-two\n")

    result = sb.run_dotsync("restore", "common", stdin="c\n")
    assert result.returncode != 0
    assert "---" in result.stdout or "-home-one" in result.stdout
    assert (sb.home / ".file1").read_text() == "home-one\n"
    assert (sb.home / ".file2").read_text() == "home-two\n"


# ---------------------------------------------------------------------------
# Trees
# ---------------------------------------------------------------------------


def test_t1_new_tree_file_picked_up_on_second_save(sandbox_factory):
    """T1: new file under @tree picked up on second save (SC5)."""
    sb = sandbox_factory()
    sb.init_repo("@tree:.config/myapp:editor\n")
    app = sb.home / ".config" / "myapp"
    app.mkdir(parents=True)
    (app / "settings.json").write_text('{"v":1}')

    assert sb.save_no_push("editor").returncode == 0
    (app / "plugins.json").write_text('{"v":1,"new":true}')
    result = sb.save_no_push("editor")
    assert result.returncode == 0

    plugins_mirror = sb.mirror_path("editor", ".config/myapp/plugins.json")
    assert plugins_mirror.exists()
    assert plugins_mirror.read_text() == '{"v":1,"new":true}'
    log = sb.git_cmd("log", "-1", "--name-only", cwd=sb.repo).stdout
    assert "plugins.json" in log


# ---------------------------------------------------------------------------
# Symlinks
# ---------------------------------------------------------------------------


def test_s1_internal_symlink_materialized(sandbox_factory):
    """S1: internal symlink materialized with manifest sidecar (SC3)."""
    sb = sandbox_factory()
    sb.init_repo("@tree:.config/app:editor\n")
    app = sb.home / ".config" / "app"
    app.mkdir(parents=True)
    (app / "real.txt").write_text("hello")
    os.symlink("real.txt", app / "link.txt")

    assert sb.save_no_push("editor").returncode == 0

    canonical = sb.mirror_path("editor", ".config/app/real.txt")
    assert canonical.read_text() == "hello"
    assert not (sb.mirror_path("editor", ".config/app/link.txt")).exists()

    manifest_path = sb.repo / ".dotsync" / "manifests" / "editor.json"
    manifest = json.loads(manifest_path.read_text())
    assert len(manifest) == 1
    entry = manifest[0]
    assert entry["home_path"] == ".config/app/link.txt"
    assert entry["kind"] == "symlink"
    assert entry["target"] == "real.txt"


def test_s6_external_symlink_save_restore_roundtrip(sandbox_factory):
    """S6: external symlink save→restore round-trip (SC3)."""
    sb = sandbox_factory()
    external = sb.root / "external"
    external.mkdir()
    (external / "secret.cfg").write_text("external-data")

    sb.init_repo("@tree:.config/app:tools\n")
    app = sb.home / ".config" / "app"
    app.mkdir(parents=True)
    os.symlink(str(external / "secret.cfg"), app / "link.cfg")

    assert sb.save_no_push("tools").returncode == 0

    materialized_dir = sb.repo / ".dotsync" / "materialized"
    assert materialized_dir.exists()
    materialized_files = [p for p in materialized_dir.rglob("*") if p.is_file()]
    assert any(p.read_text() == "external-data" for p in materialized_files)

    shutil.rmtree(app)
    result = sb.restore("tools", skip_pull=True, conflict="overwrite")
    link_cfg = sb.home / ".config" / "app" / "link.cfg"

    assert result.returncode == 0, result.combined
    assert link_cfg.exists()
    assert link_cfg.read_text() == "external-data"
    assert not link_cfg.is_symlink()


# ---------------------------------------------------------------------------
# Boundaries
# ---------------------------------------------------------------------------


def test_b6_non_interactive_save_without_remote_does_not_hang(sandbox_factory):
    """B6: save --non-interactive without origin must exit non-zero quickly (SC2)."""
    sb = sandbox_factory()
    sb.init_repo(".bashrc:shell\n")
    sb.write_home(".bashrc", "shell\n")

    result = sb.run_dotsync("save", "--non-interactive", "shell", timeout=30)
    assert result.returncode != 0
    assert "successfully pushed" not in result.combined.lower()


# ---------------------------------------------------------------------------
# Encrypt (optional — requires gpg)
# ---------------------------------------------------------------------------


def _gpg_available() -> bool:
    try:
        subprocess.run(["gpg", "--version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def _encrypt_writes_only_under_repo_plugins(sb) -> bool:
    plugins_root = sb.repo / ".plugins"
    allowed = plugins_root.resolve()
    for path in plugins_root.rglob("*"):
        if path.is_file():
            try:
                path.resolve().relative_to(allowed)
            except ValueError:
                return False
    return True


@pytest.mark.skipif(
    not _gpg_available(),
    reason="gpg not available",
)
@pytest.mark.skip(
    reason="encrypt passwd uses getpass (TTY); not automatable via subprocess stdin alone",
)
def test_e1_encrypt_track_save_restore_roundtrip(sandbox_factory):
    """E1: track --encrypt → save → restore round-trip (SC3)."""
    sb = sandbox_factory()
    sb.init_repo("")
    sb.write_home(".secret", "plaintext secret\n")

    passwd_in = "testpass123\ntestpass123\n"
    result = sb.run_dotsync("passwd", stdin=passwd_in)
    assert result.returncode == 0, result.combined
    assert _encrypt_writes_only_under_repo_plugins(sb)

    assert sb.run_dotsync("track", "--encrypt", ".secret", "private").returncode == 0
    assert sb.save_no_push("private").returncode == 0

    encrypted = sb.repo / "dotfiles" / "encrypt" / "private" / ".secret"
    assert encrypted.exists()
    assert encrypted.read_text() != "plaintext secret\n"

    (sb.home / ".secret").unlink()
    restore_in = "testpass123\n"
    result = sb.restore("private", skip_pull=True, conflict="overwrite", stdin=restore_in)
    assert result.returncode == 0, result.combined

    restored = sb.home / ".secret"
    assert restored.exists()
    assert not restored.is_symlink()
    assert restored.read_text() == "plaintext secret\n"
