import logging
import os
import re
from dataclasses import asdict

import dotsync.info as info
from dotsync.tree import TreeEntry, walk_tree


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
