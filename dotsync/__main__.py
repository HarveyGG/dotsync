#! /usr/bin/env python3

import logging
import sys
import os

# add the directory which contains the dotsync module to the path. this will
# only ever execute when running the __main__.py script directly since the
# python package will use an entrypoint
if __name__ == '__main__':
    import site
    mod = os.path.dirname(os.path.realpath(__file__))
    site.addsitedir(os.path.dirname(mod))

from dotsync.args import Arguments
from dotsync.enums import Actions
from dotsync.file_ops import BatchApplyError
from dotsync.policy import from_args
from dotsync.checks import safety_checks
from dotsync.flists import Filelist
from dotsync.git import Git, GitPullError
from dotsync.calc_ops import CalcOps, RestoreAborted
from dotsync.tree import materialize_symlinks, pattern_walk_root, restore_symlinks
from dotsync.plugins.plain import PlainPlugin
from dotsync.plugins.encrypt import EncryptPlugin
import dotsync.info as info


# ------------------------------------------------------------------------------
# Utility functions for common checks and operations
# ------------------------------------------------------------------------------

def ensure_filelist_exists(flist_fname, create_if_missing=False):
    """Check if filelist exists, return True if exists, False otherwise"""
    if os.path.exists(flist_fname):
        return True
    
    if create_if_missing:
        logging.info('creating empty filelist')
        open(flist_fname, 'w').close()
        return True
    
    logging.error(f'Filelist not found: {flist_fname}')
    logging.info('Run "dotsync init" to initialize the repository')
    return False


def load_filelist(flist_fname):
    """Load and parse filelist, return Filelist object or None if error"""
    if not ensure_filelist_exists(flist_fname):
        return None
    return Filelist(flist_fname)


def normalize_filepath(filepath, home):
    """Normalize file path to be relative to home directory starting with '.'"""
    normalized_path = filepath
    if normalized_path.startswith('~/'):
        normalized_path = normalized_path[2:]
    elif normalized_path.startswith(home + '/'):
        normalized_path = normalized_path[len(home) + 1:]
    
    if not normalized_path.startswith('.'):
        if not normalized_path.startswith('/'):
            normalized_path = '.' + normalized_path
        else:
            logging.error(f'File path must be relative to home directory: {filepath}')
            return None
    
    return normalized_path


def check_path_in_home(normalized_path, home):
    """Reject paths that escape home via .. (do not follow symlinks)"""
    home_abs = os.path.abspath(home)
    full = os.path.abspath(os.path.join(home, normalized_path))
    if not full.startswith(home_abs + os.sep) and full != home_abs:
        logging.error(f'Path {normalized_path} resolves outside home directory')
        return False
    return True


def check_file_exists(filepath, prompt_if_missing=True):
    """Check if file exists, optionally prompt user if missing"""
    if os.path.exists(filepath):
        return True
    
    if prompt_if_missing:
        logging.warning(f'File does not exist: {filepath}')
        response = input('File does not exist. Add it anyway? [yN] ')
        return response.lower() == 'y'
    
    return False


def read_filelist_lines(flist_fname):
    """Read filelist content as list of lines"""
    if not os.path.exists(flist_fname):
        return []
    
    with open(flist_fname, 'r') as f:
        return f.readlines()


def check_entry_exists_in_filelist(existing_lines, normalized_path, category=None):
    """Check if a file entry already exists in filelist"""
    new_entry = f'{normalized_path}:{category}\n' if category else normalized_path
    for line in existing_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if stripped == new_entry.strip() or (':' in stripped and stripped.split(':')[0] == normalized_path):
            return True
    return False


def handle_dest_file_conflict(repo_file, dest_file, repo, plugin, plugin_name=None, detailed_prompt=False, policy=None):
    """Handle conflicts when destination file already exists
    
    Args:
        repo_file: Source file path in repository
        dest_file: Destination file path in home directory
        repo: Repository root path
        plugin: Plugin instance (for samefile check)
        plugin_name: Plugin name (for encrypted file comparison)
        detailed_prompt: If True, show detailed options (overwrite/keep/cancel)
    
    Returns:
        tuple: (should_proceed, should_copy)
        - should_proceed: True if operation should continue, False if cancelled
        - should_copy: True if should copy from repo, False if should keep existing
    """
    import filecmp
    
    if not os.path.exists(dest_file):
        # Check for dangling symlink
        if os.path.islink(dest_file):
            logging.info(f'Removing dangling symlink: {dest_file}')
            os.remove(dest_file)
        return (True, True)
    
    # Check if files are the same
    try:
        if plugin.samefile(repo_file, dest_file):
            logging.debug(f'{dest_file} is the same as in repo, skipping')
            return (True, False)  # Skip, don't copy
    except Exception:
        pass  # Continue with comparison
    
    if os.path.islink(dest_file):
        link_target = os.readlink(dest_file)
        repo_abs = os.path.abspath(repo_file)
        try:
            resolved_target = os.path.abspath(os.path.join(os.path.dirname(dest_file), link_target))
        except Exception:
            resolved_target = None
        if (os.path.abspath(link_target) == repo_abs or
            (resolved_target and resolved_target == repo_abs) or
            link_target.startswith(repo + os.sep)):
            # Symlink to repo, safe to remove
            logging.info(f'Removing symlink to repo: {dest_file}')
            os.remove(dest_file)
            return (True, True)
        else:
            logging.warning(f'{dest_file} is a symlink pointing to {link_target}')
            if policy and policy.non_interactive:
                from dotsync.interaction import decide_conflict
                result = decide_conflict(True, True, False, policy)
                if result == (True, True):
                    os.remove(dest_file)
                    return (True, True)
                if result == (True, False):
                    return (True, False)
                return (False, False)
            response = input('Remove this symlink? [Yn] ')
            response = 'y' if not response else response.lower()
            if response == 'y':
                os.remove(dest_file)
                return (True, True)
            return (False, False)

    if not os.path.exists(repo_file):
        if policy and policy.non_interactive:
            from dotsync.interaction import decide_conflict
            result = decide_conflict(True, False, False, policy)
            if result == (True, True):
                return (True, True)
            if result == (True, False):
                return (True, False)
            return (False, False)
        response = input(f'{dest_file} already exists but repo file not found. Keep existing? [Yn] ')
        response = 'y' if not response else response.lower()
        return (True, response != 'y')
    
    # Compare files if possible
    files_differ = None
    if detailed_prompt:
        try:
            if plugin_name == 'encrypt':
                # For encrypted files, can't easily compare
                files_differ = None
            else:
                files_differ = not filecmp.cmp(repo_file, dest_file, shallow=False)
        except Exception:
            files_differ = None
    
    if policy and policy.non_interactive:
        from dotsync.interaction import decide_conflict
        result = decide_conflict(True, os.path.islink(dest_file), False, policy)
        if result == (True, True):
            os.remove(dest_file)
            return (True, True)
        if result == (True, False):
            return (True, False)
        return (False, False)

    if files_differ and detailed_prompt:
        print(f'File {dest_file} already exists and differs from repository version.')
        print('Options:')
        print('  [o] Overwrite with repository version')
        print('  [k] Keep existing file')
        print('  [c] Cancel')
        while True:
            choice = input('Your choice [okc]: ').lower()
            if choice == 'o':
                logging.info(f'Removing existing file: {dest_file}')
                os.remove(dest_file)
                return (True, True)
            elif choice == 'k':
                logging.info('Keeping existing file')
                return (True, False)
            elif choice == 'c':
                logging.info('Cancelled')
                return (False, False)
            else:
                print('Invalid choice, please enter o, k, or c')
    else:
        prompt = f'{dest_file} already exists'
        if files_differ is True:
            prompt += ' and differs from repository version'
        prompt += '. Replace? [Yn] '
        response = input(prompt)
        response = 'y' if not response else response.lower()
        if response == 'y':
            os.remove(dest_file)
            return (True, True)
        return (False, False)


def find_dotsync_repo(start_dir=None, home=None):
    """Find dotsync repository directory by searching upward from start_dir
    
    Search strategy:
    1. Check environment variable DOTSYNC_REPO
    2. Search upward from start_dir for directory containing .git and filelist
    3. Check default location ~/.dotfiles
    
    Returns:
        str: Path to repository directory, or None if not found
    """
    if home is None:
        home = info.home
    
    # Check environment variable first
    env_repo = os.environ.get('DOTSYNC_REPO')
    if env_repo:
        env_repo = os.path.expanduser(env_repo)
        if os.path.isdir(env_repo):
            filelist_path = os.path.join(env_repo, 'filelist')
            git_path = os.path.join(env_repo, '.git')
            if os.path.exists(filelist_path) or os.path.isdir(git_path):
                return env_repo
    
    # Search upward from start_dir
    if start_dir is None:
        start_dir = os.getcwd()
    
    current_dir = os.path.abspath(start_dir)

    while True:
        filelist_path = os.path.join(current_dir, 'filelist')
        git_path = os.path.join(current_dir, '.git')
        if os.path.exists(filelist_path):
            if os.path.isdir(git_path) or current_dir == os.path.join(home, '.dotfiles'):
                return current_dir

        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir or current_dir == home:
            break
        current_dir = parent_dir
    
    # Check default location
    default_repo = os.path.join(home, '.dotfiles')
    if os.path.isdir(default_repo):
        filelist_path = os.path.join(default_repo, 'filelist')
        git_path = os.path.join(default_repo, '.git')
        if os.path.exists(filelist_path) or os.path.isdir(git_path):
            return default_repo
    
    return None


# ------------------------------------------------------------------------------
# Command functions
# ------------------------------------------------------------------------------

def init_repo(repo_dir, flist):
    # Ensure repository directory exists
    if not os.path.exists(repo_dir):
        try:
            os.makedirs(repo_dir, exist_ok=True)
            logging.info(f'Created repository directory: {repo_dir}')
        except OSError as e:
            logging.error(f'Failed to create repository directory {repo_dir}: {e}')
            return
    
    git = Git(repo_dir)
    if not os.path.isdir(os.path.join(repo_dir, '.git')):
        logging.info('creating git repo')
        git.init()
    else:
        logging.warning('existing git repo, not re-creating')

    changed = False

    # Create README.md if it doesn't exist
    readme_path = os.path.join(repo_dir, 'README.md')
    if not os.path.exists(readme_path):
        readme_content = """# Dotfiles

This repository is managed by [dotsync](https://github.com/HarveyGG/dotsync), a dotfiles management tool.

## Setup GitHub Repository

To backup your dotfiles to GitHub:

1. Create a new repository on GitHub (e.g., `dotfiles`)
2. Add the remote to your local repository:
   ```bash
   cd ~/.dotfiles
   git remote add origin git@github.com:YOUR_USERNAME/dotfiles.git
   ```
3. Push your files:
   ```bash
   dotsync commit
   # When prompted, answer 'y' to push to remote
   ```

Alternatively, you can push manually using git commands:
```bash
git push -u origin master
```

## Basic Usage

- Add a file to manage: `dotsync add ~/.zshrc`
- Update files from home to repo: `dotsync update`
- Restore files from repo to home: `dotsync restore`
- Commit changes: `dotsync commit`
- List managed files: `dotsync list`

For more information, visit the [dotsync documentation](https://github.com/HarveyGG/dotsync).
"""
        with open(readme_path, 'w') as f:
            f.write(readme_content)
        git.add('README.md')
        changed = True
    else:
        logging.warning('existing README.md, not recreating')

    # Create filelist if it doesn't exist
    if not os.path.exists(flist):
        ensure_filelist_exists(flist, create_if_missing=True)
        git.add(os.path.basename(flist))
        changed = True
    else:
        logging.warning('existing filelist, not recreating')

    if changed:
        git.commit()


def bootstrap_repo(home):
    """Create and initialize the default dotsync repository if missing."""
    env_repo = os.environ.get('DOTSYNC_REPO')
    if env_repo:
        repo = os.path.abspath(os.path.expanduser(env_repo))
    else:
        repo = os.path.join(home, '.dotfiles')

    if not os.path.exists(repo):
        os.makedirs(repo, exist_ok=True)
        logging.info(f'Created repository directory: {repo}')
    elif not os.path.isdir(repo):
        logging.error(f'{repo} exists but is not a directory')
        return None

    flist_fname = os.path.join(repo, 'filelist')
    init_repo(repo, flist_fname)
    return repo


def infer_category_from_path(filepath):
    """Infer category name from file path based on common patterns"""
    basename = os.path.basename(filepath)
    dirname = os.path.dirname(filepath)
    
    # Direct matches
    if basename == '.zshrc':
        return 'zsh'
    elif basename == '.vimrc' or basename == '.nvimrc':
        return 'vim'
    elif basename == '.gitconfig':
        return 'git'
    elif 'ssh' in filepath or 'ssh' in dirname:
        return 'ssh'
    elif 'aws' in filepath or 'aws' in dirname:
        return 'aws'
    elif 'tmux' in filepath:
        return 'tmux'
    elif 'vscode' in filepath or '.vscode' in dirname:
        return 'vscode'
    elif '.vibe' in filepath or basename == 'vibe':
        return 'vibe'
    elif basename.startswith('.'):
        # For dotfiles starting with ., use the name without dot
        return basename[1:].split('.')[0]
    
    # Default: use the directory name or filename without extension
    if dirname and dirname != '.':
        return os.path.basename(dirname)
    return basename.split('.')[0] if '.' in basename else basename


def add_to_filelist(flist_fname, filepath, category, home, dry_run, verbose_level, encrypt=False, auto_update=False, repo=None, plugins=None, plugin_dirs=None):
    """Add a new configuration file to the filelist"""
    # System files to ignore (e.g., macOS .DS_Store, Windows Thumbs.db)
    SYSTEM_FILES = {'.DS_Store', 'Thumbs.db', '.DS_Store?'}
    
    normalized_path = normalize_filepath(filepath, home)
    if normalized_path is None:
        return 1
    if not check_path_in_home(normalized_path, home):
        return 1

    # Reject system files
    basename = os.path.basename(normalized_path)
    if basename in SYSTEM_FILES:
        logging.error(f'Cannot manage system file: {normalized_path}')
        logging.info('System files like .DS_Store are automatically ignored')
        return 1
    
    # Check if path exists (skip prompt in dry-run mode)
    full_path = os.path.join(home, normalized_path)
    if dry_run:
        # In dry-run, just warn if path doesn't exist but continue
        if not os.path.exists(full_path):
            logging.warning(f'Path does not exist: {full_path} (dry-run mode, continuing)')
    else:
        # In normal mode, prompt user if path doesn't exist
        if not check_file_exists(full_path, prompt_if_missing=True):
            logging.info('Cancelled')
            return 1
    
    # Determine category
    if not category:
        category = infer_category_from_path(normalized_path)
        logging.info(f'Inferred category: {category}')
    
    # Read existing filelist
    existing_lines = read_filelist_lines(flist_fname)
    
    # Build entry with optional encrypt plugin
    plugin_suffix = '|encrypt' if encrypt else ''
    
    # If encrypt is requested, prompt for password interactively (for both file and directory)
    if encrypt and not dry_run:
        try:
            from dotsync.plugins.encrypt import EncryptPlugin
            repo_dir = os.path.dirname(flist_fname) if repo is None else repo
            encrypt_plugin = EncryptPlugin(
                data_dir=os.path.join(repo_dir, '.plugins', 'encrypt'),
                repo_dir=os.path.join(repo_dir, 'dotfiles', 'encrypt') if repo else None
            )
            encrypt_plugin.init_password()
            logging.info('Encryption password set')
        except Exception as e:
            logging.error(f'Failed to initialize encryption: {e}')
            return 1
    
    if os.path.isdir(full_path):
        from dotsync.tree import DIR_SKIP
        paths_to_add = []
        for root, dirs, files in os.walk(full_path):
            dirs[:] = [d for d in dirs if d not in DIR_SKIP]
            for f in files:
                if f in SYSTEM_FILES:
                    continue
                abs_f = os.path.join(root, f)
                rel = os.path.relpath(abs_f, home)
                if not rel.startswith('.'):
                    rel = '.' + rel
                paths_to_add.append(rel)
        if not paths_to_add:
            logging.warning(f'No files found under directory {filepath}')
            return 1
        new_entries = []
        for p in paths_to_add:
            if check_entry_exists_in_filelist(existing_lines, p, category):
                logging.debug(f'Already in filelist: {p}')
                continue
            new_entries.append((p, f'{p}:{category}{plugin_suffix}\n'))
            existing_lines.append(f'{p}:{category}{plugin_suffix}\n')
        if not new_entries:
            logging.warning(f'All files under {filepath} are already in filelist')
            return 1
        if dry_run:
            for p, _ in new_entries:
                logging.info(f'[DRY RUN] Would add to filelist: {p}:{category}{plugin_suffix}')
            return 0
        with open(flist_fname, 'a') as f:
            if existing_lines and not existing_lines[-1].endswith('\n'):
                f.write('\n')
            for p, entry in new_entries:
                f.write(entry)
                logging.info(f'Added to filelist: {p}:{category}{plugin_suffix}')
        if auto_update and not dry_run and repo and plugins is not None and plugin_dirs is not None:
            logging.info('Auto-updating files...')
            try:
                plugin_name = 'encrypt' if encrypt else 'plain'
                new_only = {p: {'categories': [category], 'plugin': plugin_name} for p, _ in new_entries}
                manifest = {plugin_name: [os.path.join(category, p) for p, _ in new_entries]}
                filelist_obj = Filelist(flist_fname)
                from dotsync.args import Arguments
                args = Arguments(['update', category, '--non-interactive'])
                update_files(
                    repo, filelist_obj, new_only, manifest, plugins, plugin_dirs, home, args,
                )
                restore_args = Arguments(['restore', category, '--non-interactive', '--skip-pull'])
                restore_files(
                    repo, filelist_obj, new_only, manifest, plugins, plugin_dirs, home, restore_args,
                )
                logging.info('Files synced and linked successfully')
            except Exception as e:
                logging.error(f'Failed to auto-update: {e}')
                logging.info(f'Run "dotsync update {category}" to sync the files')
        else:
            logging.info(f'Run "dotsync update {category}" to sync the files')
        return 0
    
    # Single file: check if already in filelist
    new_entry = f'{normalized_path}:{category}{plugin_suffix}\n'
    if check_entry_exists_in_filelist(existing_lines, normalized_path, category):
        logging.warning(f'Entry already exists in filelist: {normalized_path}:{category}')
        return 1
    
    # Add new entry (before the last newline if file ends with newline, otherwise append)
    if dry_run:
        logging.info(f'[DRY RUN] Would add to filelist: {normalized_path}:{category}{plugin_suffix}')
        return 0
    
    # Append new entry
    with open(flist_fname, 'a') as f:
        # Add a newline before entry if file doesn't end with one
        if existing_lines and not existing_lines[-1].endswith('\n'):
            f.write('\n')
        f.write(new_entry)
    
    logging.info(f'Added to filelist: {normalized_path}:{category}{plugin_suffix}')
    
    # Auto-update: sync file to repository and create symlink
    if auto_update and not dry_run:
        logging.info('Auto-updating file...')
        try:
            # Load filelist
            filelist = Filelist(flist_fname)
            manifest = filelist.manifest()
            
            # Activate categories
            try:
                filelist = filelist.activate([category])
            except RuntimeError as e:
                logging.error(f'Error activating category {category}: {e}')
                return 1
            
            # Update and restore for the specific file
            for plugin_name in plugins:
                flist = {path: filelist[path]['categories'] for path in filelist 
                        if filelist[path]['plugin'] == plugin_name and path == normalized_path}
                if not flist:
                    continue
                
                plugin_dir = plugin_dirs[plugin_name]
                calc_ops = CalcOps(plugin_dir, home, plugins[plugin_name])
                calc_ops.update(flist).apply(dry_run)
                calc_ops.restore(flist).apply(dry_run)
                
            logging.info('File synced and linked successfully')
        except Exception as e:
            logging.error(f'Failed to auto-update: {e}')
            logging.info('You can manually run "dotsync update" to sync the file')
    else:
        logging.info(f'Run "dotsync update {category}" to sync the file')
    
    return 0


def encrypt_to_filelist(flist_fname, filepath, home, dry_run):
    """Convert an existing plain config file to encrypted management"""
    # Normalize filepath
    normalized_path = normalize_filepath(filepath, home)
    if normalized_path is None:
        return 1
    
    # Load filelist
    filelist = load_filelist(flist_fname)
    if filelist is None:
        return 1
    
    # Check if file is already in filelist
    if normalized_path not in filelist.files:
        logging.error(f'File {normalized_path} is not in filelist. Use "dotsync add" first.')
        return 1
    
    # Check if already encrypted
    instances = filelist.files[normalized_path]
    for instance in instances:
        if instance['plugin'] == 'encrypt':
            logging.warning(f'File {normalized_path} is already encrypted')
            return 1
    
    # Read existing filelist lines
    existing_lines = read_filelist_lines(flist_fname)
    
    if dry_run:
        logging.info(f'[DRY RUN] Would convert {normalized_path} to encrypted')
        return 0
    
    # Initialize encryption password interactively
    try:
        from dotsync.plugins.encrypt import EncryptPlugin
        repo_dir = os.path.dirname(flist_fname)
        encrypt_plugin = EncryptPlugin(
            data_dir=os.path.join(repo_dir, '.plugins', 'encrypt'),
            repo_dir=os.path.join(repo_dir, 'dotfiles', 'encrypt')
        )
        encrypt_plugin.init_password()
        logging.info('Encryption password verified')
    except Exception as e:
        logging.error(f'Failed to initialize encryption: {e}')
        return 1
    
    # Update filelist: replace plain entries with encrypted entries
    new_lines = []
    updated = False
    for line in existing_lines:
        stripped = line.strip()
        # Skip empty lines and comments
        if not stripped or stripped.startswith('#'):
            new_lines.append(line)
            continue
        
        # Check if this line is for our file
        # Parse: path[:category][|plugin]
        parts = stripped.split(':')
        if len(parts) >= 1:
            file_path = parts[0].split('|')[0]  # Remove plugin suffix if present
            
            if file_path == normalized_path:
                # This is the file we want to encrypt
                # Reconstruct the line with |encrypt suffix
                if '|' in stripped:
                    # Already has a plugin, replace it with encrypt
                    base = stripped.rsplit('|', 1)[0]
                    new_lines.append(base + '|encrypt\n')
                elif ':' in stripped:
                    # Has category but no plugin
                    new_lines.append(stripped + '|encrypt\n')
                else:
                    # No category, no plugin
                    new_lines.append(stripped + '|encrypt\n')
                updated = True
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    
    if not updated:
        logging.error(f'Could not find {normalized_path} in filelist')
        return 1
    
    # Write updated filelist
    with open(flist_fname, 'w') as f:
        f.writelines(new_lines)
    
    logging.info(f'Converted {normalized_path} to encrypted management')
    logging.info('Run "dotsync update" to re-sync the file with encryption')
    
    return 0


def purge_repo_paths(repo, plugin_dirs, paths_by_plugin, dotsync_repo=None):
    """Delete mirrored paths from the repository."""
    if dotsync_repo is None:
        dotsync_repo = repo

    for plugin_name, paths in paths_by_plugin.items():
        plugin_dir = plugin_dirs[plugin_name]
        for rel_path in paths:
            if rel_path.startswith('.dotsync/'):
                full = os.path.join(dotsync_repo, rel_path)
            else:
                full = os.path.join(plugin_dir, rel_path)
            if os.path.isfile(full):
                os.remove(full)
                logging.info(f'Removed repository file: {full}')
            elif os.path.isdir(full):
                import shutil
                shutil.rmtree(full)
                logging.info(f'Removed repository directory: {full}')


def unmanage_from_filelist(flist_fname, filepath, home, repo, plugins, plugin_dirs, dry_run, policy=None, purge_repo=False):
    """Restore a configuration file to home directory and stop managing it"""
    normalized_path = normalize_filepath(filepath, home)
    if normalized_path is None:
        return 1
    if not check_path_in_home(normalized_path, home):
        return 1

    filelist = load_filelist(flist_fname)
    if filelist is None:
        return 1

    tree = filelist.find_tree_for_path(normalized_path)
    if tree is not None:
        pattern = tree['pattern']
        walk_root = pattern_walk_root(pattern) or pattern
        norm = normalized_path.rstrip('/')
        if norm == pattern.rstrip('/') or norm == walk_root.rstrip('/'):
            return _unmanage_tree(
                flist_fname, tree, home, repo, plugins, plugin_dirs,
                dry_run, policy, purge_repo,
            )

    dir_base = normalized_path.rstrip('/')
    home_dir = os.path.join(home, dir_base)
    is_dir_input = dir_base.endswith('/') or os.path.isdir(home_dir)
    if normalized_path in filelist.files:
        targets = [normalized_path]
    elif is_dir_input:
        prefix = dir_base + os.sep
        targets = sorted(p for p in filelist.files if p.startswith(prefix))
        if not targets:
            logging.error(f'No managed files under {dir_base}/')
            return 1
    else:
        logging.error(f'File {normalized_path} is not managed by dotsync')
        return 1

    if dry_run:
        for p in targets:
            logging.info(f'[DRY RUN] Would unmanage {p}')
        return 0

    keep_going = getattr(policy, 'keep_going', False) if policy else False
    failed = []
    for normalized_path in targets:
        if _unmanage_one(
            flist_fname, normalized_path, home, repo, filelist, plugins, plugin_dirs,
            policy, purge_repo=purge_repo,
        ) != 0:
            if not keep_going:
                return 1
            failed.append(normalized_path)
    if failed:
        for p in failed:
            logging.error(f'Failed to unmanage {p}')
        return 1
    return 0


def _unmanage_tree(flist_fname, tree, home, repo, plugins, plugin_dirs, dry_run, policy, purge_repo):
    """Remove a @tree entry from the filelist and optionally purge mirrored paths."""
    pattern = tree['pattern']
    if dry_run:
        logging.info(f'[DRY RUN] Would untrack tree {pattern}')
        if purge_repo:
            logging.info(f'[DRY RUN] Would purge mirrored tree paths for {pattern}')
        return 0

    existing_lines = read_filelist_lines(flist_fname)
    new_lines = []
    removed = False
    tree_prefix = f'@tree:{pattern}'
    for line in existing_lines:
        stripped = line.strip()
        if stripped.startswith(tree_prefix):
            removed = True
            continue
        new_lines.append(line)

    if not removed:
        logging.error(f'Tree {pattern} is not managed by dotsync')
        return 1

    with open(flist_fname, 'w') as f:
        f.writelines(new_lines)
    logging.info(f'Removed tree {pattern} from filelist')

    if purge_repo:
        plugin_name = tree['plugin']
        plugin_dir = plugin_dirs[plugin_name]
        master = min(tree['categories'])
        from dotsync.manifest import manifest_path, read_manifest

        paths = []
        tree_root = os.path.join(plugin_dir, master, pattern_walk_root(pattern) or pattern)
        if os.path.isdir(tree_root):
            for root, dirs, files in os.walk(tree_root):
                for fname in files:
                    rel = os.path.relpath(os.path.join(root, fname), plugin_dir)
                    paths.append(rel)

        for entry in read_manifest(repo, master):
            paths.append(entry['canonical_repo_path'])

        purge_repo_paths(repo, plugin_dirs, {plugin_name: paths}, dotsync_repo=repo)

        manifest_file = manifest_path(repo, master)
        if os.path.exists(manifest_file):
            os.remove(manifest_file)
            logging.info(f'Removed sidecar manifest: {manifest_file}')

    return 0


def _unmanage_one(flist_fname, normalized_path, home, repo, filelist, plugins, plugin_dirs, policy=None, purge_repo=False):
    """Unmanage a single file. filelist is the loaded object (may be stale after first call)."""
    if normalized_path not in filelist.files:
        logging.error(f'File {normalized_path} is not managed by dotsync')
        return 1

    instances = filelist.files[normalized_path]
    if not instances:
        logging.error(f'File {normalized_path} has no valid configuration')
        return 1

    instance = instances[0]
    plugin_name = instance['plugin']
    categories = instance['categories']
    master_category = min(categories)
    plugin_dir = plugin_dirs[plugin_name]
    repo_file = os.path.join(plugin_dir, master_category, normalized_path)
    home_file = os.path.join(home, normalized_path)

    if not os.path.exists(repo_file):
        logging.warning(f'Repository file not found: {repo_file}')

    plugin = plugins[plugin_name]
    should_proceed, should_copy = handle_dest_file_conflict(
        repo_file, home_file, repo, plugin, plugin_name=plugin_name, detailed_prompt=True, policy=policy
    )
    if not should_proceed:
        logging.info('Cancelled')
        return 1
    if should_copy is False and os.path.islink(home_file):
        os.remove(home_file)
        should_copy = True

    if should_copy and os.path.exists(repo_file):
        home_dir = os.path.dirname(home_file)
        if home_dir and not os.path.exists(home_dir):
            os.makedirs(home_dir, exist_ok=True)
            logging.info(f'Created directory: {home_dir}')
        try:
            if plugin_name == 'encrypt':
                logging.info(f'Decrypting {normalized_path}...')
                plugin.init_password()
                plugin.remove(repo_file, home_file)
            else:
                original_hard = plugin.hard
                plugin.hard = True
                try:
                    logging.info(f'Copying {normalized_path}...')
                    plugin.remove(repo_file, home_file)
                finally:
                    plugin.hard = original_hard
            logging.info(f'File restored to: {home_file}')
        except Exception as e:
            logging.error(f'Failed to copy/decrypt file: {e}')
            return 1

    existing_lines = read_filelist_lines(flist_fname)
    new_lines = []
    removed = False
    for line in existing_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            new_lines.append(line)
            continue
        parts = stripped.split(':')
        if len(parts) >= 1:
            file_path = parts[0].split('|')[0]
            if file_path == normalized_path:
                removed = True
                continue
        new_lines.append(line)

    if not removed:
        logging.warning(f'Could not find {normalized_path} in filelist')

    with open(flist_fname, 'w') as f:
        f.writelines(new_lines)
    logging.info(f'Removed {normalized_path} from filelist')

    if purge_repo and os.path.exists(repo_file):
        try:
            os.remove(repo_file)
            logging.info(f'Removed repository file: {repo_file}')
            category_dir = os.path.dirname(repo_file)
            if os.path.exists(category_dir) and not os.listdir(category_dir):
                os.rmdir(category_dir)
                logging.info(f'Removed empty category directory: {category_dir}')
        except Exception as e:
            logging.warning(f'Failed to clean up repository file: {e}')

    if plugin_name == 'encrypt':
        try:
            plugin.clean_data([os.path.join(master_category, normalized_path)])
            logging.info('Cleaned up encryption metadata')
        except Exception as e:
            logging.warning(f'Failed to clean up encryption metadata: {e}')

    logging.info(f'Successfully unmanaged {normalized_path}')
    return 0


def list_managed_files(flist_fname, categories, home):
    """List all managed configuration files"""
    filelist = load_filelist(flist_fname)
    if filelist is None:
        return 1
    
    # If no categories specified, show all files
    if not categories or categories == ['common', info.hostname]:
        # Show all files from filelist
        all_files = {}
        for path, instances in filelist.files.items():
            for instance in instances:
                plugin = instance['plugin']
                cats = ','.join(instance['categories'])
                if path not in all_files:
                    all_files[path] = []
                all_files[path].append({
                    'categories': cats,
                    'plugin': plugin
                })
        
        if not all_files:
            print('No managed configuration files found.')
            return 0
        
        print('Managed configuration files:')
        print('=' * 70)
        for path in sorted(all_files.keys()):
            instances = all_files[path]
            full_path = os.path.join(home, path)
            exists = '✓' if os.path.exists(full_path) else '✗'
            
            for instance in instances:
                categories_str = instance['categories']
                plugin = instance['plugin']
                print(f'{exists} {path:<40} [{categories_str}] ({plugin})')
        
        print('=' * 70)
        print(f'Total: {len(all_files)} file(s)')
    else:
        # Show files for specified categories
        try:
            active_files = filelist.activate(categories)
        except RuntimeError:
            logging.error(f'Error activating categories: {categories}')
            return 1
        
        if not active_files:
            print(f'No files found for categories: {", ".join(categories)}')
            return 0
        
        print(f'Managed files for categories: {", ".join(categories)}')
        print('=' * 70)
        for path in sorted(active_files.keys()):
            instance = active_files[path]
            full_path = os.path.join(home, path)
            exists = '✓' if os.path.exists(full_path) else '✗'
            categories_str = ','.join(instance['categories'])
            plugin = instance['plugin']
            print(f'{exists} {path:<40} [{categories_str}] ({plugin})')
        
        print('=' * 70)
        print(f'Total: {len(active_files)} file(s)')
    
    return 0


def show_categories(flist_fname):
    """Show category groups and unique categories from filelist"""
    filelist = load_filelist(flist_fname)
    if filelist is None:
        return 1

    group_lines = []
    with open(flist_fname, 'r') as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            if '=' in stripped:
                group_lines.append(stripped)

    categories = set()
    for instances in filelist.files.values():
        for instance in instances:
            categories.update(instance['categories'])
    for group_cats in filelist.groups.values():
        categories.update(group_cats)

    print('Category groups:')
    if group_lines:
        for line in sorted(group_lines):
            group_name = line.split('=', 1)[0]
            marker = '  (current hostname)' if group_name == info.hostname else ''
            print(f'  {line}{marker}')
    else:
        print('  (none)')

    print()
    print('Categories:')
    if categories:
        for cat in sorted(categories):
            print(f'  {cat}')
    else:
        print('  (none)')

    if info.hostname in filelist.groups:
        print()
        print(f'Current hostname "{info.hostname}" matches group "{info.hostname}"')

    return 0


def confirm_prune(stale_paths, policy):
    """Ask before deleting repo mirror paths no longer in the manifest."""
    if not stale_paths:
        return True
    if policy and policy.non_interactive:
        return True

    print('The following repository files are no longer in the manifest:')
    for path in sorted(stale_paths):
        print(f'  {path}')
    ans = input('Remove these files from the repository? [yN] ')
    return ans.lower() in ('y', 'yes')


def materialize_tree_symlinks(filelist_obj, home, repo, plugin_dirs, categories):
    """Materialize symlinks for active @tree entries; return canonical repo paths."""
    symlink_canonicals = {}
    active_cats = filelist_obj._flatten_categories(categories)

    for tree in filelist_obj.trees:
        if not set(active_cats) & set(tree['categories']):
            continue

        plugin_name = tree['plugin']
        plugin_dir = plugin_dirs[plugin_name]
        watched = filelist_obj.expand_trees(home, categories)
        watched = {
            path: info for path, info in watched.items()
            if set(info['categories']) & set(tree['categories'])
        }
        if not watched:
            continue

        master = min(tree['categories'])
        entries = materialize_symlinks(
            home,
            plugin_dir,
            watched,
            master,
            tree['pattern'],
            dotsync_repo=repo,
        )
        if entries:
            paths = [e['canonical_repo_path'] for e in entries]
            symlink_canonicals.setdefault(plugin_name, []).extend(paths)

    return symlink_canonicals


def prepare_active_filelist(filelist_obj, home, categories, plugin_dirs=None, from_repo=False):
    """Merge atomic and tree entries for save/update/restore."""
    return filelist_obj.merge_active(
        home,
        categories,
        plugin_dir=plugin_dirs.get('plain') if plugin_dirs else None,
        from_repo=from_repo,
    )


def plugin_filelist(active_filelist, plugin):
    """Build calc_ops file dict for a single plugin."""
    return {
        path: active_filelist[path]
        for path in active_filelist
        if active_filelist[path]['plugin'] == plugin
    }


def update_files(repo, filelist_obj, active_filelist, manifest, plugins, plugin_dirs, home, args):
    """Update files from home to repository"""
    clean_ops = []
    policy = from_args(args)

    symlink_canonicals = materialize_tree_symlinks(
        filelist_obj, home, repo, plugin_dirs, args.categories
    )
    manifest = filelist_obj.build_save_manifest(
        home, args.categories, symlink_canonicals=symlink_canonicals
    )

    for plugin in plugins:
        flist = plugin_filelist(active_filelist, plugin)
        if not flist:
            continue
        logging.debug(f'active filelist for plugin {plugin}: {flist}')

        plugin_dir = plugin_dirs[plugin]
        calc_ops = CalcOps(plugin_dir, home, plugins[plugin], policy=policy)

        try:
            calc_ops.update(flist).apply(args.dry_run, keep_going=policy.keep_going)
        except BatchApplyError as e:
            for op_str, err in e.errors:
                logging.error(f'{op_str}: {err}')
            return 1
        except Exception as e:
            logging.error(str(e))
            return 1

        allowed = set(manifest.get(plugin, []))
        stale = calc_ops.find_stale_repo_files(allowed)
        if stale and not confirm_prune(stale, policy):
            logging.info('Prune cancelled')
            return 1

        clean_ops.append(calc_ops.clean_repo(manifest[plugin]))
        plugins[plugin].clean_data(manifest[plugin])

    for clean_op in clean_ops:
        try:
            clean_op.apply(args.dry_run, keep_going=policy.keep_going)
        except BatchApplyError as e:
            for op_str, err in e.errors:
                logging.error(f'{op_str}: {err}')
            return 1

    return 0


def ensure_repo_current(git, policy):
    """Fetch and fast-forward pull before restore; return HEAD sha or None on failure."""
    if policy.skip_pull:
        sha = git.head_sha()
    else:
        try:
            if git.has_remote():
                sha = git.pull_ff_only()
            else:
                logging.debug('No remote configured; using local repository')
                sha = git.head_sha()
        except GitPullError as e:
            logging.error(f'Failed to pull latest changes: {e}')
            return None

    print(f'Restoring from commit {sha}')
    return sha


def restore_files(repo, filelist_obj, active_filelist, manifest, plugins, plugin_dirs, home, args):
    """Restore files from repository to home"""
    clean_ops = []
    policy = from_args(args)

    git = Git(repo)
    if ensure_repo_current(git, policy) is None:
        return 1

    active_cats = filelist_obj._flatten_categories(args.categories)

    for plugin in plugins:
        flist = plugin_filelist(active_filelist, plugin)
        if not flist:
            continue
        logging.debug(f'active filelist for plugin {plugin}: {flist}')

        plugin_dir = plugin_dirs[plugin]
        calc_ops = CalcOps(plugin_dir, home, plugins[plugin], policy=policy)

        try:
            calc_ops.restore(flist).apply(args.dry_run, keep_going=policy.keep_going)
            restore_symlinks(
                home,
                plugin_dir,
                repo,
                active_cats,
                plugins[plugin],
                policy,
                dry_run=args.dry_run,
            )
        except RestoreAborted as e:
            logging.error(str(e))
            return 1
        except BatchApplyError as e:
            for op_str, err in e.errors:
                logging.error(f'{op_str}: {err}')
            return 1
        except Exception as e:
            logging.error(str(e))
            return 1

        clean_ops.append(calc_ops.clean_repo(manifest.get(plugin, [])))
        plugins[plugin].clean_data(manifest.get(plugin, []))

    for clean_op in clean_ops:
        try:
            clean_op.apply(args.dry_run, keep_going=policy.keep_going)
        except BatchApplyError as e:
            for op_str, err in e.errors:
                logging.error(f'{op_str}: {err}')
            return 1

    return 0


def clean_files(repo, filelist_obj, active_filelist, manifest, plugins, plugin_dirs, home, args):
    """Clean files from repository that are no longer managed"""
    clean_ops = []
    policy = from_args(args)

    for plugin in plugins:
        flist = plugin_filelist(active_filelist, plugin)
        if not flist:
            continue
        logging.debug(f'active filelist for plugin {plugin}: {flist}')

        plugin_dir = plugin_dirs[plugin]
        calc_ops = CalcOps(plugin_dir, home, plugins[plugin], policy=policy)

        try:
            calc_ops.clean(flist).apply(args.dry_run, keep_going=policy.keep_going)
        except BatchApplyError as e:
            for op_str, err in e.errors:
                logging.error(f'{op_str}: {err}')
            return 1
        except Exception as e:
            logging.error(str(e))
            return 1

        clean_ops.append(calc_ops.clean_repo(manifest.get(plugin, [])))
        plugins[plugin].clean_data(manifest.get(plugin, []))

    for clean_op in clean_ops:
        try:
            clean_op.apply(args.dry_run, keep_going=policy.keep_going)
        except BatchApplyError as e:
            for op_str, err in e.errors:
                logging.error(f'{op_str}: {err}')
            return 1

    return 0


def show_diff(repo, filelist, plugins, plugin_dirs, home, git, args):
    """Show differences between home and repository"""
    print('\n'.join(git.diff(ignore=['.plugins/'])))
    policy = from_args(args)

    for plugin in plugins:
        calc_ops = CalcOps(plugin_dirs[plugin], home, plugins[plugin], policy=policy)
        diff = calc_ops.diff(args.categories)
        
        if diff:
            print(f'\n{plugin}-plugin updates not yet in repo:')
            print('\n'.join(diff))
    
    return 0


def push_with_remote(git, no_push=False):
    """Push to remote; prompt for URL if origin is missing. Returns exit code."""
    if no_push:
        logging.warning(
            'Changes saved locally only (--no-push). '
            'Assets are not durable until pushed to a remote.'
        )
        return 0

    if not git.has_remote():
        url = input('No remote configured. Enter Git remote URL (or leave empty to skip): ')
        if not url.strip():
            logging.error('Aborted: no remote configured and push declined')
            return 1
        git.add_remote('origin', url.strip())

    try:
        git.push()
        logging.info('successfully pushed to git remote')
    except Exception as e:
        logging.error(f'Failed to push to remote: {e}')
        return 1
    return 0


def save_files(repo, filelist_obj, active_filelist, manifest, plugins, plugin_dirs, home, args, git):
    """Mirror home to repo, commit, and push by default."""
    result = update_files(
        repo, filelist_obj, active_filelist, manifest, plugins, plugin_dirs, home, args
    )
    if result != 0:
        return result

    if args.dry_run:
        if args.no_push:
            logging.info('[DRY RUN] Would git add, commit (no push)')
        else:
            logging.info('[DRY RUN] Would git add, commit, and push')
        return 0

    has_new_changes = git.has_changes()
    if not has_new_changes:
        logging.warning('no changes detected in repo, not creating commit')
        return push_with_remote(git, no_push=args.no_push)

    git.add()
    msg = args.commit_message or git.gen_commit_message(ignore=['.plugins/'])

    if not msg or msg.strip() == '':
        logging.warning('no valid changes to commit after filtering')
        git.reset()
        return push_with_remote(git, no_push=args.no_push)

    try:
        git.commit(msg)
    except Exception as e:
        logging.error(f'Failed to commit: {e}')
        git.reset()
        return 1

    return push_with_remote(git, no_push=args.no_push)


def commit_changes(repo, git):
    """Commit changes to git repository"""
    has_new_changes = git.has_changes()
    
    if not has_new_changes:
        logging.warning('no changes detected in repo, not creating commit')
        # Even if no new changes, check if there are unpushed commits to push
        if git.has_remote() and git.has_unpushed_commits():
            ans = input('No new changes, but you have unpushed commits. Push to remote? [Yn] ')
            ans = ans if ans else 'y'
            if ans.lower() == 'y':
                try:
                    git.push()
                    logging.info('successfully pushed to git remote')
                except Exception as e:
                    logging.error(f'Failed to push to remote: {e}')
                    return 1
        return 0
    
    git.add()
    msg = git.gen_commit_message(ignore=['.plugins/'])
    
    # Handle empty commit message (no valid changes after filtering)
    if not msg or msg.strip() == '':
        logging.warning('no valid changes to commit after filtering')
        git.reset()
        return 0
    
    try:
        git.commit(msg)
    except Exception as e:
        logging.error(f'Failed to commit: {e}')
        git.reset()
        return 1
    
    if git.has_remote():
        ans = input('remote for repo detected, push to remote? [Yn] ')
        ans = ans if ans else 'y'
        if ans.lower() == 'y':
            try:
                git.push()
                logging.info('successfully pushed to git remote')
            except Exception as e:
                logging.error(f'Failed to push to remote: {e}')
                return 1
    else:
        logging.info('No remote repository configured.')
        logging.info('To connect to GitHub:')
        logging.info('  1. Create a repository on GitHub')
        logging.info('  2. Run: git remote add origin git@github.com:USERNAME/REPO.git')
        logging.info('  3. Run: dotsync commit (will prompt to push)')
        logging.info('See README.md for more details.')
    
    return 0


def change_password(dotfiles, plugins):
    """Change encryption password for encrypted files"""
    logging.debug('attempting to change encryption password')
    repo = os.path.join(dotfiles, 'encrypt')
    
    if os.path.exists(repo):
        plugins['encrypt'].init_password()
        plugins['encrypt'].change_password(repo=repo)
    else:
        plugins['encrypt'].change_password()
    
    return 0


def setup_plugins_and_dirs(repo):
    """Setup plugins and plugin directories, return (plugins, plugin_dirs, dotfiles)"""
    dotfiles = os.path.join(repo, 'dotfiles')
    logging.debug(f'dotfiles path is {dotfiles}')
    
    plugins_data_dir = os.path.join(repo, '.plugins')
    plugins = {
        'plain': PlainPlugin(
            data_dir=os.path.join(plugins_data_dir, 'plain'),
            repo_dir=os.path.join(dotfiles, 'plain'),
            hard=False),  # Will be set from args if needed
        'encrypt': EncryptPlugin(
            data_dir=os.path.join(plugins_data_dir, 'encrypt'),
            repo_dir=os.path.join(dotfiles, 'encrypt'))
    }
    
    plugin_dirs = {plugin: os.path.join(dotfiles, plugin) for plugin in plugins}
    
    return plugins, plugin_dirs, dotfiles


def main(args=None, cwd=os.getcwd(), home=info.home):
    if args is None:
        args = sys.argv[1:]

    # parse cmd arguments
    args = Arguments(args)
    logging.basicConfig(format=logging.BASIC_FORMAT, level=args.verbose_level)
    logging.debug(f'ran with arguments {args}')

    # For init command, use specified directory or default to ~/.dotfiles or cwd
    # For track/add, bootstrap repo if missing; other commands require existing repo
    bootstrap_if_missing = args.action in (Actions.TRACK, Actions.ADD)

    if args.action == Actions.INIT:
        if hasattr(args, 'init_directory') and args.init_directory:
            # User specified a directory
            repo = os.path.abspath(os.path.expanduser(args.init_directory))
        else:
            # Check if current directory looks like it should be the repo
            # (for testing and explicit init in desired directory)
            current_has_git_or_filelist = (
                os.path.isdir(os.path.join(cwd, '.git')) or 
                os.path.exists(os.path.join(cwd, 'filelist'))
            )
            default_dotfiles = os.path.join(home, '.dotfiles')
            
            # If cwd is home directory, use ~/.dotfiles (safer)
            # Otherwise use cwd if it has git/filelist or is different from home
            if cwd == home:
                repo = default_dotfiles
            elif current_has_git_or_filelist or cwd != default_dotfiles:
                repo = cwd
            else:
                repo = default_dotfiles
        
        # Create directory if it doesn't exist
        if not os.path.exists(repo):
            try:
                os.makedirs(repo, exist_ok=True)
                logging.info(f'Created directory: {repo}')
            except OSError as e:
                logging.error(f'Failed to create directory {repo}: {e}')
                return 1
        elif not os.path.isdir(repo):
            logging.error(f'{repo} exists but is not a directory')
            return 1
    elif bootstrap_if_missing:
        found_repo = find_dotsync_repo(cwd, home)
        if found_repo is None:
            repo = bootstrap_repo(home)
            if repo is None:
                return 1
            logging.info(f'Bootstrapped dotsync repository at: {repo}')
        else:
            repo = found_repo
            logging.debug(f'Found dotsync repository at: {repo}')
    else:
        found_repo = find_dotsync_repo(cwd, home)
        if found_repo is None:
            logging.error('Could not find dotsync repository')
            logging.info('Search strategy:')
            logging.info('  1. Environment variable DOTSYNC_REPO')
            logging.info('  2. Upward search from current directory for .git and filelist')
            logging.info('  3. Default location ~/.dotfiles')
            logging.info('Run "dotsync init" in the directory where you want to create the repository')
            return 1
        repo = found_repo
        logging.debug(f'Found dotsync repository at: {repo}')
    
    flist_fname = os.path.join(repo, 'filelist')

    # run safety checks
    if not safety_checks(repo, home, args.action == Actions.INIT):
        logging.error(f'safety checks failed for {repo}, exiting')
        return 1

    # check for init
    if args.action == Actions.INIT:
        init_repo(repo, flist_fname)
        return 0

    # Setup plugins early for add command (needed for auto-update)
    plugins, plugin_dirs, dotfiles = setup_plugins_and_dirs(repo)
    plugins['plain'].hard = args.hard_mode

    # check for track / add (deprecated alias)
    if args.action in (Actions.TRACK, Actions.ADD):
        if args.action == Actions.ADD:
            logging.warning("'add' is deprecated; use 'track' instead")
        return add_to_filelist(
            flist_fname, args.add_filepath, args.add_category, home, 
            args.dry_run, args.verbose_level, 
            encrypt=args.encrypt,
            auto_update=not getattr(args, 'no_auto_update', False),
            repo=repo,
            plugins=plugins,
            plugin_dirs=plugin_dirs
        )

    # check for encrypt
    if args.action == Actions.ENCRYPT:
        if not args.add_filepath:
            logging.error('encrypt action requires filepath argument')
            return 1
        return encrypt_to_filelist(flist_fname, args.add_filepath, home, args.dry_run)

    # check for untrack / unmanage (deprecated alias)
    if args.action in (Actions.UNTRACK, Actions.UNMANAGE):
        if args.action == Actions.UNMANAGE:
            logging.warning("'unmanage' is deprecated; use 'untrack' instead")
        if not args.add_filepath:
            logging.error('untrack action requires filepath argument')
            return 1
        if args.purge_repo:
            logging.info('Purging mirrored files from repository')
        return unmanage_from_filelist(
            flist_fname, args.add_filepath, home, repo, plugins, plugin_dirs,
            args.dry_run, policy=from_args(args), purge_repo=args.purge_repo,
        )

    # check for list
    if args.action == Actions.LIST:
        return list_managed_files(flist_fname, args.categories, home)

    # check for categories
    if args.action == Actions.CATEGORIES:
        return show_categories(flist_fname)

    # Load filelist for other operations
    filelist_obj = load_filelist(flist_fname)
    if filelist_obj is None:
        return 1

    try:
        if args.action == Actions.RESTORE:
            active_filelist = prepare_active_filelist(
                filelist_obj, home, args.categories, plugin_dirs, from_repo=True,
            )
            manifest = filelist_obj.build_restore_manifest(
                plugin_dirs, args.categories, repo,
            )
        else:
            active_filelist = prepare_active_filelist(
                filelist_obj, home, args.categories, plugin_dirs, from_repo=False,
            )
            manifest = filelist_obj.manifest()
    except RuntimeError:
        logging.error(f'Error activating categories: {args.categories}')
        return 1

    # set up git interface
    git = Git(repo)

    # Route to appropriate command function
    if args.action == Actions.UPDATE:
        return update_files(
            repo, filelist_obj, active_filelist, manifest, plugins, plugin_dirs, home, args,
        )
    elif args.action == Actions.SAVE:
        return save_files(
            repo, filelist_obj, active_filelist, manifest, plugins, plugin_dirs, home, args, git,
        )
    elif args.action == Actions.RESTORE:
        return restore_files(
            repo, filelist_obj, active_filelist, manifest, plugins, plugin_dirs, home, args,
        )
    elif args.action == Actions.CLEAN:
        return clean_files(
            repo, filelist_obj, active_filelist, manifest, plugins, plugin_dirs, home, args,
        )
    elif args.action == Actions.DIFF:
        return show_diff(repo, active_filelist, plugins, plugin_dirs, home, git, args)
    elif args.action == Actions.COMMIT:
        return commit_changes(repo, git)
    elif args.action == Actions.PASSWD:
        return change_password(dotfiles, plugins)

    return 0


if __name__ == '__main__':
    sys.exit(main())
