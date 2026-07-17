"""Black-box lifecycle scenarios L2–L5 from tests/blackbox/test_plan.md."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.blackbox


def test_l2_untrack_preserves_home_file(sandbox_factory):
    """L2: untrack removes from filelist; home file preserved; mirror kept."""
    sb = sandbox_factory()
    sb.init_repo(".profile:common\n")
    sb.write_home(".profile", "profile content\n")
    assert sb.save_no_push("common").returncode == 0

    mirror = sb.mirror_path("common", ".profile")
    assert mirror.exists()

    result = sb.run_dotsync("untrack", ".profile")
    assert result.returncode == 0, result.combined

    filelist = (sb.repo / "filelist").read_text()
    assert ".profile" not in filelist

    list_result = sb.run_dotsync("list", "common")
    assert list_result.returncode == 0
    assert ".profile" not in list_result.stdout

    profile = sb.home / ".profile"
    assert profile.is_file()
    assert profile.read_text() == "profile content\n"
    assert mirror.exists()


def test_l3_untrack_purge_repo_deletes_mirror(sandbox_factory):
    """L3: untrack --purge-repo deletes mirror; home file preserved."""
    sb = sandbox_factory()
    sb.init_repo(".profile:common\n")
    sb.write_home(".profile", "profile content\n")
    assert sb.save_no_push("common").returncode == 0

    mirror = sb.mirror_path("common", ".profile")
    assert mirror.exists()

    result = sb.run_dotsync("untrack", "--purge-repo", ".profile")
    assert result.returncode == 0, result.combined

    assert ".profile" not in (sb.repo / "filelist").read_text()
    assert not mirror.exists()

    profile = sb.home / ".profile"
    assert profile.is_file()
    assert profile.read_text() == "profile content\n"


def test_l4_track_bootstraps_dotfiles(sandbox_factory):
    """L4: track bootstraps ~/.dotfiles when repo missing (DOTSYNC_REPO unset)."""
    sb = sandbox_factory()
    sb.write_home(".gitconfig", "[user]\n\tname = Test\n")

    default_repo = sb.home / ".dotfiles"
    assert not default_repo.exists()

    result = sb.run_dotsync("track", ".gitconfig", "tools", unset_repo=True)
    assert result.returncode == 0, result.combined

    assert (default_repo / ".git").is_dir()
    assert ".gitconfig" in (default_repo / "filelist").read_text()

    gitconfig = sb.home / ".gitconfig"
    assert gitconfig.is_file() and not gitconfig.is_symlink()
    assert gitconfig.read_text() == "[user]\n\tname = Test\n"


def test_l5_track_auto_update_creates_mirror_immediately(sandbox_factory):
    """L5: default track mirrors file before explicit save."""
    sb = sandbox_factory()
    sb.write_home(".zshrc", "export ZSH=1\n")

    result = sb.run_dotsync("track", ".zshrc", "shell")
    assert result.returncode == 0, result.combined

    mirror = sb.mirror_path("shell", ".zshrc")
    assert mirror.exists()
    assert mirror.read_text() == "export ZSH=1\n"

    zshrc = sb.home / ".zshrc"
    assert zshrc.is_file() and not zshrc.is_symlink()


def test_l5_track_no_auto_update_defers_mirror_until_save(sandbox_factory):
    """L5 variant: --no-auto-update skips mirror until save."""
    sb = sandbox_factory()
    sb.write_home(".zshrc", "export ZSH=1\n")

    result = sb.run_dotsync("track", "--no-auto-update", ".zshrc", "shell")
    assert result.returncode == 0, result.combined

    assert ".zshrc" in (sb.repo / "filelist").read_text()
    mirror = sb.mirror_path("shell", ".zshrc")
    assert not mirror.exists()

    assert sb.save_no_push("shell").returncode == 0
    assert mirror.exists()
    assert mirror.read_text() == "export ZSH=1\n"
