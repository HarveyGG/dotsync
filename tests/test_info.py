from os.path import expanduser

import dotsync.info

class TestInfo:
    def test_home(self):
        assert dotsync.info.home == expanduser('~')
