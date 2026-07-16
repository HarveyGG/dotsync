import fnmatch
import os
from dataclasses import dataclass
from typing import Dict, List

DIR_SKIP = {'extensions', 'worktrees', 'Cache', 'CachedData', '.git', 'node_modules', 'logs'}

SYSTEM_FILES = {'.DS_Store', 'Thumbs.db', '.DS_Store?'}


@dataclass
class TreeEntry:
    pattern: str
    categories: List[str]
    plugin: str = 'plain'


def pattern_walk_root(pattern: str) -> str:
    for i, ch in enumerate(pattern):
        if ch in '*?[]':
            slash = pattern.rfind('/', 0, i)
            return pattern[:slash + 1] if slash >= 0 else ''
    return pattern


def pattern_has_glob(pattern: str) -> bool:
    return any(ch in pattern for ch in '*?[]')


def normalize_home_rel(home: str, abs_path: str) -> str:
    rel = os.path.relpath(abs_path, home)
    if not rel.startswith('.'):
        rel = '.' + rel
    return rel


def walk_tree(home: str, pattern: str) -> Dict[str, dict]:
    """Walk home for file paths matching a tree pattern."""
    walk_root = pattern_walk_root(pattern)
    abs_root = os.path.join(home, walk_root)

    if not os.path.exists(abs_root):
        return {}

    has_glob = pattern_has_glob(pattern)

    if os.path.isfile(abs_root) or os.path.islink(abs_root):
        rel = normalize_home_rel(home, abs_root)
        if has_glob and not fnmatch.fnmatch(rel, pattern):
            return {}
        if not has_glob and rel != pattern:
            return {}
        kind = 'symlink' if os.path.islink(abs_root) else 'file'
        return {rel: {'kind': kind}}

    results = {}
    for root, dirs, files in os.walk(abs_root):
        dirs[:] = [d for d in dirs if d not in DIR_SKIP]
        for fname in files:
            if fname in SYSTEM_FILES:
                continue
            abs_f = os.path.join(root, fname)
            rel = normalize_home_rel(home, abs_f)

            if has_glob:
                if not fnmatch.fnmatch(rel, pattern):
                    continue
            elif rel != pattern and not rel.startswith(pattern + '/'):
                continue

            kind = 'symlink' if os.path.islink(abs_f) else 'file'
            results[rel] = {'kind': kind}

    return results
