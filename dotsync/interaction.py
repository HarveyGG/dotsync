import difflib
import os


def collect_filelist_categories(filelist):
    """Return sorted unique category names from a Filelist."""
    categories = set()
    for instances in filelist.files.values():
        for instance in instances:
            categories.update(instance['categories'])
    for group_cats in filelist.groups.values():
        categories.update(group_cats)
    for tree in filelist.trees:
        categories.update(tree['categories'])
    return sorted(categories)


def prompt_category_selection(categories, default_group=None):
    """Interactively pick one or more categories from a numbered checklist."""
    if not categories:
        print('No categories found in filelist.')
        return []

    print('\nAvailable categories:')
    for i, cat in enumerate(categories, 1):
        hint = ''
        if default_group and cat in default_group:
            hint = ' (recommended for this machine)'
        print(f'  [{i}] {cat}{hint}')
    print('  [a] All categories')
    print()

    while True:
        raw = input(
            'Select categories (numbers, names, comma-separated, or "a"): '
        ).strip()
        if not raw:
            print('Please select at least one category.')
            continue
        if raw.lower() in ('a', 'all'):
            return list(categories)

        selected = []
        invalid = False
        for part in raw.split(','):
            part = part.strip()
            if not part:
                continue
            if part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(categories):
                    selected.append(categories[idx])
                else:
                    print(f'Invalid number: {part}')
                    invalid = True
                    break
            elif part in categories:
                selected.append(part)
            else:
                print(f'Unknown category: {part}')
                invalid = True
                break

        if invalid:
            continue
        if not selected:
            print('Please select at least one category.')
            continue

        seen = set()
        result = []
        for cat in selected:
            if cat not in seen:
                seen.add(cat)
                result.append(cat)
        return result


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
