import builtins
import os

import pytest

from dotsync.__main__ import main
from dotsync.calc_ops import CalcOps, RestoreAborted
from dotsync.plugins.plain import PlainPlugin
from dotsync.policy import RunPolicy


def setup_home_repo(tmp_path):
    home = tmp_path / 'home'
    repo = tmp_path / 'repo'
    os.makedirs(home)
    os.makedirs(repo)
    return home, repo


def test_restore_shows_diff_and_aborts_entire_restore(tmp_path, capsys):
    home, repo = setup_home_repo(tmp_path)
    os.makedirs(repo / 'cat1')
    (repo / 'cat1' / 'file1').write_text('repo one\n')
    (repo / 'cat1' / 'file2').write_text('repo two\n')
    (home / 'file1').write_text('home one\n')

    inputs = iter(['c'])
    capsys.readouterr()

    calc = CalcOps(repo, home, PlainPlugin(tmp_path / '.data'))
    with pytest.raises(RestoreAborted):
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(builtins, 'input', lambda _: next(inputs))
            calc.restore({'file1': ['cat1'], 'file2': ['cat1']}).apply()

    captured = capsys.readouterr()
    assert 'home one' in captured.out or '-home one' in captured.out
    assert 'repo one' in captured.out or '+repo one' in captured.out
    assert not (home / 'file2').exists()
    assert (home / 'file1').read_text() == 'home one\n'


def test_restore_skips_identical_file_without_prompt(tmp_path):
    home, repo = setup_home_repo(tmp_path)
    os.makedirs(repo / 'cat1')
    content = 'same content\n'
    (repo / 'cat1' / 'file').write_text(content)
    (home / 'file').write_text(content)

    def fail_if_input(_):
        raise AssertionError('input called for identical file')

    calc = CalcOps(repo, home, PlainPlugin(tmp_path / '.data'))
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(builtins, 'input', fail_if_input)
        calc.restore({'file': ['cat1']}).apply()

    assert (home / 'file').read_text() == content


def test_restore_overwrite_continues_restore(tmp_path):
    home, repo = setup_home_repo(tmp_path)
    os.makedirs(repo / 'cat1')
    (repo / 'cat1' / 'file1').write_text('repo one\n')
    (repo / 'cat1' / 'file2').write_text('repo two\n')
    (home / 'file1').write_text('home one\n')

    inputs = iter(['o'])
    calc = CalcOps(repo, home, PlainPlugin(tmp_path / '.data'))
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(builtins, 'input', lambda _: next(inputs))
        calc.restore({'file1': ['cat1'], 'file2': ['cat1']}).apply()

    assert (home / 'file1').read_text() == 'repo one\n'
    assert (home / 'file2').read_text() == 'repo two\n'


def test_restore_non_interactive_abort_on_conflict(tmp_path):
    home, repo = setup_home_repo(tmp_path)
    os.makedirs(repo / 'cat1')
    (repo / 'cat1' / 'file').write_text('repo\n')
    (home / 'file').write_text('home\n')

    policy = RunPolicy(non_interactive=True, conflict='abort')
    calc = CalcOps(repo, home, PlainPlugin(tmp_path / '.data'), policy=policy)
    with pytest.raises(RestoreAborted):
        calc.restore({'file': ['cat1']}).apply()


def test_restore_main_cancel_exits_nonzero(tmp_path, monkeypatch):
    home = tmp_path / 'home'
    repo = tmp_path / 'repo'
    os.makedirs(home)
    os.makedirs(repo)
    main(args=['init'], cwd=str(repo), home=str(home))
    with open(repo / 'filelist', 'w') as f:
        f.write('.file1:common\n.file2:common\n')
    (home / '.file1').write_text('home1\n')
    (home / '.file2').write_text('home2\n')
    assert main(args=['update'], cwd=str(repo), home=str(home)) == 0
    (home / '.file1').write_text('changed1\n')
    (home / '.file2').write_text('changed2\n')

    monkeypatch.setattr('builtins.input', lambda _: 'c')

    assert main(args=['restore'], cwd=str(repo), home=str(home)) == 1
    assert (home / '.file1').read_text() == 'changed1\n'
    assert (home / '.file2').read_text() == 'changed2\n'
