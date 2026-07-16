import os
import subprocess

import pytest

from dotsync.__main__ import main
from dotsync.git import Git


def create_published_remote(tmp_path, flist, home_files, categories=None):
    """Create a bare remote with dotfiles content pushed from a source repo."""
    bare = tmp_path / 'remote.git'
    subprocess.run(['git', 'init', '--bare', str(bare)], check=True)

    work = tmp_path / 'work'
    source_home = tmp_path / 'source_home'
    os.makedirs(source_home)
    os.makedirs(work)
    main(args=['init'], cwd=str(work), home=str(source_home))
    with open(work / 'filelist', 'w') as f:
        f.write(flist)
    git = Git(str(work))
    git.add('filelist')
    git.commit('add filelist')

    for rel, content in home_files.items():
        path = source_home / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    update_cats = categories or ['shell', 'vim']
    assert main(args=['update'] + update_cats, cwd=str(work), home=str(source_home)) == 0
    if git.has_changes():
        git.add()
        git.commit('mirror dotfiles')

    subprocess.run(['git', 'remote', 'add', 'origin', str(bare)], cwd=str(work), check=True)
    branch = subprocess.run(
        ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
        cwd=str(work),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    subprocess.run(['git', 'push', '-u', 'origin', branch], cwd=str(work), check=True)
    return bare, source_home


def remote_url(path):
    return f'file://{path.resolve()}'


class TestRestoreWizard:
    def test_restore_wizard_interactive(self, tmp_path, monkeypatch, capsys):
        flist = '.zshrc:shell\n.vimrc:vim\n'
        bare, _ = create_published_remote(
            tmp_path,
            flist,
            {'.zshrc': 'zsh config', '.vimrc': 'vim config'},
        )

        home = tmp_path / 'home'
        os.makedirs(home)
        inputs = iter([
            remote_url(bare),
            '1',
            'y',
        ])
        monkeypatch.setattr('builtins.input', lambda p=None: next(inputs))

        dotfiles = home / '.dotfiles'
        assert not dotfiles.exists()

        assert main(args=['restore'], cwd=str(home), home=str(home)) == 0

        captured = capsys.readouterr()
        assert 'Available categories' in captured.out
        assert 'Restore summary' in captured.out
        assert dotfiles.is_dir()
        assert (home / '.zshrc').read_text() == 'zsh config'
        assert not (home / '.vimrc').exists()

    def test_restore_wizard_non_interactive(self, tmp_path):
        flist = '.zshrc:shell\n.vimrc:vim\n'
        bare, _ = create_published_remote(
            tmp_path,
            flist,
            {'.zshrc': 'zsh config', '.vimrc': 'vim config'},
        )

        home = tmp_path / 'home'
        os.makedirs(home)

        def fail_input(_prompt):
            raise AssertionError('input called in non-interactive restore wizard')

        import builtins
        orig = builtins.input
        builtins.input = fail_input
        try:
            assert main(
                args=[
                    'restore',
                    '--remote', remote_url(bare),
                    '--categories', 'shell,vim',
                    '--yes',
                    '--conflict', 'overwrite',
                ],
                cwd=str(home),
                home=str(home),
            ) == 0
        finally:
            builtins.input = orig

        assert (home / '.zshrc').read_text() == 'zsh config'
        assert (home / '.vimrc').read_text() == 'vim config'

    def test_restore_wizard_declined_url_aborts(self, tmp_path, monkeypatch, caplog):
        home = tmp_path / 'home'
        os.makedirs(home)
        monkeypatch.setattr('builtins.input', lambda p=None: '')

        assert main(args=['restore'], cwd=str(home), home=str(home)) == 1
        assert not (home / '.dotfiles').exists()
        assert 'aborted: no remote url' in caplog.text.lower()

    def test_restore_wizard_conflict_overwrite(self, tmp_path, monkeypatch):
        flist = '.zshrc:shell\n'
        bare, _ = create_published_remote(
            tmp_path,
            flist,
            {'.zshrc': 'repo zsh'},
            categories=['shell'],
        )

        home = tmp_path / 'home'
        os.makedirs(home)
        (home / '.zshrc').write_text('home zsh')

        inputs = iter([
            remote_url(bare),
            'shell',
            'y',
            'o',
        ])
        monkeypatch.setattr('builtins.input', lambda p=None: next(inputs))

        assert main(args=['restore'], cwd=str(home), home=str(home)) == 0
        assert (home / '.zshrc').read_text() == 'repo zsh'

    def test_restore_wizard_non_interactive_requires_remote(self, tmp_path, caplog):
        home = tmp_path / 'home'
        os.makedirs(home)

        assert main(
            args=['restore', '--categories', 'shell', '--yes'],
            cwd=str(home),
            home=str(home),
        ) == 1
        assert '--remote is required' in caplog.text

    def test_restore_wizard_non_interactive_requires_categories(self, tmp_path, caplog):
        home = tmp_path / 'home'
        os.makedirs(home)

        assert main(
            args=['restore', '--remote', 'file:///tmp/nope', '--yes'],
            cwd=str(home),
            home=str(home),
        ) == 1
        assert '--categories is required' in caplog.text

    def test_restore_wizard_clone_and_pull(self, tmp_path, monkeypatch, capsys):
        flist = '.zshrc:shell\n'
        bare, _ = create_published_remote(
            tmp_path,
            flist,
            {'.zshrc': 'zsh config'},
            categories=['shell'],
        )

        home = tmp_path / 'home'
        os.makedirs(home)

        pull_calls = []
        orig_pull = Git.pull_ff_only

        def track_pull(self):
            pull_calls.append(True)
            return orig_pull(self)

        monkeypatch.setattr(Git, 'pull_ff_only', track_pull)
        monkeypatch.setattr(
            'builtins.input',
            lambda p=None: remote_url(bare) if 'URL' in (p or '') else 'y',
        )

        assert main(
            args=['restore', '--categories', 'shell'],
            cwd=str(home),
            home=str(home),
        ) == 0

        captured = capsys.readouterr()
        assert pull_calls
        assert 'Restoring from commit' in captured.out
        assert (home / '.zshrc').read_text() == 'zsh config'
