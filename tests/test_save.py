import logging
import os
import subprocess

from dotsync.__main__ import main, update_files
from dotsync.git import Git


def setup_repo(tmp_path, flist='.file:common'):
    home = tmp_path / 'home'
    repo = tmp_path / 'repo'
    os.makedirs(home)
    os.makedirs(repo)
    main(args=['init'], cwd=str(repo), home=str(home))
    with open(repo / 'filelist', 'w') as f:
        f.write(flist)
    return home, repo


def test_save_mirrors_commits_and_pushes_by_default(monkeypatch, tmp_path):
    home, repo = setup_repo(tmp_path)
    (home / '.file').write_text('content')

    calls = []

    orig_commit = Git.commit
    orig_push = Git.push

    def track_update(*args, **kwargs):
        calls.append('mirror')
        return update_files(*args, **kwargs)

    def track_commit(self, message=None):
        calls.append('commit')
        return orig_commit(self, message)

    def track_push(self):
        calls.append('push')
        return orig_push(self)

    monkeypatch.setattr('dotsync.__main__.update_files', track_update)
    monkeypatch.setattr(Git, 'commit', track_commit)
    monkeypatch.setattr(Git, 'push', track_push)
    subprocess.run(['git', 'remote', 'add', 'origin', str(repo)], cwd=str(repo), check=True)

    assert main(args=['save'], cwd=str(repo), home=str(home)) == 0
    assert calls == ['mirror', 'commit', 'push']
    assert (repo / 'dotfiles' / 'plain' / 'common' / '.file').read_text() == 'content'


def test_save_no_push_skips_push_with_warning(caplog, tmp_path, monkeypatch):
    home, repo = setup_repo(tmp_path)
    (home / '.file').write_text('content')

    push_called = []
    orig_push = Git.push

    def track_push(self):
        push_called.append(True)
        return orig_push(self)

    monkeypatch.setattr(Git, 'push', track_push)

    with caplog.at_level(logging.WARNING):
        assert main(args=['save', '--no-push'], cwd=str(repo), home=str(home)) == 0

    assert not push_called
    assert 'not durable' in caplog.text.lower()


def test_save_custom_message(tmp_path):
    home, repo = setup_repo(tmp_path)
    bare = tmp_path / 'bare.git'
    subprocess.run(['git', 'init', '--bare', str(bare)], check=True)
    subprocess.run(['git', 'remote', 'add', 'origin', str(bare)], cwd=str(repo), check=True)
    (home / '.file').write_text('content')

    assert main(args=['save', '-m', 'sync dotfiles'], cwd=str(repo), home=str(home)) == 0
    git = Git(str(repo))
    assert git.last_commit() == 'sync dotfiles'


def test_save_dry_run_no_commit(tmp_path):
    home, repo = setup_repo(tmp_path)
    (home / '.file').write_text('content')
    git = Git(str(repo))
    initial_commit = git.last_commit()

    assert main(args=['save', '--dry-run'], cwd=str(repo), home=str(home)) == 0
    assert git.last_commit() == initial_commit
    assert not (repo / 'dotfiles' / 'plain' / 'common' / '.file').exists()


def test_save_missing_remote_declined_aborts(monkeypatch, tmp_path, caplog):
    home, repo = setup_repo(tmp_path)
    (home / '.file').write_text('content')
    monkeypatch.setattr('builtins.input', lambda p: '')

    assert main(args=['save'], cwd=str(repo), home=str(home)) == 1
    assert 'Aborted' in caplog.text


def test_save_missing_remote_prompt_adds_and_pushes(monkeypatch, tmp_path):
    home, repo = setup_repo(tmp_path)
    bare = tmp_path / 'bare.git'
    subprocess.run(['git', 'init', '--bare', str(bare)], check=True)
    (home / '.file').write_text('content')

    monkeypatch.setattr('builtins.input', lambda p: str(bare))

    assert main(args=['save'], cwd=str(repo), home=str(home)) == 0
    git = Git(str(repo))
    assert git.has_remote()
    result = subprocess.run(
        ['git', 'ls-remote', 'origin'],
        cwd=str(repo),
        stdout=subprocess.PIPE,
        check=True,
    )
    assert result.stdout.strip()


def test_save_push_failure_exits_nonzero(monkeypatch, tmp_path, caplog):
    home, repo = setup_repo(tmp_path)
    (home / '.file').write_text('content')
    subprocess.run(['git', 'remote', 'add', 'origin', str(repo)], cwd=str(repo), check=True)

    def fail_push(self):
        raise subprocess.CalledProcessError(1, 'git push', output=b'push rejected')

    monkeypatch.setattr(Git, 'push', fail_push)

    assert main(args=['save'], cwd=str(repo), home=str(home)) == 1
    assert 'Failed to push' in caplog.text
