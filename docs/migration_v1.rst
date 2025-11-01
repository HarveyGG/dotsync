===================
Migration from v1.x
===================

Reasons for rewriting
=====================

After many years dotsync was finally completely rewritten in python. The first
version was written in pure bash, and while this was appealing at first it
quickly became a nightmare from a maintenance point-of-view. The new python
rewrite comes with many advantages including:

* Much better cross-platform compatibility, especially for MacOS and friends.
  Using utilities like ``find`` became problematic between different
  environments
* A fully automated test suite to test dotsync on both Linux and MacOS
* Code that the author can understand after not seeing it for a week
* Unified install method (pip) for all the platforms

Differences between the old and the new
=======================================

After much consideration it was decided to rather to not re-implement the
directory support, which is the only major change functionality wise from the
first version. It requires a lot of special treatment that breaks some of the
logic that works very well for single files which lead to weird bugs and
behaviour in the first version. Excluding it made the file-handling logic much
more robust and the behaviour surrounding the handling of files is much more
predictable.

Sticking with the old version
=============================

Should you decide you'd like to stick to the old version of dotsync, you are
welcome to do so. Installing the pip package will also make the original dotsync
available as the command ``dotsync.sh`` (AUR package includes this as well).
Please note that I will not be able to support the old version anymore, and as
such you're on your own if you decide to use the old version.

Migrating to the new version
============================

To make room for future improvements, the layout of the dotsync dotfiles repos
had to change. Unfortunately this means that the new repos are not directly
compatible with the old ones, although it is easy to migrate to the new
version's format. To do so, do the following:

1. Firstly, backup your current dotfiles repo in case something goes wrong
2. Next, do a hard restore using the old dotsync so that it copies all your
   files from your repo to your home folder using ``dotsync.sh hard-restore``
3. Now, delete your old dotsync files inside your repo as well as your
   cryptlist (which signals to dotsync that you are using the old version) using
   ``rm -rf dotfiles dmz cryptlist passwd``. Encrypted files are now specified
   using the new plugin syntax (see :doc:`filelist`), so add them to your
   original filelist using the new syntax.
4. With the new version of dotsync, first run ``dotsync init -v`` and then run
   ``dotsync update -v``. This will store the files from your home folder back
   in your repo in their new locations. If you have encrypted files this will
   also ask for your new encryption password
5. Commit the changes to your repo using either git or ``dotsync commit``
6. Familiarize yourself with the new dotsync command-line interface which has
   changed slightly to better follow conventions commonly found on the
   command-line by having a look at the usage section in ``dotsync -h``
