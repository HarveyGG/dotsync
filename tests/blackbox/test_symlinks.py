"""Black-box symlink scenarios S2–S5 from tests/blackbox/test_plan.md."""

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


def test_s2_external_symlink_materialized_under_dotsync_materialized(sandbox_factory):
    """S2: external symlink materialized under .dotsync/materialized/ (save-only, SC3)."""
    sb = sandbox_factory()
    external = sb.root / "external"
    external.mkdir()
    (external / "secret.cfg").write_text("external-data")

    sb.init_repo("@tree:.config/app:tools\n")
    app = sb.home / ".config" / "app"
    app.mkdir(parents=True)
    os.symlink(str(external / "secret.cfg"), app / "link.cfg")

    result = sb.save_no_push("tools")
    assert result.returncode == 0, result.combined

    materialized_dir = sb.repo / ".dotsync" / "materialized"
    assert materialized_dir.exists()
    materialized_files = [p for p in materialized_dir.rglob("*") if p.is_file()]
    assert any(p.read_text() == "external-data" for p in materialized_files)

    manifest = json.loads(
        (sb.repo / ".dotsync" / "manifests" / "tools.json").read_text()
    )
    assert len(manifest) == 1
    entry = manifest[0]
    assert entry["home_path"] == ".config/app/link.cfg"
    assert entry["kind"] == "symlink"
    assert entry["target"] == str(external / "secret.cfg")
    assert entry["canonical_repo_path"].startswith(".dotsync/materialized/")
    assert entry["canonical_repo_path"].endswith("/secret.cfg")

    materialized = sb.repo / entry["canonical_repo_path"]
    assert materialized.is_file()
    assert materialized.read_text() == "external-data"
    assert not (sb.mirror_path("tools", ".config/app/link.cfg")).exists()


def test_s3_broken_symlink_warn_and_skip(sandbox_factory):
    """S3: broken symlink warns and skips with no mirror artifact."""
    sb = sandbox_factory()
    sb.init_repo("@tree:.config/app:editor\n")
    app = sb.home / ".config" / "app"
    app.mkdir(parents=True)
    os.symlink("missing.txt", app / "broken.txt")

    result = sb.save_no_push("editor")
    assert result.returncode == 0, result.combined
    assert "broken symlink" in result.combined
    assert ".config/app/broken.txt" in result.combined

    assert not (sb.mirror_path("editor", ".config/app/broken.txt")).exists()

    manifest_path = sb.repo / ".dotsync" / "manifests" / "editor.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        assert not any(e["home_path"] == ".config/app/broken.txt" for e in manifest)


def test_s4_dedup_when_link_target_also_watched(sandbox_factory):
    """S4: dedup when symlink target is also watched in tree."""
    sb = sandbox_factory()
    sb.init_repo("@tree:.config/app:editor\n")
    app = sb.home / ".config" / "app"
    app.mkdir(parents=True)
    (app / "real.txt").write_text("shared")
    os.symlink("real.txt", app / "link.txt")

    assert sb.save_no_push("editor").returncode == 0

    canonical = sb.mirror_path("editor", ".config/app/real.txt")
    assert canonical.read_text() == "shared"
    assert not (sb.mirror_path("editor", ".config/app/link.txt")).exists()

    manifest = json.loads(
        (sb.repo / ".dotsync" / "manifests" / "editor.json").read_text()
    )
    assert len(manifest) == 1
    entry = manifest[0]
    assert entry["home_path"] == ".config/app/link.txt"
    assert entry["kind"] == "symlink"
    assert entry["target"] == "real.txt"
    assert entry["canonical_repo_path"] == "editor/.config/app/real.txt"


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
