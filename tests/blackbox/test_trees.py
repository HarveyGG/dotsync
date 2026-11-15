"""Black-box tree scenarios T2–T4 from tests/blackbox/test_plan.md."""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.blackbox


def test_t2_glob_filter_on_tree_excludes_non_matching_paths(sandbox_factory):
    """T2: @tree glob includes only matching paths; excludes node_modules."""
    sb = sandbox_factory()
    sb.init_repo("@tree:.agents/skills/vibe-module-*:tools\n")
    skills = sb.home / ".agents" / "skills"
    (skills / "vibe-module-foo").mkdir(parents=True)
    (skills / "vibe-module-foo" / "SKILL.md").write_text("foo\n")
    (skills / "vibe-module-bar").mkdir(parents=True)
    (skills / "vibe-module-bar" / "SKILL.md").write_text("bar\n")
    (skills / "other-module").mkdir(parents=True)
    (skills / "other-module" / "SKILL.md").write_text("other\n")
    baz_pkg = skills / "vibe-module-baz" / "node_modules" / "pkg"
    baz_pkg.mkdir(parents=True)
    (baz_pkg / "index.js").write_text("skip\n")

    assert sb.save_no_push("tools").returncode == 0

    foo_mirror = sb.mirror_path("tools", ".agents/skills/vibe-module-foo/SKILL.md")
    bar_mirror = sb.mirror_path("tools", ".agents/skills/vibe-module-bar/SKILL.md")
    assert foo_mirror.exists()
    assert bar_mirror.exists()
    assert not sb.mirror_path("tools", ".agents/skills/other-module/SKILL.md").exists()
    tools_mirror_root = sb.repo / "dotfiles" / "plain" / "tools"
    assert not any("node_modules" in str(p) for p in tools_mirror_root.rglob("*"))


def test_t3_prune_stale_repo_file_after_tree_member_removed(sandbox_factory):
    """T3: removing tree member prunes stale mirror after interactive confirm."""
    sb = sandbox_factory()
    sb.init_repo("@tree:.config/myapp:editor\n")
    app = sb.home / ".config" / "myapp"
    app.mkdir(parents=True)
    (app / "settings.json").write_text('{"key": "value"}\n')
    (app / "old.json").write_text('{"stale": true}\n')

    assert sb.save_no_push("editor").returncode == 0

    old_mirror = sb.mirror_path("editor", ".config/myapp/old.json")
    settings_mirror = sb.mirror_path("editor", ".config/myapp/settings.json")
    assert old_mirror.exists()
    assert settings_mirror.exists()

    (app / "old.json").unlink()

    result = sb.run_dotsync("save", "--no-push", "editor", stdin="n\n")
    assert result.returncode == 1, result.combined
    assert "no longer in the manifest" in result.combined
    assert "old.json" in result.combined
    assert old_mirror.exists()

    result = sb.run_dotsync(
        "save", "--no-push", "--yes", "--non-interactive", "editor"
    )
    assert result.returncode == 0, result.combined
    assert "no longer in the manifest" not in result.combined
    assert not old_mirror.exists()
    assert settings_mirror.exists()


def test_t4_tree_save_restore_roundtrip_on_clean_home(sandbox_factory):
    """T4: @tree save then restore on fresh HOME via bare remote (SC5, SC1)."""
    sb = sandbox_factory(with_bare=True, with_home2=True)
    sb.init_repo("@tree:.config/nvim:editor\n")
    nvim = sb.home / ".config" / "nvim"
    nvim.mkdir(parents=True)
    original = "require('plugins')\n"
    (nvim / "init.lua").write_text(original)

    assert sb.save_no_push("editor").returncode == 0
    sb.add_origin()
    branch = sb.git_cmd("rev-parse", "--abbrev-ref", "HEAD", cwd=sb.repo).stdout.strip()
    sb.git_cmd("push", "-u", "origin", branch, cwd=sb.repo)

    home2 = sb.home2
    result = sb.restore_fresh(home2, "editor")
    assert result.returncode == 0, result.combined

    restored = home2 / ".config" / "nvim" / "init.lua"
    assert restored.read_text() == original
    assert restored.is_file() and not restored.is_symlink()
    assert not sb.symlinks_pointing_into_repo(home2)


def _good_skill_md() -> str:
    """SKILL.md body sized like production regressions (>=200 B)."""
    body = """---
name: Test Module
description: "Module description for regression guard blackbox test"
---

# Test Module

Substantive skill content for dotsync regression guard.
"""
    pad = "x" * max(0, 220 - len(body))
    return body + ("\n# Padding\n" + pad + "\n" if pad else "")


def test_t_regression_skill_md(sandbox_factory):
    """T-regression-skill-md: 1-byte home file must not wipe 421 B repo mirror."""
    sb = sandbox_factory()
    sb.init_repo("@tree:.cursor/skills:skills\n")
    module = "vibe-module-test"
    skill_home = sb.home / ".cursor" / "skills" / module / "SKILL.md"
    skill_home.parent.mkdir(parents=True)
    good_content = _good_skill_md()
    skill_home.write_text(good_content)
    assert sb.save_no_push("skills").returncode == 0

    skill_mirror = sb.mirror_path(
        "skills", f".cursor/skills/{module}/SKILL.md"
    )
    assert skill_mirror.exists()
    assert skill_mirror.stat().st_size >= 200

    skill_home.write_text("\n")
    assert skill_home.stat().st_size == 1

    result = sb.save_no_push("skills")
    assert result.returncode == 1, result.combined
    assert "Content regression" in result.combined
    assert f"{module}/SKILL.md" in result.combined or module in result.combined
    assert skill_mirror.read_bytes() == good_content.encode()
    status = sb.git_cmd("status", "--porcelain", cwd=sb.repo).stdout.strip()
    assert "SKILL.md" not in status or status == ""


def test_t_whitespace_only_small_repo(sandbox_factory):
    """T-whitespace-only: wipe triggers even when repo file is below 200 B."""
    sb = sandbox_factory()
    sb.init_repo("@tree:.cursor/skills:skills\n")
    module = "small-module"
    skill_home = sb.home / ".cursor" / "skills" / module / "SKILL.md"
    skill_home.parent.mkdir(parents=True)
    frontmatter = "---\nname: small\n---\n"
    skill_home.write_text(frontmatter)
    assert sb.save_no_push("skills").returncode == 0
    skill_mirror = sb.mirror_path("skills", f".cursor/skills/{module}/SKILL.md")
    assert len(skill_mirror.read_bytes()) == len(frontmatter.encode())

    skill_home.write_text("\n")
    result = sb.save_no_push("skills")
    assert result.returncode == 1
    assert "whitespace-only" in result.combined
    assert skill_mirror.read_text() == frontmatter


def test_t_force_content_regression_override(sandbox_factory):
    sb = sandbox_factory()
    sb.init_repo("@tree:.cursor/skills:skills\n")
    module = "force-module"
    skill_home = sb.home / ".cursor" / "skills" / module / "SKILL.md"
    skill_home.parent.mkdir(parents=True)
    good = _good_skill_md()
    skill_home.write_text(good)
    assert sb.save_no_push("skills").returncode == 0
    skill_mirror = sb.mirror_path("skills", f".cursor/skills/{module}/SKILL.md")

    skill_home.write_text("\n")
    blocked = sb.save_no_push("skills")
    assert blocked.returncode == 1

    forced = sb.run_dotsync(
        "save",
        "--no-push",
        "--non-interactive",
        "--force-content-regression",
        "skills",
    )
    assert forced.returncode == 0
    assert skill_mirror.read_bytes() == b"\n"
    status = sb.git_cmd("status", "--porcelain", cwd=sb.repo).stdout
    assert "SKILL.md" in status or sb.git_cmd(
        "log", "-1", "--oneline", cwd=sb.repo
    ).stdout


def test_t_accept_regressions_alias(sandbox_factory):
    sb = sandbox_factory()
    sb.init_repo(".wip:common\n")
    sb.write_home(".wip", "original content here\n" * 15)
    assert sb.save_no_push("common").returncode == 0
    sb.write_home(".wip", "\n")
    assert sb.save_no_push("common").returncode == 1
    ok = sb.run_dotsync(
        "save", "--no-push", "--non-interactive", "--accept-regressions", "common"
    )
    assert ok.returncode == 0
    assert sb.mirror_path("common", ".wip").read_bytes() == b"\n"


def test_t_dry_run_regression(sandbox_factory):
    sb = sandbox_factory()
    sb.init_repo(".wip:common\n")
    sb.write_home(".wip", "x" * 220)
    assert sb.save_no_push("common").returncode == 0
    sb.write_home(".wip", "\n")
    result = sb.run_dotsync("save", "--dry-run", "--no-push", "common")
    assert result.returncode == 1
    assert "Content regression" in result.combined
    assert sb.mirror_path("common", ".wip").stat().st_size == 220


def test_t_filelist_guard_min_bytes(sandbox_factory):
    sb = sandbox_factory()
    sb.init_repo(".wip:common|min-bytes=50\n")
    sb.write_home(".wip", "short")
    result = sb.save_no_push("common")
    assert result.returncode == 1
    assert "min-bytes=50" in result.combined


def test_t_tree_bulk_one_regression_aborts(sandbox_factory):
    sb = sandbox_factory()
    sb.init_repo("@tree:.cursor/skills:skills\n")
    base = sb.home / ".cursor" / "skills"
    for i in range(100):
        d = base / f"mod-{i}"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(f"content-{i}\n" * 30)
    assert sb.save_no_push("skills").returncode == 0

    good_mirror = sb.mirror_path("skills", ".cursor/skills/mod-0/SKILL.md")
    good_bytes = good_mirror.read_bytes()
    (base / "mod-0" / "SKILL.md").write_text("\n")
    for i in range(1, 100):
        (base / f"mod-{i}" / "SKILL.md").write_text(f"updated-{i}\n" * 30)

    result = sb.save_no_push("skills")
    assert result.returncode == 1
    assert "mod-0" in result.combined
    assert good_mirror.read_bytes() == good_bytes
    untouched = sb.mirror_path("skills", ".cursor/skills/mod-1/SKILL.md")
    assert b"updated-1" not in untouched.read_bytes()


def test_t_update_blocks_content_regression(sandbox_factory):
    sb = sandbox_factory()
    sb.init_repo(".wip:common\n")
    sb.write_home(".wip", "x" * 220)
    assert sb.save_no_push("common").returncode == 0
    sb.write_home(".wip", "\n")
    result = sb.run_dotsync("update", "--no-push", "--non-interactive", "common")
    assert result.returncode == 1
    assert "Content regression" in result.combined
    assert sb.mirror_path("common", ".wip").stat().st_size == 220


def test_t_external_symlink_target_regression_blocked(sandbox_factory):
    sb = sandbox_factory()
    sb.init_repo("@tree:.config/app:tools\n")
    external = sb.root / "external"
    external.mkdir()
    payload = "external secret payload\n" * 15
    (external / "secret.cfg").write_text(payload)
    app = sb.home / ".config" / "app"
    app.mkdir(parents=True)
    os.symlink(str(external / "secret.cfg"), app / "link.cfg")
    assert sb.save_no_push("tools").returncode == 0
    materialized = next(
        p for p in (sb.repo / ".dotsync" / "materialized").rglob("secret.cfg")
        if p.is_file()
    )
    assert materialized.read_text() == payload

    (external / "secret.cfg").write_text("\n")
    result = sb.save_no_push("tools")
    assert result.returncode == 1
    assert "link.cfg" in result.combined
    assert materialized.read_text() == payload


def test_t_guard_nonempty_end_to_end(sandbox_factory):
    sb = sandbox_factory()
    sb.init_repo("@tree:.config/app:common|guard=nonempty\n")
    app = sb.home / ".config" / "app"
    app.mkdir(parents=True)
    (app / "cfg.txt").write_text("valid config\n")
    assert sb.save_no_push("common").returncode == 0
    (app / "cfg.txt").write_text("\n")
    result = sb.save_no_push("common")
    assert result.returncode == 1
    assert "guard=nonempty" in result.combined


def test_t_filelist_guard_nonempty_and_encrypt_combo(sandbox_factory):
    sb = sandbox_factory()
    filelist = (
        ".secret:common|encrypt|min-bytes=50\n"
        ".note:common|guard=nonempty\n"
    )
    sb.init_repo(filelist)
    assert sb.run_dotsync("list").returncode == 0
    sb.write_home(".note", "hello\n")
    sb.write_home(".secret", "short")
    result = sb.save_no_push("common")
    assert result.returncode == 1
    assert "min-bytes=50" in result.combined


def test_t_min_bytes_twenty_enforced(sandbox_factory):
    sb = sandbox_factory()
    sb.init_repo(".wip:common|min-bytes=20\n")
    sb.write_home(".wip", "x" * 19)
    result = sb.save_no_push("common")
    assert result.returncode == 1
    assert "min-bytes=20" in result.combined


def test_t_multi_tree_same_category_guard_isolation(sandbox_factory):
    """Tree A min-bytes guard must not apply to tree B paths in the same category."""
    sb = sandbox_factory()
    filelist = "@tree:.tree-a:common|min-bytes=50\n@tree:.tree-b:common\n"
    sb.init_repo(filelist)
    tree_a = sb.home / ".tree-a"
    tree_b = sb.home / ".tree-b"
    tree_a.mkdir(parents=True)
    tree_b.mkdir(parents=True)
    (tree_a / "ok.txt").write_text("x" * 50)
    ext_tiny = sb.home / ".ext_tiny"
    ext_tiny.write_text("ok\n")
    os.symlink(str(ext_tiny), tree_b / "link.txt")
    result = sb.save_no_push("common")
    assert result.returncode == 0
    materialized = [
        p for p in (sb.repo / ".dotsync" / "materialized").rglob("*") if p.is_file()
    ]
    assert any(p.read_text() == "ok\n" for p in materialized)


@pytest.mark.parametrize(
    "bad_line",
    [
        ".wip:common|min-bytes=abc\n",
        ".wip:common|min-bytes=-1\n",
        "@tree:.config/app:common|guard=bogus\n",
    ],
)
def test_t_invalid_filelist_modifiers_exit_1(sandbox_factory, bad_line):
    sb = sandbox_factory()
    sb.init_repo(bad_line, commit=False)
    sb.write_home(".wip", "hello" if bad_line.startswith(".wip") else "")
    if bad_line.startswith("@tree"):
        app = sb.home / ".config" / "app"
        app.mkdir(parents=True)
        (app / "cfg.txt").write_text("ok\n")
    result = sb.run_dotsync("list")
    assert result.returncode == 1
    assert "Invalid filelist modifier" in result.combined
