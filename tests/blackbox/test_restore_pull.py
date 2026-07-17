"""Black-box restore-pull scenarios RP3–RP4 from tests/blackbox/test_plan.md."""

from __future__ import annotations

import pytest

from tests.blackbox.conftest import setup_repo_behind_remote

pytestmark = pytest.mark.blackbox


def test_rp3_skip_pull_uses_local_head_without_fetch(sandbox_factory):
    """RP3: --skip-pull restores from stale local HEAD (unsafe path)."""
    sb = sandbox_factory(with_bare=True)
    setup_repo_behind_remote(sb, ".file:common\n", "remote-content\n")
    local_mirror = sb.mirror_path("common", ".file")
    local_mirror.write_text("local-content")
    assert not (sb.home / ".file").exists()

    result = sb.restore("common", skip_pull=True, conflict="overwrite")
    assert result.returncode == 0, result.combined
    assert (sb.home / ".file").read_text() == "local-content"


def test_rp4_no_remote_restore_uses_local_head(sandbox_factory):
    """RP4: no origin uses local HEAD with informational debug message."""
    sb = sandbox_factory()
    sb.init_repo(".file:common\n")
    sb.write_home(".file", "local-only\n")
    assert sb.save_no_push("common").returncode == 0
    local_sha = sb.head_sha()
    (sb.home / ".file").unlink()
    assert not (sb.home / ".file").exists()

    result = sb.run_dotsync(
        "restore",
        "common",
        "-vv",
        "--non-interactive",
        "--conflict",
        "overwrite",
    )
    assert result.returncode == 0, result.combined
    assert f"Restoring from commit {local_sha}" in result.stdout
    assert "No remote configured; using local repository" in result.combined
    assert (sb.home / ".file").read_text() == "local-only\n"
