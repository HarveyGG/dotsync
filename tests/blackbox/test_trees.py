"""Black-box tree scenarios T2, T4 from tests/blackbox/test_plan.md."""

from __future__ import annotations

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
