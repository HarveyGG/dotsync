import os
import re
import subprocess
import shlex
import logging
import enum
from collections import Counter


class GitPullError(Exception):
    pass


class FileState(enum.Enum):
    MODIFIED = 'M'
    ADDED = 'A'
    DELETED = 'D'
    RENAMED = 'R'
    COPIED = 'C'
    UPDATED = 'U'
    UNTRACKED = '?'


MAX_PATHS_IN_COMMIT_MESSAGE = 3
_DOTFILES_CATEGORY_RE = re.compile(
    r'^dotfiles/(?:plain|encrypt)/([^/]+)/'
)


def _commit_path_label(path):
    """Shorten repo paths for commit messages."""
    match = _DOTFILES_CATEGORY_RE.match(path)
    if match:
        return path[match.end():]
    if path.startswith('dotfiles/'):
        return path[len('dotfiles/'):]
    return path


def _infer_dotfiles_category(paths):
    categories = set()
    for path in paths:
        match = _DOTFILES_CATEGORY_RE.match(path)
        if match:
            categories.add(match.group(1))
    if len(categories) == 1:
        return categories.pop()
    return None


def _format_change_counts(changes):
    order = (
        FileState.ADDED,
        FileState.MODIFIED,
        FileState.DELETED,
        FileState.RENAMED,
        FileState.COPIED,
        FileState.UPDATED,
    )
    counts = Counter(state for state, _ in changes)
    parts = []
    for state in order:
        count = counts.get(state, 0)
        if count:
            parts.append(f'{count} {state.name.lower()}')
    return ', '.join(parts)


class Git:
    def __init__(self, repo_dir):
        if not os.path.isdir(repo_dir):
            raise FileNotFoundError

        self.repo_dir = repo_dir

    @classmethod
    def clone(cls, url, dest_dir):
        """Clone a remote repository into dest_dir and return a Git handle."""
        if os.path.exists(dest_dir):
            raise FileExistsError(f'{dest_dir} already exists')
        parent = os.path.dirname(dest_dir)
        if parent:
            os.makedirs(parent, exist_ok=True)
        logging.info(f'cloning {url} to {dest_dir}')
        try:
            subprocess.run(
                ['git', 'clone', url, dest_dir],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except subprocess.CalledProcessError as e:
            err = (e.stderr or b'').decode().strip()
            raise GitPullError(f'git clone failed: {err}') from e
        return cls(dest_dir)

    def run(self, cmd):
        if type(cmd) is not list:
            cmd = shlex.split(cmd)
        logging.info(f'running git command {cmd}')
        try:
            proc = subprocess.run(cmd, cwd=self.repo_dir,
                                  stdout=subprocess.PIPE, check=True)
        except subprocess.CalledProcessError as e:
            logging.error(e.stdout.decode())
            logging.error(f'git command {cmd} failed with exit code '
                          f'{e.returncode}\n')
            raise
        logging.debug(f'git command {cmd} succeeded')
        return proc.stdout.decode()

    def init(self):
        self.run('git init')

    def reset(self, fname=None):
        self.run('git reset' if fname is None else f'git reset {fname}')

    def add(self, fname=None):
        self.run('git add --all' if fname is None else f'git add {fname}')

    def commit(self, message=None):
        if message is None:
            message = self.gen_commit_message()
        return self.run(['git', 'commit', '-m', message])

    def status(self, staged=True):
        out = self.run('git status --porcelain').strip()
        status = []
        
        # Handle empty output
        if not out:
            return status
        
        for line in out.split('\n'):
            # Skip empty lines
            if not line.strip():
                continue
            
            # git status --porcelain format: XY filename
            # X = staged state, Y = working tree state
            # Both can be: M=modified, A=added, D=deleted, R=renamed, C=copied, U=updated, ?=untracked
            # Space means no change in that area
            if len(line) < 3:
                logging.warning(f'Unexpected git status line format: {line}')
                continue
            
            state_chars = line[:2]
            path = line[3:].strip() if len(line) > 3 else ''
            
            # Handle special cases that don't follow XY format
            if state_chars in ['!!', '##']:
                continue
            
            # Extract stage and work states
            stage_char = state_chars[0]
            work_char = state_chars[1]
            
            # Choose which state to use based on staged parameter
            # If preferred state is space, try the other one
            if staged:
                state_char = stage_char if stage_char != ' ' else work_char
            else:
                state_char = work_char if work_char != ' ' else stage_char
            
            # Skip if both states are spaces (no change)
            if state_char == ' ':
                continue
            
            # Only process if we have a valid path
            if not path:
                continue
            
            try:
                file_state = FileState(state_char)
            except ValueError:
                # Handle unknown states gracefully (might be submodule states, etc.)
                logging.debug(f'Unknown file state: {state_char} in line: {line}, skipping')
                continue
            
            status.append((file_state, path))
        
        return sorted(status, key=lambda s: s[1])

    def has_changes(self):
        return bool(self.run('git status -s --porcelain').strip())

    def gen_commit_message(self, ignore=[]):
        changes = []
        for stat in self.status():
            state, path = stat
            # skip all untracked files since they will not be committed
            if state == FileState.UNTRACKED:
                continue
            if any((path.startswith(p) for p in ignore)):
                logging.debug(f'ignoring {path} from commit message')
                continue
            changes.append((state, path))

        if not changes:
            return ''

        if len(changes) == 1:
            state, path = changes[0]
            return f'{state.name.capitalize()} {_commit_path_label(path)}'

        if len(changes) <= MAX_PATHS_IN_COMMIT_MESSAGE:
            parts = [
                f'{state.name.lower()} {_commit_path_label(path)}'
                for state, path in changes
            ]
            return ', '.join(parts).capitalize()

        category = _infer_dotfiles_category(path for _, path in changes)
        prefix = f'Update {category}' if category else 'Update dotfiles'
        summary = _format_change_counts(changes)
        return f'{prefix}: {len(changes)} files ({summary})'

    def commits(self):
        return self.run('git log -1 --pretty=%s').strip().split('\n')

    def last_commit(self):
        return self.commits()[-1]

    def has_remote(self):
        return bool(self.run('git remote').strip())

    def head_sha(self):
        return self.run('git rev-parse HEAD').strip()

    def fetch(self):
        self.run('git fetch')

    def pull_ff_only(self):
        try:
            self.fetch()
            self.run('git pull --ff-only')
        except subprocess.CalledProcessError as e:
            output = getattr(e, 'output', None) or getattr(e, 'stdout', b'') or b''
            raise GitPullError(output.decode().strip()) from e
        return self.head_sha()

    def add_remote(self, name, url):
        self.run(['git', 'remote', 'add', name, url])

    def push(self):
        branch = self.run('git rev-parse --abbrev-ref HEAD').strip()
        try:
            self.run('git rev-parse --abbrev-ref @{upstream}')
        except subprocess.CalledProcessError:
            self.run(['git', 'push', '-u', 'origin', branch])
        else:
            self.run('git push')

    def has_unpushed_commits(self):
        """Check if there are commits that haven't been pushed to remote"""
        if not self.has_remote():
            return False
        try:
            branch = self.run('git rev-parse --abbrev-ref HEAD').strip()
            result = self.run(f'git rev-list --left-right --count {branch}...origin/{branch}')
            if result.strip():
                ahead, behind = map(int, result.strip().split('\t'))
                return ahead > 0
            return False
        except subprocess.CalledProcessError:
            # Remote branch might not exist yet, check if we have any commits
            try:
                return bool(self.run('git log --oneline').strip())
            except subprocess.CalledProcessError:
                return False

    def diff(self, ignore=[]):
        if not self.has_changes():
            return ['no changes']

        self.add()
        status = self.status()
        self.reset()

        diff = []

        for path in status:
            # ignore the paths specified in ignore
            if any((path[1].startswith(i) for i in ignore)):
                continue
            diff.append(f'{path[0].name.lower()} {path[1]}')

        return diff
