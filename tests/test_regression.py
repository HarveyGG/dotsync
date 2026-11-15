import os

import pytest

from dotsync.flists import Filelist
from dotsync.plugins.plain import PlainPlugin
from dotsync.regression import (
    collect_content_regressions,
    evaluate_pair,
    handle_content_regressions,
)


def _plain_plugin(tmp_path):
    data = tmp_path / '.plugins' / 'plain'
    data.mkdir(parents=True, exist_ok=True)
    repo = tmp_path / 'dotfiles' / 'plain'
    repo.mkdir(parents=True, exist_ok=True)
    return PlainPlugin(data_dir=str(data), repo_dir=str(repo))


class TestRegressionRules:
    def test_whitespace_only_wipe(self, tmp_path):
        home = tmp_path / 'home'
        home.mkdir()
        plugin_dir = tmp_path / 'dotfiles' / 'plain'
        cat = plugin_dir / 'skills'
        cat.mkdir(parents=True)
        source = home / '.cursor' / 'SKILL.md'
        source.parent.mkdir(parents=True)
        repo = cat / '.cursor' / 'SKILL.md'
        repo.parent.mkdir(parents=True)
        repo.write_bytes(b'---\nname: x\n---\nbody\n' * 5)
        source.write_text('\n')
        plugin = _plain_plugin(tmp_path)
        hit = evaluate_pair(
            '.cursor/SKILL.md',
            str(source),
            str(repo),
            {},
            'plain',
            plugin,
        )
        assert hit is not None
        assert hit.reason == 'whitespace-only'

    def test_sharp_size_drop(self, tmp_path):
        home = tmp_path / 'home'
        home.mkdir()
        plugin_dir = tmp_path / 'dotfiles' / 'plain'
        master = plugin_dir / 'common'
        master.mkdir(parents=True)
        source = home / '.file'
        source.write_bytes(b'x')
        repo = master / '.file'
        repo.write_bytes(b'x' * 250)
        plugin = _plain_plugin(tmp_path)
        hit = evaluate_pair('.file', str(source), str(repo), {}, 'plain', plugin)
        assert hit is not None
        assert hit.reason == 'sharp size drop'

    def test_min_bytes_guard(self, tmp_path):
        home = tmp_path / 'home'
        home.mkdir()
        plugin_dir = tmp_path / 'dotfiles' / 'plain'
        master = plugin_dir / 'common'
        master.mkdir(parents=True)
        source = home / '.file'
        source.write_bytes(b'short')
        repo = master / '.file'
        repo.write_bytes(b'longer content here')
        plugin = _plain_plugin(tmp_path)
        entry = {'min_bytes': 50}
        hit = evaluate_pair('.file', str(source), str(repo), entry, 'plain', plugin)
        assert hit is not None
        assert 'min-bytes=50' in hit.reason

    def test_filelist_pipe_guards(self, tmp_path):
        fname = tmp_path / 'filelist'
        fname.write_text('@tree:.config/app:editor|guard=nonempty\n')
        flist = Filelist(str(fname))
        assert flist.trees[0]['guard'] == 'nonempty'

    def test_filelist_encrypt_and_min_bytes(self, tmp_path):
        fname = tmp_path / 'filelist'
        fname.write_text('foo:common|encrypt|min-bytes=50\n')
        flist = Filelist(str(fname))
        inst = flist.files['foo'][0]
        assert inst['plugin'] == 'encrypt'
        assert inst['min_bytes'] == 50

    @pytest.mark.parametrize(
        'line',
        [
            '.wip:common|min-bytes=abc\n',
            '.wip:common|min-bytes=0\n',
            '.wip:common|min-bytes=-5\n',
            '.wip:common|guard=bogus\n',
            '.wip:common|bogus\n',
        ],
    )
    def test_invalid_filelist_modifiers_raise(self, tmp_path, line):
        fname = tmp_path / 'filelist'
        fname.write_text(line)
        with pytest.raises(ValueError, match='Invalid filelist modifier'):
            Filelist(str(fname))


class TestRegressionCollection:
    def test_collect_blocks_atomic_path(self, tmp_path):
        home = tmp_path / 'home'
        home.mkdir()
        repo_root = tmp_path / 'repo'
        repo_root.mkdir()
        plugin_dir = repo_root / 'dotfiles' / 'plain' / 'common'
        plugin_dir.mkdir(parents=True)
        fname = repo_root / 'filelist'
        fname.write_text('.notes:common\n')
        flist = Filelist(str(fname))
        active = flist.activate(['common'])
        source = home / '.notes'
        source.write_text('\n')
        (plugin_dir / '.notes').write_bytes(b'important notes ' * 20)

        plugins, plugin_dirs = {
            'plain': _plain_plugin(repo_root),
        }, {
            'plain': str(repo_root / 'dotfiles' / 'plain'),
        }
        hits = collect_content_regressions(
            flist, str(home), str(repo_root), plugin_dirs, ['common'], active, plugins,
        )
        assert len(hits) == 1
        assert handle_content_regressions(hits, False) == 1
        assert handle_content_regressions(hits, True) == 0