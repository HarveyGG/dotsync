"""Black-box mirror-only scenarios M2–M3 from tests/blackbox/test_plan.md."""

from __future__ import annotations

import hashlib
import shutil

import pytest

pytestmark = pytest.mark.blackbox

MOCKDIR_FILELIST = (
    ".mockdir/.hidden/file:mock\n"
    ".mockdir/subdir/file1:mock\n"
    ".mockdir/subdir/subdir2/file2:mock\n"
)


def test_m2_byte_identical_round_trip_atomic_file(sandbox_factory):
    """M2: atomic file round-trip preserves bytes (SC1, SC2)."""
    sb = sandbox_factory()
    sb.init_repo(".config/app/settings.json:editor\n")
    content = "café\nline2\n"
    settings = sb.home / ".config" / "app" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text(content)
    pre_hash = hashlib.sha256(content.encode()).hexdigest()

    assert sb.save_no_push("editor").returncode == 0
    shutil.rmtree(sb.home / ".config")

    assert sb.restore("editor", skip_pull=True, conflict="overwrite").returncode == 0
    restored = sb.home / ".config" / "app" / "settings.json"
    assert hashlib.sha256(restored.read_text(encoding="utf-8").encode()).hexdigest() == pre_hash


def test_m3_nested_tree_paths_restore_as_regular_files(sandbox_factory):
    """M3: nested atomic paths restore as regular files, not symlinks."""
    sb = sandbox_factory()
    sb.init_repo(MOCKDIR_FILELIST)
    mock = sb.home / ".mockdir"
    (mock / ".hidden").mkdir(parents=True)
    (mock / ".hidden" / "file").write_text("hidden\n")
    (mock / "subdir").mkdir(parents=True)
    (mock / "subdir" / "file1").write_text("f1\n")
    (mock / "subdir" / "subdir2").mkdir(parents=True)
    (mock / "subdir" / "subdir2" / "file2").write_text("f2\n")

    assert sb.save_no_push("mock").returncode == 0
    shutil.rmtree(mock)

    assert sb.restore("mock", skip_pull=True, conflict="overwrite").returncode == 0

    paths = [
        ".mockdir/.hidden/file",
        ".mockdir/subdir/file1",
        ".mockdir/subdir/subdir2/file2",
    ]
    for rel in paths:
        fp = sb.home / rel
        assert fp.is_file() and not fp.is_symlink(), rel
    assert not sb.symlinks_pointing_into_repo()
