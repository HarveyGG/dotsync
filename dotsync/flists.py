import logging
import os
import re
from dataclasses import asdict

import dotsync.info as info
from dotsync.tree import (
    TreeEntry,
    expand_trees_from_repo,
    pattern_has_glob,
    pattern_walk_root,
    walk_tree,
)


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

                # group
                if '=' in line:
                    group, categories = line.split('=')
                    categories = categories.split(',')
                    if group == info.hostname:
                        categories.append(info.hostname)
                    self.groups[group] = categories
                # file
                else:
                    split = re.split('[:|]', line)

                    path, categories, plugin = split[0], ['common'], 'plain'
                    if len(split) >= 2:
                        if ':' in line:
                            categories = split[1].split(',')
                        else:
                            plugin = split[1]
                    if len(split) >= 3:
                        plugin = split[2]

                    if path not in self.files:
                        self.files[path] = []
                    self.files[path].append({
                        'categories': categories,
                        'plugin': plugin
                    })

    def _parse_tree_line(self, line):
        split = re.split('[:|]', line)

        pattern, categories, plugin = split[0], ['common'], 'plain'
        if len(split) >= 2:
            if ':' in line:
                categories = split[1].split(',')
            else:
                plugin = split[1]
        if len(split) >= 3:
            plugin = split[2]

        self.trees.append(asdict(TreeEntry(
            pattern=pattern,
            categories=categories,
            plugin=plugin,
        )))

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
                files[path] = {
                    'categories': tree['categories'],
                    'plugin': tree['plugin'],
                    'kind': node['kind'],
                }

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

        for path, info in trees.items():
            if path in files:
                logging.error('path active as both atomic file and tree entry: '
                              f'{path}')
                raise RuntimeError
            files[path] = info

        return files

    def build_save_manifest(self, home, categories, symlink_canonicals=None):
        """Manifest of allowed repo paths including expanded trees."""
        manifest = self.manifest()
        tree_files = self.expand_trees(home, categories)

        for path, info in tree_files.items():
            if info.get('kind') == 'symlink':
                continue
            plugin = info['plugin']
            for category in self._expand_category_names(info['categories']):
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
            for path, info in tree_files.items():
                if info['plugin'] != plugin_name:
                    continue
                for category in self._expand_category_names(info['categories']):
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
