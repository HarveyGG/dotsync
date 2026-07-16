from dotsync.plugins.plain import PlainPlugin


def test_restore_creates_regular_file_not_symlink(tmp_path):
    repo = tmp_path / 'repo'
    home = tmp_path / 'home'
    repo.mkdir()
    home.mkdir()

    category = repo / 'shell'
    category.mkdir()
    repo_file = category / '.zshrc'
    content = 'export PATH=/usr/bin'
    repo_file.write_text(content)

    dest = home / '.zshrc'
    assert not dest.exists()

    plugin = PlainPlugin(str(tmp_path / 'data'))
    plugin.remove(repo_file, dest)

    assert dest.exists()
    assert not dest.is_symlink()
    assert dest.read_text() == content
