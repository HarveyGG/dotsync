import os

from dotsync.flists import Filelist


def write_flist(tmp_path, content):
    fname = os.path.join(tmp_path, 'filelist')
    with open(fname, 'w') as f:
        f.write(content)
    return fname


def test_filelist_parses_tree_entry(tmp_path):
    fname = write_flist(tmp_path, '@tree:.config/nvim:editor\n')

    fl = Filelist(fname)
    assert fl.trees[0]['pattern'] == '.config/nvim'
    assert fl.trees[0]['categories'] == ['editor']
    assert fl.trees[0]['plugin'] == 'plain'


def test_filelist_parses_tree_with_multiple_categories(tmp_path):
    fname = write_flist(tmp_path, '@tree:.local/share/app:tools,common\n')

    fl = Filelist(fname)
    assert fl.trees[0]['pattern'] == '.local/share/app'
    assert fl.trees[0]['categories'] == ['tools', 'common']


def test_filelist_parses_tree_with_encrypt_plugin(tmp_path):
    fname = write_flist(tmp_path, '@tree:.ssh:tools|encrypt\n')

    fl = Filelist(fname)
    assert fl.trees[0]['pattern'] == '.ssh'
    assert fl.trees[0]['categories'] == ['tools']
    assert fl.trees[0]['plugin'] == 'encrypt'


def test_filelist_parses_tree_with_plugin_only(tmp_path):
    fname = write_flist(tmp_path, '@tree:.config/nvim|encrypt\n')

    fl = Filelist(fname)
    assert fl.trees[0]['pattern'] == '.config/nvim'
    assert fl.trees[0]['categories'] == ['common']
    assert fl.trees[0]['plugin'] == 'encrypt'


def test_filelist_parses_tree_glob_pattern(tmp_path):
    fname = write_flist(tmp_path, '@tree:.local/share/my-app/custom-*:tools\n')

    fl = Filelist(fname)
    assert fl.trees[0]['pattern'] == '.local/share/my-app/custom-*'
    assert fl.trees[0]['categories'] == ['tools']


def test_filelist_trees_do_not_affect_files(tmp_path):
    fname = write_flist(tmp_path,
                        '@tree:.config/nvim:editor\n'
                        '.zshrc:shell\n')

    fl = Filelist(fname)
    assert len(fl.trees) == 1
    assert fl.files == {
        '.zshrc': [{
            'categories': ['shell'],
            'plugin': 'plain',
        }],
    }


def test_filelist_multiple_trees(tmp_path):
    fname = write_flist(tmp_path,
                        '@tree:.config/nvim:editor\n'
                        '@tree:.config/alacritty:editor\n')

    fl = Filelist(fname)
    assert len(fl.trees) == 2
    assert fl.trees[0]['pattern'] == '.config/nvim'
    assert fl.trees[1]['pattern'] == '.config/alacritty'
