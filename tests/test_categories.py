import os
import socket

from dotsync.__main__ import main


class TestCategories:
    def setup_repo(self, tmp_path, flist):
        home = tmp_path / 'home'
        repo = tmp_path / 'repo'
        os.makedirs(home)
        os.makedirs(repo)
        main(args=['init'], cwd=str(repo))
        with open(repo / 'filelist', 'w') as f:
            f.write(flist)
        return home, repo

    def test_categories_lists_groups_and_categories(self, tmp_path, capsys):
        flist = (
            'laptop=vim,shell\n'
            '.zshrc:shell\n'
            '.vimrc:vim,editor\n'
        )
        home, repo = self.setup_repo(tmp_path, flist)

        assert main(args=['categories'], cwd=str(repo), home=str(home)) == 0

        captured = capsys.readouterr()
        assert 'laptop=vim,shell' in captured.out
        assert 'shell' in captured.out
        assert 'vim' in captured.out
        assert 'editor' in captured.out

    def test_categories_hints_current_hostname(self, tmp_path, capsys):
        hostname = socket.gethostname()
        flist = (
            f'{hostname}=vim,shell\n'
            '.zshrc:shell\n'
        )
        home, repo = self.setup_repo(tmp_path, flist)

        assert main(args=['categories'], cwd=str(repo), home=str(home)) == 0

        captured = capsys.readouterr()
        assert f'{hostname}=vim,shell' in captured.out
        assert 'current hostname' in captured.out.lower()

    def test_categories_empty_filelist(self, tmp_path, capsys):
        home, repo = self.setup_repo(tmp_path, '')

        assert main(args=['categories'], cwd=str(repo), home=str(home)) == 0

        captured = capsys.readouterr()
        assert '(none)' in captured.out
