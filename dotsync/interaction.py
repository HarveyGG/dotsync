import difflib
import os


def show_restore_diff(source_path, dest_path):
    """Show unified diff between home dest and repo source, or a binary summary."""
    try:
        with open(source_path, 'rb') as f:
            source_bytes = f.read()
        with open(dest_path, 'rb') as f:
            dest_bytes = f.read()
    except OSError:
        print(f'Cannot compare {dest_path} with repository version')
        return

    if b'\0' in source_bytes or b'\0' in dest_bytes:
        print(f'Binary files differ: {dest_path}')
        return

    source_lines = source_bytes.decode('utf-8', errors='replace').splitlines(keepends=True)
    dest_lines = dest_bytes.decode('utf-8', errors='replace').splitlines(keepends=True)
    diff = difflib.unified_diff(
        dest_lines,
        source_lines,
        fromfile=f'home/{os.path.basename(dest_path)}',
        tofile=f'repo/{os.path.basename(source_path)}',
    )
    for line in diff:
        print(line, end='')


def prompt_restore_overwrite_or_cancel(dest_path):
    """Prompt to overwrite home file or cancel the entire restore."""
    print(f'\n{dest_path} differs from repository version.')
    while True:
        choice = input('[o] Overwrite  [c] Cancel restore: ').strip().lower()
        if choice in ('o', 'overwrite'):
            return True
        if choice in ('c', 'cancel'):
            return False
        print('Invalid choice, please enter o or c')


def decide_candidate(candidates, policy, restore_path_file, master_path):
    if len(candidates) <= 1:
        return candidates[0] if candidates else None
    if not policy.non_interactive:
        return None
    if policy.candidate == 'abort' or policy.candidate == 'prompt':
        return None
    if policy.candidate == 'prefer-home':
        for c in candidates:
            if c == restore_path_file:
                return c
    if policy.candidate == 'prefer-master' and master_path:
        for c in candidates:
            if c == master_path:
                return c
    return candidates[0]


def decide_conflict(dest_exists, is_symlink, samefile, policy):
    if not dest_exists:
        return (True, True)
    if samefile:
        return (True, False)
    if not policy.non_interactive:
        return None
    if policy.conflict == 'overwrite':
        return (True, True)
    if policy.conflict == 'keep':
        return (True, False)
    return (False, False)
