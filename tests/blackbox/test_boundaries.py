"""Black-box boundary scenarios B1–B5 from tests/blackbox/test_plan.md."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.blackbox


def test_b1_empty_filelist_save_succeeds_with_no_file_ops(sandbox_factory):
    """B1: empty filelist save succeeds; no dotfiles/ artifacts created."""
    sb = sandbox_factory()
    sb.init_repo("# empty\n")

    result = sb.run_dotsync("save", "--no-push", "--non-interactive")
    assert result.returncode == 0, result.combined

    dotfiles = sb.repo / "dotfiles"
    assert not dotfiles.exists() or not any(dotfiles.rglob("*"))


def test_b2_decline_remote_url_aborts_save(sandbox_factory):
    """B2: empty stdin at remote URL prompt aborts save (SC2)."""
    sb = sandbox_factory()
    sb.init_repo(".file:common\n")
    sb.write_home(".file", "content\n")

    result = sb.run_dotsync("save", "common", stdin="\n")
    assert result.returncode != 0
    assert "Aborted" in result.combined
    assert "successfully pushed" not in result.combined.lower()


def test_b3_push_failure_exits_nonzero(sandbox_factory):
    """B3: push to invalid remote exits non-zero (SC2)."""
    sb = sandbox_factory()
    sb.init_repo(".file:common\n")
    sb.write_home(".file", "content\n")

    bad_remote = sb.root / "readonly"
    bad_remote.mkdir()
    bad_remote.chmod(0o555)
    sb.git_cmd("remote", "add", "origin", f"file://{bad_remote.resolve()}", cwd=sb.repo)

    result = sb.run_dotsync("save", "common", "--non-interactive")
    assert result.returncode != 0
    assert "Failed to push" in result.combined


def test_b4_binary_conflict_shows_summary_and_cancel(sandbox_factory):
    """B4: binary conflict shows summary; cancel leaves home unchanged (SC6)."""
    sb = sandbox_factory()
    sb.init_repo(".bin:common\n")
    (sb.home / ".bin").write_bytes(b"\x00\x01\x02\xff")
    assert sb.save_no_push("common").returncode == 0

    conflicting = b"\xaa\xbb\xcc\xdd"
    bin_path = sb.home / ".bin"
    bin_path.write_bytes(conflicting)

    result = sb.run_dotsync("restore", "common", "--skip-pull", stdin="c\n")
    assert result.returncode != 0
    assert f"Binary files differ: {bin_path}" in result.combined
    assert bin_path.read_bytes() == conflicting


def test_b5_no_push_prints_durability_warning(sandbox_factory):
    """B5: --no-push prints durability warning."""
    sb = sandbox_factory(with_bare=True)
    sb.init_repo(".file:common\n")
    sb.write_home(".file", "content\n")
    sb.add_origin()

    result = sb.run_dotsync("save", "--no-push", "--non-interactive", "common")
    assert result.returncode == 0, result.combined
    assert "not durable" in result.combined.lower()
