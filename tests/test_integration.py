import os
from dotsync.__main__ import main

# meant to test basic usage patterns
class TestIntegration:
    def setup_repo(self, tmp_path, flist=""):
        home = tmp_path / 'home'
        repo = tmp_path / 'repo'
        os.makedirs(home)
        os.makedirs(repo)
        main(args=['init'], cwd=str(repo))
        with open(repo / 'filelist', 'w') as f:
            f.write(flist)

        return home, repo

    # adds a file to the filelist and updates the repo (and then again)
    def test_add_to_flist(self, tmp_path):
        home, repo = self.setup_repo(tmp_path)
        filelist = repo / "filelist"

        filelist.write_text("foo")
        main(args=['update'], cwd=str(repo), home=str(home))
        assert not (repo / "dotfiles").is_dir()

        (home / "foo").touch()
        main(args=['update'], cwd=str(repo), home=str(home))
        assert (repo / "dotfiles").is_dir()
        assert not (home / "foo").exists()

        filelist.write_text("foo\nbar")
        main(args=['update'], cwd=str(repo), home=str(home))
        assert (repo / "dotfiles").is_dir()

        (home / "bar").touch()
        main(args=['update'], cwd=str(repo), home=str(home))
        assert not (home / "foo").exists()
        assert not (home / "bar").exists()
        assert (repo / "dotfiles" / "plain" / "common" / "bar").exists()

    # adds a file to the repo, removes it from home and then restores it
    def test_add_remove_restore(self, tmp_path):
        home, repo = self.setup_repo(tmp_path, "foo")

        (home / "foo").touch()
        main(args=['update'], cwd=str(repo), home=str(home))

        assert not (home / "foo").exists()

        main(args=['restore'], cwd=str(repo), home=str(home))

        assert (home / "foo").is_file()
        assert not (home / "foo").is_symlink()

    # adds a shared category file to the repo, then makes it an invidual
    # category file
    def test_add_separate_cats(self, tmp_path):
        home, repo = self.setup_repo(tmp_path)
        filelist = repo / "filelist"

        (home / "foo").touch()
        filelist.write_text("foo:asd,common")
        main(args=['update'], cwd=str(repo), home=str(home))

        assert not (home / "foo").exists()
        assert (repo / "dotfiles" / "plain" / "asd" / "foo").exists()
        assert not (repo / "dotfiles" / "plain" / "asd" / "foo").is_symlink()
        assert not (repo / "dotfiles" / "plain" / "common" / "foo").exists()

    def test_update_restore_nested_dir_with_hidden(self, tmp_path):
        """add dir with .hidden and nested subdirs: update copies to repo, restore creates regular files"""
        home, repo = self.setup_repo(tmp_path, '')
        mock = home / '.mockdir'
        mock.mkdir()
        (mock / '.hidden').mkdir()
        (mock / '.hidden' / 'file').write_text('hidden')
        (mock / 'subdir').mkdir()
        (mock / 'subdir' / 'file1').write_text('f1')
        (mock / 'subdir' / 'subdir2').mkdir()
        (mock / 'subdir' / 'subdir2' / 'file2').write_text('f2')

        flist = '.mockdir/.hidden/file:mock\n.mockdir/subdir/file1:mock\n.mockdir/subdir/subdir2/file2:mock\n'
        with open(repo / 'filelist', 'w') as f:
            f.write(flist)

        assert main(args=['update', 'mock'], cwd=str(repo), home=str(home)) == 0
        assert main(args=['restore', 'mock'], cwd=str(repo), home=str(home)) == 0

        for p in ['.mockdir/.hidden/file', '.mockdir/subdir/file1', '.mockdir/subdir/subdir2/file2']:
            fp = home / p
            assert fp.exists(), f'{p} should exist'
            assert not fp.is_symlink(), f'{p} should be a regular file'
            assert 'dotfiles' in str((repo / 'dotfiles' / 'plain' / 'mock' / p).resolve()), f'{p} should be mirrored in repo'

    def test_add_dir_then_update_restore_regular_files(self, tmp_path):
        """add dir with --no-auto-update, then update+restore: home files become regular copies"""
        home, repo = self.setup_repo(tmp_path, '')
        mock = home / '.mockdir'
        mock.mkdir()
        (mock / '.hidden').mkdir()
        (mock / '.hidden' / 'file').write_text('hidden')
        (mock / 'subdir').mkdir()
        (mock / 'subdir' / 'file1').write_text('f1')

        assert main(args=['add', '--no-auto-update', '.mockdir'], cwd=str(repo), home=str(home)) == 0
        assert main(args=['update', 'mockdir'], cwd=str(repo), home=str(home)) == 0
        assert main(args=['restore', 'mockdir'], cwd=str(repo), home=str(home)) == 0

        for p in ['.mockdir/.hidden/file', '.mockdir/subdir/file1']:
            fp = home / p
            assert fp.exists(), f'{p} should exist after restore'
            assert not fp.is_symlink(), f'{p} should be a regular file'
