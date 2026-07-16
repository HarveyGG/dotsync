===============
Getting started
===============

dotsync v2 keeps dotfiles in their **natural home paths** and mirrors them
into a git repository. You edit ``~/.zshrc`` (and similar) as usual; ``save``
persists changes to GitHub; ``restore`` copies them back on a new machine.

Setting up on your source machine
=================================

Choose where the repo lives — default ``~/.dotfiles``, or set
``DOTSYNC_REPO``. You need git and dotsync installed (see :doc:`installation`).

Track paths you want to persist
-------------------------------

No separate ``init`` step. The first ``track`` creates the repo and filelist::

   dotsync track ~/.zshrc shell
   dotsync track ~/.gitconfig tools
   dotsync track ~/.config/nvim editor

Use ``--encrypt`` for sensitive files::

   dotsync track --encrypt ~/.ssh/config tools

Save: mirror, commit, and push
------------------------------

::

   dotsync save

This copies watched paths from home into the repo, commits, and **pushes to
``origin`` by default**. If no remote exists, dotsync prompts for a Git URL.

Your home files remain regular files — not symlinks into the repo::

   ls -l ~/.zshrc
   # -rw-r--r-- ... /home/user/.zshrc

Repository layout after save::

   ~/.dotfiles
   ├── filelist
   └── dotfiles
       └── plain
           ├── common
           │   └── .zshrc
           └── shell
               └── ...

Using ``@tree`` for directories
--------------------------------

For config trees that grow over time, add ``@tree`` lines to ``filelist``::

   @tree:.config/nvim:editor

Every ``save`` re-walks the tree — new files are included automatically. See
:doc:`usage` for glob patterns and symlink materialization.

Restore on a new machine
========================

Run the restore wizard::

   dotsync restore

Flow:

1. Prompt for Git remote URL if no local repo exists
2. Clone to ``~/.dotfiles`` and pull latest (`git pull --ff-only`)
3. Show categories from ``filelist`` — select what to restore
4. Copy repo → home; show diff before overwriting any conflicting file

Non-interactive bootstrap::

   dotsync restore \
     --remote https://github.com/username/dotfiles.git \
     --categories common,shell \
     --yes

Example workflow for multiple hosts
===================================

Two machines, "laptop" and "desktop". Share ``.vimrc``; keep separate
``.xinitrc`` files.

**Laptop** — create filelist entries via track or edit ``filelist`` directly::

   laptop=tools,x
   desktop=tools,x

   .vimrc:laptop,desktop
   .xinitrc:laptop
   .xinitrc:desktop

Then save and push::

   [laptop]$ dotsync save -m "Initial laptop configs"

**Desktop** — restore shared files first, then add desktop-only configs::

   [desktop]$ dotsync restore common laptop desktop -v

   # Edit .xinitrc for desktop, then mirror back
   [desktop]$ dotsync save -m "Add desktop xinitrc"

Future changes: edit at home on either machine, ``dotsync save``, and on the
other machine run ``dotsync restore`` (which pulls before copying).

Upgrading from v1
=================

If you used dotsync v1 link mode, home paths may be symlinks into
``~/.dotfiles``. v2 requires real files at home before ``save``. Run the
standalone migration script (not a dotsync command) — see :doc:`v2_migration`.
