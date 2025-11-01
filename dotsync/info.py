from os.path import expanduser
import socket

__version__ = '2.2.9'
__author__ = 'Harvey'
__author_email__ = 'harvey.wanghy@gmail.com'
__url__ = 'https://github.com/HarveyGG/dotsync'
__license__ = 'MIT License (Non-Commercial Use Only)'

home = expanduser('~')
hostname = socket.gethostname()
