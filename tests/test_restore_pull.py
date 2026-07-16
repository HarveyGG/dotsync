import os
import subprocess

import pytest

from dotsync.__main__ import main
from dotsync.git import Git, GitPullError


def setup_repo(tmp_path, flist='.file:common'):
    home = tmp_path / 'home'
    repo = tmp_path / 'repo'
    os.makedirs(home)
    os.makedirs(repo)
    main(args=['init'], cwd=str(repo), home=str(home))
    with open(repo / 'filelist', 'w') as f:
        f.write(flist)
    return home, repo


def test_restore_calls_pull_before_copy(monkeypatch, tmp_path):
    home, repo = setup_repo(tmp_path)
    open(home / '.file', 'w').write('content')
    assert main(args=['update'], cwd=str(repo), home=str(home)) == 0
    subprocess.run(['git', 'remote', 'add', 'origin', str(repo)], cwd=str(repo), check=True)

    order = []
    git = Git(str(repo))
    expected_sha = git.head_sha()

    def track_pull(self):
        order.append('pull')
        return expected_sha

    from dotsync.plugins.plain import PlainPlugin
    original_remove = PlainPlugin.remove

    def track_copy(self, source, dest):
        order.append('copy')
        return original_remove(self, source, dest)

    monkeypatch.setattr(Git, 'pull_ff_only', track_pull)
    monkeypatch.setattr(PlainPlugin, 'remove', track_copy)

    assert main(args=['restore'], cwd=str(repo), home=str(home)) == 0
    assert 'pull' in order
    assert 'copy' in order
    assert order.index('pull') < order.index('copy')


def test_restore_prints_commit_sha(capsys, tmp_path):
    home, repo = setup_repo(tmp_path)
    open(home / '.file', 'w').write('content')
    assert main(args=['update'], cwd=str(repo), home=str(home)) == 0

    git = Git(str(repo))
    expected_sha = git.head_sha()

    assert main(args=['restore'], cwd=str(repo), home=str(home)) == 0
    captured = capsys.readouterr()
    assert f'Restoring from commit {expected_sha}' in captured.out


def test_restore_skip_pull_skips_fetch(monkeypatch, tmp_path):
    home, repo = setup_repo(tmp_path)
    open(home / '.file', 'w').write('content')
    assert main(args=['update'], cwd=str(repo), home=str(home)) == 0

    pull_called = []

    def track_pull(self):
        pull_called.append(True)
        return self.head_sha()

    monkeypatch.setattr(Git, 'pull_ff_only', track_pull)

    assert main(args=['restore', '--skip-pull'], cwd=str(repo), home=str(home)) == 0
    assert not pull_called


def test_restore_pull_failure_aborts(monkeypatch, tmp_path, caplog):
    home, repo = setup_repo(tmp_path)
    open(home / '.file', 'w').write('content')
    assert main(args=['update'], cwd=str(repo), home=str(home)) == 0

    subprocess.run(['git', 'remote', 'add', 'origin', str(repo)], cwd=str(repo), check=True)

    def fail_pull(self):
        raise GitPullError('fatal: Not possible to fast-forward')

    monkeypatch.setattr(Git, 'pull_ff_only', fail_pull)

    assert not (home / '.file').exists()
    assert main(args=['restore'], cwd=str(repo), home=str(home)) == 1
    assert not (home / '.file').exists()
    assert 'Failed to pull latest changes' in caplog.text


def test_restore_no_remote_uses_local_head(tmp_path, capsys):
    home, repo = setup_repo(tmp_path)
    open(home / '.file', 'w').write('content')
    assert main(args=['update'], cwd=str(repo), home=str(home)) == 0

    git = Git(str(repo))
    expected_sha = git.head_sha()

    assert main(args=['restore'], cwd=str(repo), home=str(home)) == 0
    captured = capsys.readouterr()
    assert f'Restoring from commit {expected_sha}' in captured.out
    assert (home / '.file').is_file()
