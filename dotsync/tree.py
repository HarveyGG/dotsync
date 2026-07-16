import fnmatch
import hashlib
import logging
import os
import shutil
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from dotsync.manifest import MATERIALIZED_DIR, read_manifest, write_manifest

DIR_SKIP = {'extensions', 'worktrees', 'Cache', 'CachedData', '.git', 'node_modules', 'logs'}

SYSTEM_FILES = {'.DS_Store', 'Thumbs.db', '.DS_Store?'}

SYMLINK_MAX_DEPTH = 40


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


def is_internal_target(home_rel: str, tree_pattern: str) -> bool:
    walk_root = pattern_walk_root(tree_pattern)
    if not walk_root:
        return fnmatch.fnmatch(home_rel, tree_pattern)
    if not (home_rel == walk_root or home_rel.startswith(walk_root + '/')):
        return False
    if pattern_has_glob(tree_pattern):
        return fnmatch.fnmatch(home_rel, tree_pattern)
    return True


def resolve_symlink_chain(home: str, rel_path: str) -> Tuple[Optional[str], Optional[str]]:
    """Follow symlinks from a home-relative path.

    Returns (resolved_abs, resolved_home_rel) or (None, None) if broken or cyclic.
    """
    visited: Set[str] = set()
    current_abs = os.path.join(home, rel_path)
    depth = 0

    while os.path.islink(current_abs):
        if current_abs in visited or depth >= SYMLINK_MAX_DEPTH:
            return None, None
        visited.add(current_abs)
        link_target = os.readlink(current_abs)
        if os.path.isabs(link_target):
            current_abs = link_target
        else:
            current_abs = os.path.normpath(
                os.path.join(os.path.dirname(current_abs), link_target)
            )
        depth += 1

    if not os.path.exists(current_abs):
        return None, None

    return current_abs, normalize_home_rel(home, current_abs)


def mirror_repo_path(category: str, home_rel: str) -> str:
    return os.path.join(category, home_rel)


def external_materialized_path(home_rel: str, basename: str) -> str:
    material_id = hashlib.sha256(home_rel.encode()).hexdigest()[:16]
    return os.path.join(MATERIALIZED_DIR, material_id, basename)


def _copy_content_to_repo(abs_source: str, dest: str) -> None:
    if os.path.isfile(abs_source):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(abs_source, dest)
    elif os.path.isdir(abs_source):
        if os.path.exists(dest):
            shutil.rmtree(dest)
        shutil.copytree(abs_source, dest)


def _canonical_repo_path(
    home_rel: str,
    resolved_rel: str,
    resolved_abs: str,
    category: str,
    tree_pattern: str,
    watched_paths: Dict[str, dict],
) -> str:
    if resolved_rel in watched_paths and watched_paths[resolved_rel].get('kind') != 'symlink':
        return mirror_repo_path(category, resolved_rel)
    if is_internal_target(resolved_rel, tree_pattern):
        return mirror_repo_path(category, resolved_rel)
    basename = os.path.basename(resolved_abs) or 'content'
    return external_materialized_path(home_rel, basename)


def materialize_symlinks(
    home: str,
    repo: str,
    watched_paths: Dict[str, dict],
    category: str,
    tree_pattern: str,
    warnings: Optional[List[str]] = None,
    dotsync_repo: Optional[str] = None,
) -> List[dict]:
    """Materialize symlink targets into the repo and write the sidecar manifest."""
    if warnings is None:
        warnings = []
    if dotsync_repo is None:
        dotsync_repo = repo

    entries = []
    copied: Set[str] = set()

    for home_rel in sorted(watched_paths):
        info = watched_paths[home_rel]
        if info.get('kind') != 'symlink':
            continue

        abs_link = os.path.join(home, home_rel)
        if not os.path.islink(abs_link):
            continue

        target_str = os.readlink(abs_link)
        resolved_abs, resolved_rel = resolve_symlink_chain(home, home_rel)
        if resolved_abs is None:
            msg = f'broken symlink at {home_rel} -> {target_str}, skipping'
            logging.warning(msg)
            warnings.append(msg)
            continue

        canonical = _canonical_repo_path(
            home_rel, resolved_rel, resolved_abs, category, tree_pattern, watched_paths
        )
        if canonical not in copied:
            if canonical.startswith('.dotsync/'):
                dest = os.path.join(dotsync_repo, canonical)
            else:
                dest = os.path.join(repo, canonical)
            _copy_content_to_repo(resolved_abs, dest)
            copied.add(canonical)

        entries.append({
            'home_path': home_rel,
            'kind': 'symlink',
            'target': target_str,
            'canonical_repo_path': canonical,
        })

    write_manifest(dotsync_repo, category, entries)
    return entries


def expand_trees_from_repo(plugin_dir: str, trees: List[dict], categories) -> Dict[str, dict]:
    """Build active tree file entries from repo mirror paths (for restore)."""
    files = {}
    for tree in trees:
        if not set(categories) & set(tree['categories']):
            continue

        master = min(tree['categories'])
        pattern = tree['pattern']
        walk_root = pattern_walk_root(pattern)
        category_root = os.path.join(plugin_dir, master, walk_root)

        if not os.path.exists(category_root):
            continue

        has_glob = pattern_has_glob(pattern)

        if os.path.isfile(category_root) or os.path.islink(category_root):
            rel = os.path.relpath(category_root, os.path.join(plugin_dir, master))
            if not rel.startswith('.'):
                rel = '.' + rel
            if has_glob and not fnmatch.fnmatch(rel, pattern):
                continue
            if not has_glob and rel != pattern:
                continue
            files[rel] = {
                'categories': tree['categories'],
                'plugin': tree['plugin'],
                'kind': 'file',
            }
            continue

        for root, dirs, fnames in os.walk(category_root):
            dirs[:] = [d for d in dirs if d not in DIR_SKIP]
            for fname in fnames:
                if fname in SYSTEM_FILES:
                    continue
                abs_f = os.path.join(root, fname)
                rel = os.path.relpath(abs_f, os.path.join(plugin_dir, master))
                if not rel.startswith('.'):
                    rel = '.' + rel

                if has_glob:
                    if not fnmatch.fnmatch(rel, pattern):
                        continue
                elif rel != pattern and not rel.startswith(pattern + '/'):
                    continue

                if rel in files:
                    continue
                files[rel] = {
                    'categories': tree['categories'],
                    'plugin': tree['plugin'],
                    'kind': 'file',
                }

    return files


def restore_symlinks(
    home: str,
    plugin_dir: str,
    dotsync_repo: str,
    categories: List[str],
    plugin,
    policy,
    dry_run: bool = False,
):
    """Restore symlink layout from sidecar manifests."""
    from dotsync.calc_ops import RestoreAborted
    from dotsync.interaction import prompt_restore_overwrite_or_cancel, show_restore_diff

    for category in categories:
        entries = read_manifest(dotsync_repo, category)
        for entry in entries:
            home_path = entry['home_path']
            target = entry['target']
            canonical = entry['canonical_repo_path']
            if canonical.startswith('.dotsync/'):
                source = os.path.join(dotsync_repo, canonical)
            else:
                source = os.path.join(plugin_dir, canonical)
            dest = os.path.join(home, home_path)

            if not os.path.exists(source):
                logging.warning(f'symlink source missing in repo: {source}, skipping')
                continue

            dest_dir = os.path.dirname(dest)
            if dest_dir and not os.path.exists(dest_dir):
                os.makedirs(dest_dir, exist_ok=True)

            if os.path.isabs(target):
                recreate_link = False
            else:
                target_abs = os.path.normpath(os.path.join(os.path.dirname(dest), target))
                recreate_link = os.path.exists(target_abs)

            if recreate_link:
                if dry_run:
                    logging.info(f'[DRY RUN] Would recreate symlink {dest} -> {target}')
                    continue
                if os.path.lexists(dest):
                    if os.path.exists(dest) and not os.path.islink(dest):
                        if policy and policy.non_interactive:
                            if policy.conflict != 'overwrite':
                                raise RestoreAborted(
                                    f'Restore aborted: {dest} conflicts with repository'
                                )
                        else:
                            show_restore_diff(source, dest)
                            if not prompt_restore_overwrite_or_cancel(dest):
                                raise RestoreAborted(f'Restore cancelled by user at {dest}')
                    os.remove(dest)
                os.symlink(target, dest)
                logging.info(f'Recreated symlink {home_path} -> {target}')
                continue

            if dry_run:
                logging.info(f'[DRY RUN] Would copy symlink content {source} -> {dest}')
                continue

            if os.path.lexists(dest):
                try:
                    if plugin.samefile(source, dest):
                        continue
                except Exception:
                    pass
                if policy and policy.non_interactive:
                    if policy.conflict == 'overwrite':
                        os.remove(dest)
                    elif policy.conflict == 'keep':
                        continue
                    else:
                        raise RestoreAborted(
                            f'Restore aborted: {dest} conflicts with repository'
                        )
                else:
                    show_restore_diff(source, dest)
                    if prompt_restore_overwrite_or_cancel(dest):
                        os.remove(dest)
                    else:
                        raise RestoreAborted(f'Restore cancelled by user at {dest}')

            plugin.remove(source, dest)
            logging.info(f'Restored symlink content to {home_path}')


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
