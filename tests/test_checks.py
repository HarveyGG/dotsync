import os

from dotsync.checks import safety_checks
from dotsync.enums import Actions
import dotsync.info as info

class TestSafetyChecks:
    def setup_repo(self, repo):
        os.makedirs(repo / '.git')
        open(repo / 'filelist', 'w').close()

    def test_home(self, tmp_path):
        home = tmp_path / 'home'
        repo = tmp_path / 'repo'

        assert not safety_checks(home, home, True)

    def test_init_empty(self, tmp_path):
        home = tmp_path / 'home'
        repo = tmp_path / 'repo'

        assert safety_checks(repo, home, True)

    def test_other_empty(self, tmp_path):
        home = tmp_path / 'home'
        repo = tmp_path / 'repo'

        assert not safety_checks(repo, home, False)

    def test_have_all(self, tmp_path):
        home = tmp_path / 'home'
        repo = tmp_path / 'repo'

        self.setup_repo(repo)

        assert safety_checks(repo, home, False)

    def test_nogit(self, tmp_path):
        home = tmp_path / 'home'
        repo = tmp_path / 'repo'

        self.setup_repo(repo)
        os.rmdir(repo / '.git')

        assert not safety_checks(repo, home, False)

    def test_nofilelist(self, tmp_path):
        home = tmp_path / 'home'
        repo = tmp_path / 'repo'

        self.setup_repo(repo)
        os.remove(repo / 'filelist')

        assert not safety_checks(repo, home, False)

    def test_old_dotsync(self, tmp_path, caplog):
        home = tmp_path / 'home'
        repo = tmp_path / 'repo'

        self.setup_repo(repo)
        open(repo / 'cryptlist', 'w').close()

        assert not safety_checks(repo, home, False)
        assert 'old dotsync repo' in caplog.text
