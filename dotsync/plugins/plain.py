import os
import shutil
import filecmp

from dotsync.plugin import Plugin


class PlainPlugin(Plugin):
    def __init__(self, *args, **kwargs):
        self.hard = kwargs.pop('hard', False)
        super().__init__(*args, **kwargs)

    def setup_data(self):
        pass

    # copies file from outside the repo to the repo
    def apply(self, source, dest):
        shutil.copy2(source, dest)

    def remove(self, source, dest):
        shutil.copy2(source, dest)

    def samefile(self, repo_file, ext_file):
        if os.path.islink(ext_file):
            return os.path.realpath(ext_file) == os.path.abspath(repo_file)
        if not os.path.exists(repo_file):
            return False
        return filecmp.cmp(repo_file, ext_file, shallow=False)

    def strify(self, op):
        if op == self.apply:
            return "COPY"
        elif op == self.remove:
            return "COPY"
        return ""
