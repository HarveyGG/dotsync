"""Black-box symlink scenario S5 from tests/blackbox/test_plan.md."""

from __future__ import annotations

import json
import os
import shutil

import pytest

pytestmark = pytest.mark.blackbox


def _save_s1_internal_symlink(sb) -> None:
    """S1 setup: internal symlink materialized with manifest sidecar."""
    sb.init_repo("@tree:.config/app:editor\n")
    app = sb.home / ".config" / "app"
    app.mkdir(parents=True)
    (app / "real.txt").write_text("hello")
    os.symlink("real.txt", app / "link.txt")
    assert sb.save_no_push("editor").returncode == 0


def test_s5_restore_recreates_internal_symlink_when_target_exists(sandbox_factory):
    """S5: restore recreates internal user symlink when target exists in tree."""
    sb = sandbox_factory()
    _save_s1_internal_symlink(sb)

    shutil.rmtree(sb.home / ".config" / "app")
    assert sb.restore("editor", skip_pull=True, conflict="overwrite").returncode == 0

    app = sb.home / ".config" / "app"
    real = app / "real.txt"
    link = app / "link.txt"
    assert real.is_file() and not real.is_symlink()
    assert real.read_text() == "hello"
    assert link.is_symlink()
    assert os.readlink(link) == "real.txt"

    manifest = json.loads(
        (sb.repo / ".dotsync" / "manifests" / "editor.json").read_text()
    )
    assert any(e["home_path"] == ".config/app/link.txt" for e in manifest)
