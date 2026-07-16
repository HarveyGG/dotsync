import json
import os

MANIFESTS_DIR = '.dotsync/manifests'
MATERIALIZED_DIR = '.dotsync/materialized'


def manifest_path(repo, category):
    return os.path.join(repo, MANIFESTS_DIR, f'{category}.json')


def read_manifest(repo, category):
    path = manifest_path(repo, category)
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def write_manifest(repo, category, entries):
    path = manifest_path(repo, category)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(entries, f, indent=2)
        f.write('\n')
