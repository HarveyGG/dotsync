"""Black-box conflict scenarios C2–C5 from tests/blackbox/test_plan.md."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.blackbox


def _setup_c1_pair(sb) -> None:
    """Shared setup: two tracked files saved then overwritten at home."""
    sb.init_repo(".file1:common\n.file2:common\n")
    sb.write_home(".file1", "repo-one\n")
    sb.write_home(".file2", "repo-two\n")
    assert sb.save_no_push("common").returncode == 0
    sb.write_home(".file1", "home-one\n")
    sb.write_home(".file2", "home-two\n")


def test_c2_overwrite_continues_restore_for_remaining_paths(sandbox_factory):
    """C2: overwrite on first conflict continues restore for remaining paths (SC6)."""
    sb = sandbox_factory()
    _setup_c1_pair(sb)

    result = sb.run_dotsync("restore", "common", stdin="o\no\n")
    assert result.returncode == 0, result.combined
    assert (sb.home / ".file1").read_text() == "repo-one\n"
    assert (sb.home / ".file2").read_text() == "repo-two\n"


def test_c3_identical_home_file_skipped_without_prompt(sandbox_factory):
    """C3: identical home file skipped without reading stdin."""
    sb = sandbox_factory()
    sb.init_repo(".same:common\n")
    content = "unchanged content\n"
    sb.write_home(".same", content)
    assert sb.save_no_push("common").returncode == 0

    result = sb.restore("common", skip_pull=True)
    assert result.returncode == 0, result.combined
    assert "-unchanged content" not in result.stdout
    assert (sb.home / ".same").read_text() == content


def test_c4_non_interactive_conflict_overwrite_applies_all(sandbox_factory):
    """C4: --conflict overwrite applies all conflicting files non-interactively."""
    sb = sandbox_factory()
    _setup_c1_pair(sb)

    result = sb.restore("common", skip_pull=True, conflict="overwrite")
    assert result.returncode == 0, result.combined
    assert (sb.home / ".file1").read_text() == "repo-one\n"
    assert (sb.home / ".file2").read_text() == "repo-two\n"


def test_c5_non_interactive_conflict_abort_exits_without_writes(sandbox_factory):
    """C5: --conflict abort exits non-zero without modifying home."""
    sb = sandbox_factory()
    sb.init_repo(".conflict:common\n")
    sb.write_home(".conflict", "repo-version\n")
    assert sb.save_no_push("common").returncode == 0
    sb.write_home(".conflict", "home-version\n")

    result = sb.restore("common", skip_pull=True, conflict="abort")
    assert result.returncode != 0
    assert (sb.home / ".conflict").read_text() == "home-version\n"
