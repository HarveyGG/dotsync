"""Content regression detection on save (HOME → repo mirror)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from dotsync.tree import plan_tree_symlink_materializations, watched_tree_paths


@dataclass(frozen=True)
class ContentRegression:
    rel_path: str
    old_size: int
    new_size: int
    reason: str


def _read_file_bytes(path: str) -> bytes:
    with open(path, 'rb') as f:
        return f.read()


def _entry_guards(entry: dict) -> Tuple[Optional[int], Optional[str]]:
    return entry.get('min_bytes'), entry.get('guard')


def _check_entry_guards(
    rel_path: str,
    repo_path: str,
    new_bytes: bytes,
    new_size: int,
    entry: dict,
) -> Optional[ContentRegression]:
    min_bytes, guard = _entry_guards(entry)
    old_size = os.path.getsize(repo_path) if os.path.isfile(repo_path) else 0

    if min_bytes is not None and new_size < min_bytes:
        return ContentRegression(
            rel_path, old_size, new_size, f'below min-bytes={min_bytes}'
        )

    if guard == 'nonempty' and len(new_bytes.strip()) == 0:
        return ContentRegression(
            rel_path, old_size, new_size, 'whitespace-only (guard=nonempty)'
        )
    return None


def _check_content_drop(
    rel_path: str,
    old_bytes: bytes,
    old_size: int,
    new_bytes: bytes,
    new_size: int,
    plugin_name: str,
) -> Optional[ContentRegression]:
    if plugin_name == 'encrypt':
        if old_size > 0 and len(new_bytes.strip()) == 0:
            return ContentRegression(rel_path, old_size, new_size, 'whitespace-only')
        return None

    if old_bytes == new_bytes:
        return None

    if len(old_bytes.strip()) > 0 and len(new_bytes.strip()) == 0:
        return ContentRegression(rel_path, old_size, new_size, 'whitespace-only')

    if old_size >= 200 and (
        new_size <= 16 or (new_size < old_size * 0.1 and new_size < 64)
    ):
        return ContentRegression(rel_path, old_size, new_size, 'sharp size drop')

    return None


def evaluate_pair(
    rel_path: str,
    source_path: str,
    repo_path: str,
    entry: dict,
    plugin_name: str,
    plugin,
) -> Optional[ContentRegression]:
    """Return a regression if updating source_path → repo_path should be blocked."""
    if not os.path.isfile(source_path):
        return None

    try:
        new_bytes = _read_file_bytes(source_path)
    except OSError:
        return None
    new_size = len(new_bytes)

    if os.path.isfile(repo_path):
        try:
            if plugin.samefile(repo_path, source_path):
                return None
        except Exception:
            pass

    hit = _check_entry_guards(rel_path, repo_path, new_bytes, new_size, entry)
    if hit:
        return hit

    if not os.path.isfile(repo_path):
        return None

    old_bytes = _read_file_bytes(repo_path)
    old_size = len(old_bytes)
    return _check_content_drop(
        rel_path, old_bytes, old_size, new_bytes, new_size, plugin_name
    )


def collect_content_regressions(
    filelist_obj,
    home: str,
    repo: str,
    plugin_dirs: Dict[str, str],
    categories,
    active_filelist: dict,
    plugins: dict,
) -> List[ContentRegression]:
    """Scan all pending save writes for content regressions."""
    regressions: List[ContentRegression] = []
    checked: Set[str] = set()

    for path, entry in active_filelist.items():
        if entry.get('kind') == 'symlink':
            continue
        plugin_name = entry['plugin']
        plugin_dir = plugin_dirs[plugin_name]
        plugin = plugins[plugin_name]
        master = min(entry['categories'])
        source = os.path.join(home, path)
        repo_path = os.path.join(plugin_dir, master, path)
        if repo_path in checked:
            continue
        checked.add(repo_path)
        hit = evaluate_pair(path, source, repo_path, entry, plugin_name, plugin)
        if hit:
            regressions.append(hit)

    active_cats = filelist_obj._flatten_categories(categories)
    for tree in filelist_obj.trees:
        if not set(active_cats) & set(tree['categories']):
            continue
        plugin_name = tree['plugin']
        plugin_dir = plugin_dirs[plugin_name]
        plugin = plugins[plugin_name]
        watched = watched_tree_paths(home, tree)
        master = min(tree['categories'])
        tree_guard = {k: tree[k] for k in ('min_bytes', 'guard') if k in tree}

        for home_rel, source_abs, dest in plan_tree_symlink_materializations(
            home,
            plugin_dir,
            watched,
            master,
            tree['pattern'],
            dotsync_repo=repo,
        ):
            if dest in checked:
                continue
            checked.add(dest)
            entry = {**watched.get(home_rel, {}), **tree_guard}
            hit = evaluate_pair(home_rel, source_abs, dest, entry, plugin_name, plugin)
            if hit:
                regressions.append(hit)

    regressions.sort(key=lambda r: r.rel_path)
    return regressions


def print_regression_report(regressions: List[ContentRegression]) -> None:
    print(f'Content regression detected in {len(regressions)} file(s):')
    for reg in regressions:
        print(f'  {reg.rel_path} ({reg.old_size} B -> {reg.new_size} B, {reg.reason})')


REFUSE_HINT = (
    'Refusing to overwrite repository mirror with regressed content. '
    'Re-run with --force-content-regression (or --accept-regressions) to allow.'
)


def handle_content_regressions(
    regressions: List[ContentRegression],
    force: bool,
) -> int:
    """Print report; return 1 to abort save/update or 0 to proceed."""
    if not regressions:
        return 0
    print_regression_report(regressions)
    if force:
        logging.warning('Content regression override is active; proceeding with save.')
        return 0
    print(REFUSE_HINT)
    logging.error('Save aborted due to content regression.')
    return 1