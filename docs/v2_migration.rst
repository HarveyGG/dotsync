============================
Migrating to v2 (mirror-only)
============================

dotsync v2 replaces the v1 "move to repo + symlink home" model with
**mirror-only** semantics:

* **Home is authoritative** — edit files in ``$HOME`` as usual
* **`save`** copies home → repo, commits, and pushes by default
* **`restore`** pulls latest, then copies repo → home
* **No dotsync-created symlinks in ``$HOME``**

If you are on a fresh install, skip to :doc:`getting_started`. This page is for
users upgrading from v1 link mode or older workflows.

Why migration is needed
=======================

v1 ``restore`` could leave symlinks in ``$HOME`` pointing into
``~/.dotfiles``. v2 ``save`` reads home path content directly; symlinks into
the repo cause ambiguous reads and are out of scope for the dotsync CLI.

**dotsync v2 does not convert legacy home symlinks.** Use the repository script
below once before adopting v2.

Step 1: Unsymlink home paths
============================

From the dotsync repository checkout (or copy the script from this repo)::

   python3 scripts/unsymlink_dotfiles_home.py --dry-run
   python3 scripts/unsymlink_dotfiles_home.py --apply

Environment variables:

* ``DOTSYNC_REPO`` — repo path (default ``~/.dotfiles``)
* ``HOME`` — home directory (default from the environment)

For each path in ``filelist``, if ``$HOME/<path>`` is a symlink whose target
lies **inside** the dotfiles repo, the script replaces the symlink with a
regular file (content copied from the target). It skips:

* Paths that are not symlinks
* Symlinks whose targets are outside the repo
* Symlink-to-directory edge cases (reported as skip)

Always run ``--dry-run`` first and review the output.

Step 2: Adopt v2 commands
=========================

Replace v1 habits with the v2 lifecycle:

+---------------------------+------------------------------------------+
| v1                        | v2                                       |
+===========================+==========================================+
| ``init``                  | implicit in ``track`` / ``restore``      |
+---------------------------+------------------------------------------+
| ``add`` / ``unmanage``    | ``track`` / ``untrack``                  |
+---------------------------+------------------------------------------+
| ``update`` + ``commit``   | ``save`` (mirror + commit + push)        |
+---------------------------+------------------------------------------+
| ``scan``                  | part of ``save`` (``@tree`` walk)        |
+---------------------------+------------------------------------------+
| ``diff``                  | ``git -C ~/.dotfiles diff`` or           |
|                           | ``save --dry-run``                       |
+---------------------------+------------------------------------------+
| ``clean``                 | ``untrack --purge-repo``                 |
+---------------------------+------------------------------------------+
| manual ``git clone``      | ``dotsync restore`` wizard               |
+---------------------------+------------------------------------------+

Example after migration::

   dotsync track ~/.zshrc shell    # if not already in filelist
   dotsync save
   dotsync restore               # on another machine

Step 3: Add ``@tree`` entries (optional)
========================================

For directories that change over time, replace per-file entries with tree
lines in ``filelist``::

   @tree:.config/nvim:editor
   @tree:.local/share/my-tool/custom-*:tools

Run ``dotsync save`` to expand and mirror the tree.

Command reference
=================

See :doc:`usage` for ``track``, ``untrack``, ``list``, ``categories``,
``save``, ``restore``, ``passwd``, and ``showpw``.

Older docs
==========

:doc:`migration_v1` covers migration from the original bash dotsync to the
Python rewrite (repo layout change). That is separate from the v2 mirror-only
model described here.
