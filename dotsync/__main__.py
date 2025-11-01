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
from dotsync.checks import safety_checks
from dotsync.flists import Filelist
from dotsync.git import Git
from dotsync.calc_ops import CalcOps
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


def handle_dest_file_conflict(repo_file, dest_file, repo, plugin, plugin_name=None, detailed_prompt=False):
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
    
    # Check if dest is a symlink to repo
    if os.path.islink(dest_file):
        link_target = os.readlink(dest_file)
        repo_abs = os.path.abspath(repo_file)
        # Try to resolve relative symlink
        try:
            resolved_target = os.path.abspath(os.path.join(os.path.dirname(dest_file), link_target))
        except:
            resolved_target = None
        # Check if symlink points to repo file
        if (os.path.abspath(link_target) == repo_abs or 
            (resolved_target and resolved_target == repo_abs) or
            link_target.startswith(repo + os.sep)):
            # Symlink to repo, safe to remove
            logging.info(f'Removing symlink to repo: {dest_file}')
            os.remove(dest_file)
            return (True, True)
        else:
            # Symlink to somewhere else
            logging.warning(f'{dest_file} is a symlink pointing to {link_target}')
            response = input('Remove this symlink? [Yn] ')
            response = 'y' if not response else response.lower()
            if response == 'y':
                os.remove(dest_file)
                return (True, True)
            else:
                return (False, False)  # Cancelled
    
    # Regular file exists - need to ask user
    if not os.path.exists(repo_file):
        # Repo file doesn't exist, can't compare
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
    
    if files_differ and detailed_prompt:
        # Detailed prompt with options
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
        # Simple prompt (default for restore)
        prompt = f'{dest_file} already exists'
        if files_differ is True:
            prompt += ' and differs from repository version'
        prompt += '. Replace? [Yn] '
        response = input(prompt)
        response = 'y' if not response else response.lower()
        if response == 'y':
            os.remove(dest_file)
            return (True, True)
        else:
            return (False, False)  # Cancelled


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
    root_dir = os.path.dirname(current_dir)
    
    # Traverse upward until we hit root or home directory
    while current_dir != root_dir and current_dir != home:
        filelist_path = os.path.join(current_dir, 'filelist')
        git_path = os.path.join(current_dir, '.git')
        
        # Check if this directory contains filelist (required for dotsync repo)
        # .git is optional but preferred for safety checks
        if os.path.exists(filelist_path):
            # Verify it's a dotsync repo (has .git or is in default location)
            if os.path.isdir(git_path) or current_dir == os.path.join(home, '.dotfiles'):
                return current_dir
        
        # Move to parent directory
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:  # Reached filesystem root
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
    
    # Normalize filepath
    normalized_path = normalize_filepath(filepath, home)
    if normalized_path is None:
        return 1
    
    # Reject system files
    basename = os.path.basename(normalized_path)
    if basename in SYSTEM_FILES:
        logging.error(f'Cannot manage system file: {normalized_path}')
        logging.info('System files like .DS_Store are automatically ignored')
        return 1
    
    # Check if file exists (skip prompt in dry-run mode)
    full_path = os.path.join(home, normalized_path)
    if dry_run:
        # In dry-run, just warn if file doesn't exist but continue
        if not os.path.exists(full_path):
            logging.warning(f'File does not exist: {full_path} (dry-run mode, continuing)')
    else:
        # In normal mode, prompt user if file doesn't exist
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
    new_entry = f'{normalized_path}:{category}{plugin_suffix}\n'
    
    # Check if already exists (check both with and without encrypt)
    if check_entry_exists_in_filelist(existing_lines, normalized_path, category):
        logging.warning(f'Entry already exists in filelist: {normalized_path}:{category}')
        return 1
    
    # If encrypt is requested, prompt for password interactively
    if encrypt and not dry_run:
        try:
            # Initialize encryption password by creating a temporary encrypt plugin
            # This will prompt for password
            from dotsync.plugins.encrypt import EncryptPlugin
            repo_dir = os.path.dirname(os.path.dirname(flist_fname)) if repo is None else repo
            encrypt_plugin = EncryptPlugin(
                data_dir=os.path.join(repo_dir, '.plugins', 'encrypt'),
                repo_dir=os.path.join(repo_dir, 'dotfiles', 'encrypt') if repo else None
            )
            encrypt_plugin.init_password()
            logging.info('Encryption password set')
        except Exception as e:
            logging.error(f'Failed to initialize encryption: {e}')
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


def unmanage_from_filelist(flist_fname, filepath, home, repo, plugins, plugin_dirs, dry_run):
    """Restore a configuration file to home directory and stop managing it"""
    
    # Normalize filepath
    normalized_path = normalize_filepath(filepath, home)
    if normalized_path is None:
        return 1
    
    # Load filelist
    filelist = load_filelist(flist_fname)
    if filelist is None:
        return 1
    
    # Check if file is in filelist
    if normalized_path not in filelist.files:
        logging.error(f'File {normalized_path} is not managed by dotsync')
        return 1
    
    # Get file instance to determine plugin and categories
    instances = filelist.files[normalized_path]
    if not instances:
        logging.error(f'File {normalized_path} has no valid configuration')
        return 1
    
    # Use the first instance (typically there's only one)
    instance = instances[0]
    plugin_name = instance['plugin']
    categories = instance['categories']
    
    # Determine repository file location
    master_category = min(categories)
    plugin_dir = plugin_dirs[plugin_name]
    repo_file = os.path.join(plugin_dir, master_category, normalized_path)
    
    # Check if repo file exists
    if not os.path.exists(repo_file):
        logging.warning(f'Repository file not found: {repo_file}')
        # Still proceed to remove from filelist
    
    # Check home directory file
    home_file = os.path.join(home, normalized_path)
    home_exists = os.path.exists(home_file) or os.path.islink(home_file)
    is_symlink = os.path.islink(home_file) if home_exists else False
    
    if dry_run:
        logging.info(f'[DRY RUN] Would unmanage {normalized_path}')
        if home_exists:
            if is_symlink:
                logging.info(f'  - Would remove symlink: {home_file}')
            else:
                logging.info(f'  - Would ask about existing file: {home_file}')
        if os.path.exists(repo_file):
            logging.info(f'  - Would copy/decrypt from repo: {repo_file} -> {home_file}')
        logging.info(f'  - Would remove from filelist')
        logging.info(f'  - Would clean up repository file')
        return 0
    
    # Handle home directory file conflict using shared logic
    plugin = plugins[plugin_name]
    should_proceed, should_copy = handle_dest_file_conflict(
        repo_file, home_file, repo, plugin, plugin_name=plugin_name, detailed_prompt=True
    )
    if not should_proceed:
        logging.info('Cancelled')
        return 1
    
    # After handle_dest_file_conflict, home_file might have been removed if it was a symlink
    # We always want to restore the file from repo (unless user chose to keep existing)
    # Copy/decrypt file from repository to home (only if we should)
    if should_copy and os.path.exists(repo_file):
        # Ensure parent directory exists
        home_dir = os.path.dirname(home_file)
        if home_dir and not os.path.exists(home_dir):
            os.makedirs(home_dir, exist_ok=True)
            logging.info(f'Created directory: {home_dir}')
        
        # Use plugin to copy/decrypt file
        plugin = plugins[plugin_name]
        try:
            if plugin_name == 'encrypt':
                # Decrypt file
                logging.info(f'Decrypting {normalized_path}...')
                plugin.init_password()  # Will prompt for password if needed
                plugin.remove(repo_file, home_file)
            else:
                # For unmanage, always copy file (don't create symlink)
                # Temporarily set hard mode to ensure copy
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
    
    # Remove from filelist
    existing_lines = read_filelist_lines(flist_fname)
    new_lines = []
    removed = False
    
    for line in existing_lines:
        stripped = line.strip()
        # Skip empty lines and comments
        if not stripped or stripped.startswith('#'):
            new_lines.append(line)
            continue
        
        # Check if this line is for our file
        parts = stripped.split(':')
        if len(parts) >= 1:
            file_path = parts[0].split('|')[0]  # Remove plugin suffix if present
            
            if file_path == normalized_path:
                # Skip this line (remove it)
                removed = True
                continue
        
        new_lines.append(line)
    
    if not removed:
        logging.warning(f'Could not find {normalized_path} in filelist')
        # Still proceed to clean up
    
    # Write updated filelist
    with open(flist_fname, 'w') as f:
        f.writelines(new_lines)
    
    logging.info(f'Removed {normalized_path} from filelist')
    
    # Clean up repository file
    if os.path.exists(repo_file):
        try:
            # Remove the file from repository
            os.remove(repo_file)
            logging.info(f'Removed repository file: {repo_file}')
            
            # Try to remove empty category directory
            category_dir = os.path.dirname(repo_file)
            if os.path.exists(category_dir) and not os.listdir(category_dir):
                os.rmdir(category_dir)
                logging.info(f'Removed empty category directory: {category_dir}')
        except Exception as e:
            logging.warning(f'Failed to clean up repository file: {e}')
    
    # Clean up plugin data if encrypted
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


def update_files(repo, filelist, manifest, plugins, plugin_dirs, home, args):
    """Update files from home to repository"""
    clean_ops = []
    
    for plugin in plugins:
        flist = {path: filelist[path]['categories'] for path in filelist if
                 filelist[path]['plugin'] == plugin}
        if not flist:
            continue
        logging.debug(f'active filelist for plugin {plugin}: {flist}')
        
        plugin_dir = plugin_dirs[plugin]
        calc_ops = CalcOps(plugin_dir, home, plugins[plugin])
        
        calc_ops.update(flist).apply(args.dry_run)
        calc_ops.restore(flist).apply(args.dry_run)
        
        clean_ops.append(calc_ops.clean_repo(manifest[plugin]))
        plugins[plugin].clean_data(manifest[plugin])
    
    for clean_op in clean_ops:
        clean_op.apply(args.dry_run)
    
    return 0


def restore_files(repo, filelist, manifest, plugins, plugin_dirs, home, args):
    """Restore files from repository to home"""
    clean_ops = []
    
    for plugin in plugins:
        flist = {path: filelist[path]['categories'] for path in filelist if
                 filelist[path]['plugin'] == plugin}
        if not flist:
            continue
        logging.debug(f'active filelist for plugin {plugin}: {flist}')
        
        plugin_dir = plugin_dirs[plugin]
        calc_ops = CalcOps(plugin_dir, home, plugins[plugin])
        
        calc_ops.restore(flist).apply(args.dry_run)
        
        clean_ops.append(calc_ops.clean_repo(manifest[plugin]))
        plugins[plugin].clean_data(manifest[plugin])
    
    for clean_op in clean_ops:
        clean_op.apply(args.dry_run)
    
    return 0


def clean_files(repo, filelist, manifest, plugins, plugin_dirs, home, args):
    """Clean files from repository that are no longer managed"""
    clean_ops = []
    
    for plugin in plugins:
        flist = {path: filelist[path]['categories'] for path in filelist if
                 filelist[path]['plugin'] == plugin}
        if not flist:
            continue
        logging.debug(f'active filelist for plugin {plugin}: {flist}')
        
        plugin_dir = plugin_dirs[plugin]
        calc_ops = CalcOps(plugin_dir, home, plugins[plugin])
        
        calc_ops.clean(flist).apply(args.dry_run)
        
        clean_ops.append(calc_ops.clean_repo(manifest[plugin]))
        plugins[plugin].clean_data(manifest[plugin])
    
    for clean_op in clean_ops:
        clean_op.apply(args.dry_run)
    
    return 0


def show_diff(repo, filelist, plugins, plugin_dirs, home, git, args):
    """Show differences between home and repository"""
    print('\n'.join(git.diff(ignore=['.plugins/'])))
    
    for plugin in plugins:
        calc_ops = CalcOps(plugin_dirs[plugin], home, plugins[plugin])
        diff = calc_ops.diff(args.categories)
        
        if diff:
            print(f'\n{plugin}-plugin updates not yet in repo:')
            print('\n'.join(diff))
    
    return 0


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
    # For other commands, automatically find repository
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

    # check for add
    if args.action == Actions.ADD:
        return add_to_filelist(
            flist_fname, args.add_filepath, args.add_category, home, 
            args.dry_run, args.verbose_level, 
            encrypt=args.encrypt,
            auto_update=True,  # Always auto-update after add
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

    # check for unmanage
    if args.action == Actions.UNMANAGE:
        if not args.add_filepath:
            logging.error('unmanage action requires filepath argument')
            return 1
        return unmanage_from_filelist(flist_fname, args.add_filepath, home, repo, plugins, plugin_dirs, args.dry_run)

    # check for list
    if args.action == Actions.LIST:
        return list_managed_files(flist_fname, args.categories, home)

    # Load filelist for other operations
    filelist = load_filelist(flist_fname)
    if filelist is None:
        return 1
    
    # generate manifest for later cleaning
    manifest = filelist.manifest()
    # activate categories on filelist
    try:
        filelist = filelist.activate(args.categories)
    except RuntimeError:
        logging.error(f'Error activating categories: {args.categories}')
        return 1

    # set up git interface
    git = Git(repo)

    # Route to appropriate command function
    if args.action == Actions.UPDATE:
        return update_files(repo, filelist, manifest, plugins, plugin_dirs, home, args)
    elif args.action == Actions.RESTORE:
        return restore_files(repo, filelist, manifest, plugins, plugin_dirs, home, args)
    elif args.action == Actions.CLEAN:
        return clean_files(repo, filelist, manifest, plugins, plugin_dirs, home, args)
    elif args.action == Actions.DIFF:
        return show_diff(repo, filelist, plugins, plugin_dirs, home, git, args)
    elif args.action == Actions.COMMIT:
        return commit_changes(repo, git)
    elif args.action == Actions.PASSWD:
        return change_password(dotfiles, plugins)

    return 0


if __name__ == '__main__':
    sys.exit(main())
