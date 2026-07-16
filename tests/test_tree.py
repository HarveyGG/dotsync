import os

from dotsync.flists import Filelist


def write_flist(tmp_path, content):
    fname = os.path.join(tmp_path, 'filelist')
    with open(fname, 'w') as f:
        f.write(content)
    return fname


def make_home(tmp_path):
    home = os.path.join(tmp_path, 'home')
    os.makedirs(home)
    return home


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


def test_expand_trees_glob_and_ignore(tmp_path):
    home = make_home(tmp_path)
    skills = os.path.join(home, '.agents', 'skills')
    os.makedirs(os.path.join(skills, 'vibe-module-foo'))
    with open(os.path.join(skills, 'vibe-module-foo', 'SKILL.md'), 'w') as f:
        f.write('foo')
    os.makedirs(os.path.join(skills, 'vibe-module-bar'))
    with open(os.path.join(skills, 'vibe-module-bar', 'SKILL.md'), 'w') as f:
        f.write('bar')
    os.makedirs(os.path.join(skills, 'other-module'))
    with open(os.path.join(skills, 'other-module', 'SKILL.md'), 'w') as f:
        f.write('other')
    os.makedirs(os.path.join(skills, 'vibe-module-baz', 'node_modules', 'pkg'))
    with open(os.path.join(skills, 'vibe-module-baz', 'node_modules', 'pkg', 'index.js'), 'w') as f:
        f.write('skip')

    fname = write_flist(tmp_path, '@tree:.agents/skills/vibe-module-*:tools\n')
    fl = Filelist(fname)
    result = fl.expand_trees(home, ['tools'])

    paths = set(result.keys())
    assert '.agents/skills/vibe-module-foo/SKILL.md' in paths
    assert '.agents/skills/vibe-module-bar/SKILL.md' in paths
    assert '.agents/skills/other-module/SKILL.md' not in paths
    assert not any('node_modules' in p for p in paths)
    assert result['.agents/skills/vibe-module-foo/SKILL.md'] == {
        'categories': ['tools'],
        'plugin': 'plain',
        'kind': 'file',
    }


def test_new_file_under_tree_included_on_second_expand(tmp_path):
    home = make_home(tmp_path)
    nvim = os.path.join(home, '.config', 'nvim')
    os.makedirs(nvim)
    with open(os.path.join(nvim, 'init.lua'), 'w') as f:
        f.write('v1')

    fname = write_flist(tmp_path, '@tree:.config/nvim:editor\n')
    fl = Filelist(fname)

    result1 = fl.expand_trees(home, ['editor'])
    assert set(result1.keys()) == {'.config/nvim/init.lua'}

    with open(os.path.join(nvim, 'plugins.lua'), 'w') as f:
        f.write('new')
    result2 = fl.expand_trees(home, ['editor'])
    assert set(result2.keys()) == {
        '.config/nvim/init.lua',
        '.config/nvim/plugins.lua',
    }


def test_expand_trees_respects_active_categories(tmp_path):
    home = make_home(tmp_path)
    nvim = os.path.join(home, '.config', 'nvim')
    os.makedirs(nvim)
    with open(os.path.join(nvim, 'init.lua'), 'w') as f:
        f.write('v1')

    fname = write_flist(tmp_path, '@tree:.config/nvim:editor\n')
    fl = Filelist(fname)

    assert fl.expand_trees(home, ['shell']) == {}
    assert fl.expand_trees(home, ['editor']) != {}
