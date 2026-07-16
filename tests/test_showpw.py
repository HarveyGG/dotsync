import json
import os

from dotsync.__main__ import main


def setup_repo(tmp_path, flist):
    home = tmp_path / 'home'
    repo = tmp_path / 'repo'
    os.makedirs(home)
    os.makedirs(repo)
    main(args=['init'], cwd=str(repo))
    with open(repo / 'filelist', 'w') as f:
        f.write(flist)
    return home, repo


def test_showpw_prints_stored_password(tmp_path, capsys, monkeypatch):
    home, repo = setup_repo(tmp_path, 'file\n')

    password = 'password123'
    monkeypatch.setattr('getpass.getpass', lambda prompt: password)

    assert main(args=['passwd'], cwd=str(repo), home=str(home)) == 0

    assert main(args=['showpw'], cwd=str(repo), home=str(home)) == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == password


def test_showpw_no_password_configured(tmp_path, capsys):
    home, repo = setup_repo(tmp_path, '.file:test\n')

    assert main(args=['showpw'], cwd=str(repo), home=str(home)) == 1


def test_showpw_legacy_passwd_store(tmp_path, capsys, monkeypatch):
    """passwd files without plaintext secret cannot be shown."""
    home, repo = setup_repo(tmp_path, 'file\n')

    password = 'password123'
    monkeypatch.setattr('getpass.getpass', lambda prompt: password)

    assert main(args=['passwd'], cwd=str(repo), home=str(home)) == 0

    passwd_path = repo / '.plugins' / 'encrypt' / 'passwd'
    data = json.loads(passwd_path.read_text())
    del data['secret']
    passwd_path.write_text(json.dumps(data))

    assert main(args=['showpw'], cwd=str(repo), home=str(home)) == 1
