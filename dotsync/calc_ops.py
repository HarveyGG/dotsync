import os
import logging

from dotsync.file_ops import FileOps


class CalcOps:
    def __init__(self, repo, restore_path, plugin):
        self.repo = str(repo)
        self.restore_path = str(restore_path)
        self.plugin = plugin

    def update(self, files):
        fops = FileOps(self.repo)

        for path in files:
            categories = files[path]

            master = min(categories)
            slaves = [c for c in categories if c != master]

            # checks if a candidate exists and also checks if the candidate is
            # a link so that its resolved path can be used
            original_path = {}

            def check_cand(cand):
                cand = os.path.join(cand, path)
                if os.path.isfile(cand):
                    if os.path.islink(cand):
                        old = cand
                        cand = os.path.realpath(cand)
                        original_path[cand] = old
                    return [cand]
                return []

            candidates = []
            candidates += check_cand(self.restore_path)

            # candidate not found in restore path, so check elsewhere
            if not candidates:
                for cand in [os.path.join(self.repo, c) for c in categories]:
                    candidates += check_cand(cand)
            else:
                logging.debug(f'"{path}" found in restore path, so overriding '
                              'any other candidates')

            if not candidates:
                logging.warning(f'unable to find any candidates for "{path}"')
                continue

            candidates = list(set(candidates))
            if len(candidates) > 1:
                print(f'multiple candidates found for {path}:\n')

                for i, cand in enumerate(candidates):
                    print(f'[{i}] {cand}')
                print('[-1] cancel')

                while True:
                    try:
                        choice = int(input('please select the version you '
                                           'would like to use '
                                           f'[0-{len(candidates)-1}]: '))
                        choice = candidates[choice]
                    except (ValueError, EOFError):
                        print('invalid choice entered, please try again')
                        continue
                    break
                source = choice

                # if one of the candidates is not in the repo and it is not the
                # source it should be deleted manually since it will not be
                # deleted in the slave linking below, as the other candidates
                # would be
                restore_path = os.path.join(self.restore_path, path)
                if restore_path in candidates and source != restore_path:
                    fops.remove(restore_path)

            else:
                source = candidates.pop()

            master = os.path.join(self.repo, master, path)
            slaves = [os.path.join(self.repo, s, path) for s in slaves]

            if source != master and not self.plugin.samefile(master, source):
                if os.path.exists(master):
                    fops.remove(master)
                # check if source is in repo, if it is not apply the plugin
                if source.startswith(self.repo + os.sep):
                    # if the source is one of the slaves, move the source
                    # otherwise just copy it because it might have changed into
                    # a seperate category - cleanup will remove it if needed
                    if source in slaves:
                        fops.move(source, master)
                    else:
                        fops.copy(source, master)
                else:
                    fops.plugin(self.plugin.apply, source, master)
                    if source in original_path:
                        fops.remove(original_path[source])
                    else:
                        fops.remove(source)

            for slave in slaves:
                if slave != source:
                    if os.path.isfile(slave) or os.path.islink(slave):
                        if os.path.realpath(slave) != master:
                            fops.remove(slave)
                        else:
                            # already linked to master so just ignore
                            continue
                fops.link(master, slave)

        return fops

    def restore(self, files):
        fops = FileOps(self.repo)

        for path in files:
            categories = files[path]
            master = min(categories)
            source = os.path.join(self.repo, master, path)

            if not os.path.exists(source):
                logging.debug(f'{source} not found in repo')
                logging.warning(f'unable to find "{path}" in repo, skipping')
                continue

            dest = os.path.join(self.restore_path, path)

            # Use shared conflict handling logic
            # Import here to avoid circular imports
            import sys
            import os as os_module
            # Get the repo root by going up from repo path
            repo_root = os_module.path.dirname(os_module.path.dirname(self.repo))
            
            # Import handle_dest_file_conflict from __main__ if available
            # For now, use inline simplified version that matches restore behavior
            should_proceed, should_copy = self._handle_restore_conflict(source, dest)
            
            if not should_proceed:
                continue
            if not should_copy:
                # Files are same, skip
                continue

            fops.plugin(self.plugin.remove, source, dest)

        return fops
    
    def _handle_restore_conflict(self, source, dest):
        """Handle conflict for restore operation (simpler than unmanage)"""
        if not os.path.exists(dest):
            # Check for dangling symlink
            if os.path.islink(dest):
                os.remove(dest)
            return (True, True)
        
        # Check if files are the same
        try:
            if self.plugin.samefile(source, dest):
                logging.debug(f'{dest} is the same file as in the repo, skipping')
                return (True, False)  # Skip, don't copy
        except Exception:
            pass
        
        # Check if dest is a symlink to repo
        if os.path.islink(dest):
            link_target = os.readlink(dest)
            repo_abs = os.path.abspath(source)
            if os.path.abspath(link_target) == repo_abs or link_target.startswith(os.path.dirname(os.path.dirname(self.repo)) + os.sep):
                # Symlink to repo, safe to remove
                logging.info(f'{dest} already linked to repo, replacing with new file')
                os.remove(dest)
                return (True, True)
            else:
                # Symlink to somewhere else, ask user (restore behavior)
                a = input(f'{dest} already exists, replace? [Yn] ')
                a = 'y' if not a else a
                if a.lower() == 'y':
                    os.remove(dest)
                    return (True, True)
                else:
                    return (False, False)  # Cancelled
        
        # Regular file exists - simple prompt for restore
        a = input(f'{dest} already exists, replace? [Yn] ')
        a = 'y' if not a else a
        if a.lower() == 'y':
            os.remove(dest)
            return (True, True)
        else:
            return (False, False)  # Cancelled

    # removes links from restore path that point to the repo
    def clean(self, files):
        fops = FileOps(self.repo)

        for path in files:
            categories = files[path]
            master = min(categories)
            repo_path = os.path.join(self.repo, master, path)

            restore_path = os.path.join(self.restore_path, path)

            if os.path.exists(repo_path) and os.path.exists(restore_path):
                if self.plugin.samefile(repo_path, restore_path):
                    fops.remove(restore_path)

        return fops

    # will go through the repo and search for files that should no longer be
    # there. accepts a list of filenames that are allowed
    def clean_repo(self, filenames):
        fops = FileOps(self.repo)

        if not os.path.isdir(self.repo):
            return fops

        # System files to ignore (e.g., macOS .DS_Store, Windows Thumbs.db)
        SYSTEM_FILES = {'.DS_Store', 'Thumbs.db', '.DS_Store?'}

        for category in os.listdir(self.repo):
            # Skip system files
            if category in SYSTEM_FILES:
                continue

            category_path = os.path.join(self.repo, category)

            # Skip if not a directory (shouldn't happen, but be safe)
            if not os.path.isdir(category_path):
                continue

            # remove empty category folders
            try:
                if not os.listdir(category_path):
                    logging.info(f'{category} is empty, removing')
                    fops.remove(category)
                    continue
            except (OSError, NotADirectoryError):
                # If listdir fails, skip this entry
                continue

            for root, dirs, files in os.walk(category_path):
                # Filter out system files from directories list
                dirs[:] = [d for d in dirs if d not in SYSTEM_FILES]

                # remove empty directories
                for dname in dirs:
                    dname = os.path.join(root, dname)
                    if os.path.isdir(dname):
                        try:
                            if not os.listdir(dname):
                                dname = os.path.relpath(dname, self.repo)
                                logging.info(f'{dname} is empty, removing')
                                fops.remove(dname)
                        except (OSError, NotADirectoryError):
                            continue

                # remove files that are not in the manifest
                for fname in files:
                    # Skip system files
                    if fname in SYSTEM_FILES:
                        continue
                    fname = os.path.relpath(os.path.join(root, fname),
                                            self.repo)
                    if fname not in filenames:
                        logging.info(f'{fname} is not in the manifest, '
                                     'removing')
                        fops.remove(fname)

        return fops

    # goes through the filelist and finds files that have modifications that
    # are not yet in the repo e.g. changes to encrypted files. This should not
    # be used for any calculations, only for informational purposes
    def diff(self, categories):
        diffs = []
        for category in categories:
            category_path = os.path.join(self.repo, category)

            for root, dirs, files in os.walk(category_path):
                for fname in files:
                    fname = os.path.join(root, fname)
                    fname = os.path.relpath(fname, category_path)

                    restore_file = os.path.join(self.restore_path, fname)
                    category_file = os.path.join(category_path, fname)

                    if not os.path.exists(restore_file):
                        continue

                    logging.debug(f'checking diff samefile for {restore_file}')
                    if not self.plugin.samefile(category_file, restore_file):
                        diffs.append(f'modified {restore_file}')

        return diffs
