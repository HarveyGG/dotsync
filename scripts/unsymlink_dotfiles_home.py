#!/usr/bin/env python3
"""
One-off migration utility — NOT part of the dotsync product.

Replaces home paths that are symlinks into a dotfiles repo with regular files
(copying the resolved content). Use before adopting mirror-only dotsync (v2).

Usage:
  python3 scripts/unsymlink_dotfiles_home.py --dry-run
  python3 scripts/unsymlink_dotfiles_home.py --apply

Environment:
  DOTSYNC_REPO  default ~/.dotfiles
  HOME          default from pathlib
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path


def parse_filelist_paths(filelist: Path) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()
    for line in filelist.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" in line:
            continue
        path = line.split(":")[0].split("|")[0]
        if path not in seen:
            seen.add(path)
            paths.append(path)
    return paths


def is_under(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def materialize_symlink(home_path: Path, repo_root: Path, dry_run: bool) -> str:
    if not home_path.is_symlink():
        return "skip-not-symlink"
    target = home_path.resolve()
    if not is_under(target, repo_root):
        return f"skip-external-target->{target}"

    if dry_run:
        return f"would-replace-symlink->{target}"

    home_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        dir=home_path.parent, prefix=f".{home_path.name}.", suffix=".tmp"
    )
    os.close(fd)
    tmp_path = Path(tmp)
    try:
        if target.is_dir():
            # Should not happen for filelist file entries; skip safely.
            return f"skip-symlink-to-dir->{target}"
        shutil.copy2(target, tmp_path)
        home_path.unlink()
        tmp_path.rename(home_path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise
    return "ok"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--repo",
        default=os.environ.get("DOTSYNC_REPO", str(Path.home() / ".dotfiles")),
    )
    args = parser.parse_args()

    home = Path.home()
    repo = Path(args.repo).expanduser().resolve()
    filelist = repo / "filelist"
    if not filelist.is_file():
        print(f"error: filelist not found: {filelist}", file=sys.stderr)
        return 1

    dry_run = args.dry_run
    paths = parse_filelist_paths(filelist)
    stats = {"ok": 0, "skip-not-symlink": 0, "skip-external-target": 0, "skip-symlink-to-dir": 0, "error": 0}

    print(f"home={home}")
    print(f"repo={repo}")
    print(f"filelist entries (unique paths)={len(paths)}")
    print(f"mode={'dry-run' if dry_run else 'apply'}")
    print("---")

    for rel in paths:
        home_path = home / rel
        try:
            result = materialize_symlink(home_path, repo, dry_run)
            key = result.split("-")[0] if result.startswith("ok") else result.split("->")[0]
            if key.startswith("would"):
                stats["ok"] += 1
            elif key.startswith("skip"):
                bucket = "skip-not-symlink"
                if "external" in result:
                    bucket = "skip-external-target"
                elif "dir" in result:
                    bucket = "skip-symlink-to-dir"
                stats[bucket] = stats.get(bucket, 0) + 1
            elif result == "ok":
                stats["ok"] += 1
            print(f"{rel}: {result}")
        except Exception as e:
            stats["error"] += 1
            print(f"{rel}: error {e}", file=sys.stderr)

    print("---")
    print(stats)
    return 1 if stats["error"] else 0


if __name__ == "__main__":
    sys.exit(main())
