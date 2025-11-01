import setuptools
import dotsync.info as info

with open('README.md', 'r') as readme:
    long_description = readme.read()

setuptools.setup(
        name = 'dotsync',
        version = info.__version__,
        author = info.__author__,
        author_email = info.__author_email__,
        description = 'A comprehensive solution to managing your dotfiles',
        long_description = long_description,
        long_description_content_type = 'text/markdown',
        url = info.__url__,
        project_urls = {
            'Documentation': 'https://dotsync.readthedocs.io',
        },
        license = info.__license__,
        packages = ['dotsync', 'dotsync.plugins'],
        entry_points = {
            'console_scripts': ['dotsync=dotsync.__main__:main']
            },
        include_package_data = True,
        classifiers = [
            'Development Status :: 5 - Production/Stable',
            'Programming Language :: Python :: 3',
            'License :: Other/Proprietary License',
            'Operating System :: POSIX',
            'Operating System :: MacOS',
            'Topic :: Utilities',
            ],
        python_requires = '>=3.8',
        )
