import os

import pytest

from dotsync.flists import Filelist
from dotsync.manifest import read_manifest
from dotsync.tree import materialize_symlinks


def make_home(tmp_path):
    home = os.path.join(tmp_path, 'home')
    os.makedirs(home)
    return home


def make_repo(tmp_path):
    repo = os.path.join(tmp_path, 'repo')
    os.makedirs(repo)
    return repo


def write_flist(tmp_path, content):
    fname = os.path.join(tmp_path, 'filelist')
    with open(fname, 'w') as f:
        f.write(content)
    return fname


def test_save_materializes_symlink_target_bytes(tmp_path):
    home = make_home(tmp_path)
    repo = make_repo(tmp_path)
    app = os.path.join(home, '.config', 'app')
    os.makedirs(app)
    with open(os.path.join(app, 'real.txt'), 'w') as f:
        f.write('hello')
    os.symlink('real.txt', os.path.join(app, 'link.txt'))

    fname = write_flist(tmp_path, '@tree:.config/app:editor\n')
    fl = Filelist(fname)
    watched = fl.expand_trees(home, ['editor'])

    entries = materialize_symlinks(
        home, repo, watched, 'editor', '.config/app'
    )

    canonical = os.path.join(repo, 'editor', '.config', 'app', 'real.txt')
    assert os.path.isfile(canonical)
    with open(canonical) as f:
        assert f.read() == 'hello'

    assert len(entries) == 1
    assert entries[0] == {
        'home_path': '.config/app/link.txt',
        'kind': 'symlink',
        'target': 'real.txt',
        'canonical_repo_path': 'editor/.config/app/real.txt',
    }

    manifest = read_manifest(repo, 'editor')
    assert manifest == entries


def test_dedup_when_link_target_also_watched(tmp_path):
    home = make_home(tmp_path)
    repo = make_repo(tmp_path)
    app = os.path.join(home, '.config', 'app')
    os.makedirs(app)
    with open(os.path.join(app, 'real.txt'), 'w') as f:
        f.write('shared')
    os.symlink('real.txt', os.path.join(app, 'link.txt'))

    fname = write_flist(tmp_path, '@tree:.config/app:editor\n')
    fl = Filelist(fname)
    watched = fl.expand_trees(home, ['editor'])

    assert '.config/app/real.txt' in watched
    assert '.config/app/link.txt' in watched

    entries = materialize_symlinks(
        home, repo, watched, 'editor', '.config/app'
    )

    canonical = os.path.join(repo, 'editor', '.config', 'app', 'real.txt')
    assert os.path.isfile(canonical)
    link_mirror = os.path.join(repo, 'editor', '.config', 'app', 'link.txt')
    assert not os.path.exists(link_mirror)

    assert len(entries) == 1
    assert entries[0]['home_path'] == '.config/app/link.txt'
    assert entries[0]['canonical_repo_path'] == 'editor/.config/app/real.txt'


def test_broken_symlink_warn_skip(tmp_path, caplog):
    home = make_home(tmp_path)
    repo = make_repo(tmp_path)
    app = os.path.join(home, '.config', 'app')
    os.makedirs(app)
    os.symlink('missing.txt', os.path.join(app, 'broken.txt'))

    fname = write_flist(tmp_path, '@tree:.config/app:editor\n')
    fl = Filelist(fname)
    watched = fl.expand_trees(home, ['editor'])

    warnings = []
    with caplog.at_level('WARNING'):
        entries = materialize_symlinks(
            home, repo, watched, 'editor', '.config/app', warnings=warnings
        )

    assert entries == []
    assert read_manifest(repo, 'editor') == []
    assert not os.path.exists(os.path.join(repo, 'editor'))
    assert len(warnings) == 1
    assert 'broken symlink' in warnings[0]
    assert '.config/app/broken.txt' in warnings[0]
    assert any('broken symlink' in r.message for r in caplog.records)


def test_external_target_to_dotsync_materialized(tmp_path):
    home = make_home(tmp_path)
    repo = make_repo(tmp_path)
    external = os.path.join(tmp_path, 'external')
    os.makedirs(external)
    with open(os.path.join(external, 'secret.cfg'), 'w') as f:
        f.write('external-data')

    app = os.path.join(home, '.config', 'app')
    os.makedirs(app)
    os.symlink(os.path.join(external, 'secret.cfg'), os.path.join(app, 'link.cfg'))

    fname = write_flist(tmp_path, '@tree:.config/app:tools\n')
    fl = Filelist(fname)
    watched = fl.expand_trees(home, ['tools'])

    entries = materialize_symlinks(
        home, repo, watched, 'tools', '.config/app'
    )

    assert len(entries) == 1
    canonical = entries[0]['canonical_repo_path']
    assert canonical.startswith('.dotsync/materialized/')
    assert canonical.endswith('/secret.cfg')
    assert not canonical.startswith('tools/')

    materialized = os.path.join(repo, canonical)
    assert os.path.isfile(materialized)
    with open(materialized) as f:
        assert f.read() == 'external-data'

    assert entries[0] == {
        'home_path': '.config/app/link.cfg',
        'kind': 'symlink',
        'target': os.path.join(external, 'secret.cfg'),
        'canonical_repo_path': canonical,
    }
