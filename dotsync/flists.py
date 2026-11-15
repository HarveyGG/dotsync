import logging
import os
from dataclasses import asdict
from typing import List, Optional, Tuple

import dotsync.info as info
from dotsync.tree import (
    TreeEntry,
    expand_trees_from_repo,
    pattern_has_glob,
    pattern_walk_root,
    walk_tree,
)


def _parse_entry_line(line: str) -> Tuple[str, str, bool]:
    if ':' in line:
        path, tail = line.split(':', 1)
        return path, tail, True
    if '|' in line:
        path, tail = line.split('|', 1)
        return path, '|' + tail, False
    return line, '', False


def _parse_tail(
    tail: str,
    has_categories: bool,
) -> Tuple[List[str], str, Optional[int], Optional[str]]:
    categories = ['common']
    plugin = 'plain'
    min_bytes: Optional[int] = None
    guard: Optional[str] = None

    if not tail:
        return categories, plugin, min_bytes, guard

    parts = tail.split('|')
    mod_start = 0
    if has_categories and parts and parts[0] != '':
        categories = parts[0].split(',')
        mod_start = 1
    elif not has_categories and tail.startswith('|'):
        parts = [p for p in tail.split('|') if p != '']

    for tok in parts[mod_start:]:
        if not tok:
            continue
        if tok == 'encrypt':
            plugin = 'encrypt'
        elif tok.startswith('min-bytes='):
            raw = tok.split('=', 1)[1]
            try:
                value = int(raw)
            except ValueError:
                _invalid_modifier(tok)
            if value <= 0:
                _invalid_modifier(tok)
            min_bytes = value
        elif tok.startswith('guard='):
            guard_name = tok.split('=', 1)[1]
            if guard_name != 'nonempty':
                _invalid_modifier(tok)
            guard = 'nonempty'
        else:
            _invalid_modifier(tok)

    return categories, plugin, min_bytes, guard


def _invalid_modifier(tok: str) -> None:
    message = f'Invalid filelist modifier: {tok}'
    logging.error(message)
    raise ValueError(message)


def _filelist_entry(
    categories: List[str],
    plugin: str,
    min_bytes: Optional[int],
    guard: Optional[str],
) -> dict:
    data = {'categories': categories, 'plugin': plugin}
    if min_bytes is not None:
        data['min_bytes'] = min_bytes
    if guard is not None:
        data['guard'] = guard
    return data


class Filelist:
    def __init__(self, fname):
        self.groups = {}
        self.files = {}
        self.trees = []

        logging.debug(f'parsing filelist in {fname}')

        with open(fname, 'r') as f:
            for line in f.readlines():
                line = line.strip()

                if not line or line.startswith('#'):
                    continue

                if line.startswith('@tree:'):
                    self._parse_tree_line(line[len('@tree:'):])
                    continue

                # group (not pipe modifiers like |min-bytes=N or |guard=nonempty)
                if (
                    '=' in line
                    and ':' not in line
                    and '|' not in line
                    and not line.startswith('.')
                    and not line.startswith('@')
                ):
                    group, categories = line.split('=', 1)
                    categories = categories.split(',')
                    if group == info.hostname:
                        categories.append(info.hostname)
                    self.groups[group] = categories
                # file
                else:
                    path, tail, has_cats = _parse_entry_line(line)
                    categories, plugin, min_bytes, guard = _parse_tail(tail, has_cats)
                    if path not in self.files:
                        self.files[path] = []
                    self.files[path].append(
                        _filelist_entry(categories, plugin, min_bytes, guard)
                    )

    def _parse_tree_line(self, line):
        pattern, tail, has_cats = _parse_entry_line(line)
        categories, plugin, min_bytes, guard = _parse_tail(tail, has_cats)
        tree_kwargs = {
            'pattern': pattern,
            'categories': categories,
            'plugin': plugin,
        }
        if min_bytes is not None:
            tree_kwargs['min_bytes'] = min_bytes
        if guard is not None:
            tree_kwargs['guard'] = guard
        tree_dict = asdict(TreeEntry(**tree_kwargs))
        for optional in ('min_bytes', 'guard'):
            if tree_dict.get(optional) is None:
                tree_dict.pop(optional, None)
        self.trees.append(tree_dict)

    def activate(self, categories):
        # expand groups
        categories = [self.groups.get(c, [c]) for c in categories]
        # flatten category list
        categories = [c for cat in categories for c in cat]

        files = {}
        for path in self.files:
            for group in self.files[path]:
                cat_list = group['categories']
                if set(categories) & set(cat_list):
                    if path in files:
                        logging.error('multiple category lists active for '
                                      f'{path}: {files[path]["categories"]} '
                                      f'and {cat_list}')
                        raise RuntimeError
                    else:
                        files[path] = group

        return files

    def expand_trees(self, home, categories):
        categories = [self.groups.get(c, [c]) for c in categories]
        categories = [c for cat in categories for c in cat]

        files = {}
        for tree in self.trees:
            if not set(categories) & set(tree['categories']):
                continue

            for path, node in walk_tree(home, tree['pattern']).items():
                if path in files:
                    logging.error('multiple tree entries active for '
                                  f'{path}: {files[path]["categories"]} '
                                  f'and {tree["categories"]}')
                    raise RuntimeError
                entry = {
                    'categories': tree['categories'],
                    'plugin': tree['plugin'],
                    'kind': node['kind'],
                }
                if 'min_bytes' in tree:
                    entry['min_bytes'] = tree['min_bytes']
                if 'guard' in tree:
                    entry['guard'] = tree['guard']
                files[path] = entry

        return files

    def _flatten_categories(self, categories):
        expanded = [self.groups.get(c, [c]) for c in categories]
        return [c for cat in expanded for c in cat]

    def merge_active(self, home, categories, plugin_dir=None, from_repo=False):
        """Merge atomic active files with tree entries from home or repo."""
        files = self.activate(categories)
        if from_repo:
            if plugin_dir is None:
                raise ValueError('plugin_dir is required when from_repo=True')
            trees = expand_trees_from_repo(plugin_dir, self.trees, categories)
        else:
            trees = self.expand_trees(home, categories)

        for path, tree_info in trees.items():
            if path in files:
                logging.error('path active as both atomic file and tree entry: '
                              f'{path}')
                raise RuntimeError
            files[path] = tree_info

        return files

    def build_save_manifest(self, home, categories, symlink_canonicals=None):
        """Manifest of allowed repo paths including expanded trees."""
        manifest = self.manifest()
        tree_files = self.expand_trees(home, categories)

        for path, tree_info in tree_files.items():
            if tree_info.get('kind') == 'symlink':
                continue
            plugin = tree_info['plugin']
            for category in self._expand_category_names(tree_info['categories']):
                manifest.setdefault(plugin, []).append(os.path.join(category, path))

        if symlink_canonicals:
            for plugin, paths in symlink_canonicals.items():
                manifest.setdefault(plugin, []).extend(paths)

        return manifest

    def _expand_category_names(self, category_names):
        expanded = []
        for category in category_names:
            if category in self.groups:
                expanded.extend(self.groups[category])
            else:
                expanded.append(category)
        return expanded

    def find_tree_for_path(self, normalized_path):
        """Return tree entry whose pattern matches normalized_path, if any."""
        for tree in self.trees:
            pattern = tree['pattern']
            walk_root = pattern_walk_root(pattern)
            if walk_root and not (
                normalized_path == walk_root
                or normalized_path.startswith(walk_root + '/')
            ):
                continue
            if pattern_has_glob(pattern):
                import fnmatch
                if fnmatch.fnmatch(normalized_path, pattern):
                    return tree
                if fnmatch.fnmatch(normalized_path + '/', pattern + '/*'):
                    return tree
            elif normalized_path == pattern or normalized_path.startswith(pattern + '/'):
                return tree
        return None

    def build_restore_manifest(self, plugin_dirs, categories, dotsync_repo):
        """Manifest of allowed repo paths for restore/clean after pull."""
        from dotsync.manifest import read_manifest

        manifest = self.manifest()
        active_cats = self._flatten_categories(categories)

        for plugin_name, plugin_dir in plugin_dirs.items():
            tree_files = expand_trees_from_repo(plugin_dir, self.trees, active_cats)
            for path, tree_info in tree_files.items():
                if tree_info['plugin'] != plugin_name:
                    continue
                for category in self._expand_category_names(tree_info['categories']):
                    manifest.setdefault(plugin_name, []).append(
                        os.path.join(category, path)
                    )

        for category in active_cats:
            for entry in read_manifest(dotsync_repo, category):
                manifest.setdefault('plain', []).append(entry['canonical_repo_path'])

        return manifest

    # generates a list of all the filenames in each plugin for later use when
    # cleaning the repo
    def manifest(self):
        manifest = {}

        for path in self.files:
            for instance in self.files[path]:
                plugin = instance['plugin']
                for category in instance['categories']:
                    if category in self.groups:
                        categories = self.groups[category]
                    else:
                        categories = [category]

                    if plugin not in manifest:
                        manifest[plugin] = []

                    for category in categories:
                        manifest[plugin].append(os.path.join(category, path))

        return manifest
