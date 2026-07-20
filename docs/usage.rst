=====
Usage
=====

The basic usage syntax looks like this::

   dotsync [flags] {action} [category [category]]

Where ``action`` is one of the lifecycle commands below and ``category`` is one
or more categories or groups to activate. If no categories are specified,
dotsync automatically activates the ``common`` category as well as a category
with your machine's hostname.

v2 is **mirror-only**: home paths are the source of truth; the repo holds
copies. dotsync never installs symlinks from ``$HOME`` into the repository.

Using categories
================

When you run dotsync, actions are limited to the categories that are active.
If you don't specify any categories the default is ``common`` plus your
hostname (e.g. ``my-laptop``).

Files in the filelist that are not part of active categories are ignored. Run
with ``-vv`` to see which categories are active.

Flags
=====

.. option:: -h, --help

   Display a help message

.. option:: -v, --verbose

   Increase verbosity. Can be specified multiple times (``-vv`` for debug).

   .. note::

      Run with at least one ``-v`` flag — otherwise output is minimal unless
      there is an error.

.. option:: --dry-run

   Print planned operations without changing the filesystem. Useful with
   ``save`` and ``restore``.

.. option:: --yes, -y

   Non-interactive mode; skip confirmation prompts.

.. option:: --no-push

   For ``save`` only: commit locally but do not push. Prints a warning that
   assets are not durable until pushed. Not recommended for normal use.

.. option:: -m MESSAGE, --message MESSAGE

   Commit message for ``save``.

.. option:: --remote URL

   Git remote URL for the ``restore`` wizard (new machine bootstrap).

.. option:: --categories LIST

   Comma-separated categories for non-interactive ``restore``.

.. option:: --conflict {prompt,overwrite,keep,abort}

   Conflict policy for non-interactive ``restore``. Interactive restore shows
   a unified diff and offers overwrite or cancel entire restore.

.. option:: --skip-pull

   Skip ``git pull`` before ``restore`` (unsafe; discouraged).

.. option:: --encrypt

   Encrypt the path when using ``track``.

.. option:: --purge-repo

   With ``untrack``: also delete the mirrored copy from the repository.

Primary actions
===============

.. option:: track

   Start watching a path. Appends an entry to ``filelist`` and, on first use,
   creates ``~/.dotfiles`` (or ``$DOTSYNC_REPO``) and runs ``git init``.

   Syntax::

      dotsync track <path> [category] [--encrypt]

   Example::

      dotsync track ~/.zshrc shell
      dotsync track ~/.config/nvim editor
      dotsync track --encrypt ~/.ssh/config tools

   Tracking a **directory** adds a single ``@tree:path:category`` line (not one
   entry per file). Use ``@tree`` in ``filelist`` directly for globs or manual
   setup; ``track`` on a directory is equivalent to appending ``@tree:…``.

.. option:: untrack

   Stop watching a path and remove it from ``filelist``. Optionally pass
   ``--purge-repo`` to delete the mirror copy in the repo.

   Syntax::

      dotsync untrack <path> [--purge-repo]

.. option:: list

   List watched paths for active categories, including encrypt flag and
   whether each entry is a file or ``@tree``.

.. option:: categories

   Show host groups (``host=cat,cat`` lines) and unique categories defined in
   ``filelist``, with a hint for the current machine hostname.

.. option:: save

   Full persist workflow for the source machine:

   1. Expand ``@tree`` entries (walk home, build manifest)
   2. Mirror home → repo (materialize symlinks inside trees)
   3. ``git add`` and ``git commit``
   4. ``git push`` to ``origin`` (default)

   Syntax::

      dotsync save [categories] [-m msg] [--dry-run] [--no-push]

   If ``origin`` is missing, dotsync prompts for a Git URL before push. Push
   failure exits non-zero.

   Replaces v1 ``update``, ``commit``, ``scan``, and ``clean_repo``.

.. option:: restore

   Full restore workflow:

   1. Bootstrap: if no local repo, wizard prompts for remote URL and clones
   2. ``git fetch`` + ``git pull --ff-only`` (abort on failure unless
      ``--skip-pull``)
   3. Copy repo → home for active categories

   When a home file exists and differs, dotsync shows a unified diff (or a
   binary summary) and prompts: overwrite or **cancel entire restore**.

   Identical files are skipped without prompting.

   Syntax::

      dotsync restore [categories] [--dry-run]
      dotsync restore --remote URL --categories a,b --yes

.. option:: passwd

   Set or change the encryption password used by the encrypt plugin.

.. option:: showpw

   Print the stored encryption password to stdout. **Local machine only** —
   visible in the terminal and shell history. Use with care.

``@tree`` entries
=================

Tree lines in ``filelist`` use the ``@tree:`` prefix::

   @tree:.config/nvim:editor
   @tree:.local/share/my-app/custom-*:tools

On every ``save``, dotsync walks matching paths under ``$HOME``, mirrors each
file into the repo, and can prune stale mirror files (with confirmation unless
``--yes``). Symlinks inside trees are materialized (target content stored in
git). See :doc:`filelist` for syntax details.

Legacy actions (deprecated)
=============================

These v1 commands remain as aliases but are not the recommended workflow:

.. option:: init

   Use ``track`` (local) or ``restore`` (new machine) instead.

.. option:: add / unmanage

   Aliases for ``track`` / ``untrack``.

.. option:: update / commit / diff / clean

   Use ``save``, ``git -C $DOTSYNC_REPO diff``, or ``untrack --purge-repo``.

See :doc:`v2_migration` when upgrading from v1 link mode.
