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
