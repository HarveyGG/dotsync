============
Installation
============

System package manager
======================

* Arch Linux: `AUR package <https://aur.archlinux.org/packages/dotsync>`_

Install using pip
=================

The easiest method to install dotsync is using pip (you might need to change the
command to ``pip3`` depending on your system)::

   pip install -U dotsync

If you are installing dotsync using pip make sure to check out the `Shell
completion`_ section to get tab-completion working.

Shell completion
================

If you did not install dotsync using the system package manager you can get
shell completion (tab-completion) working by installing the relevant dotsync
completion scripts for your shell.

Bash::

   url="https://raw.githubusercontent.com/HarveyGG/dotsync/master/pkg/completion/bash.sh"
   curl "$url" >> ~/.bash_completion

Fish shell::

   url="https://raw.githubusercontent.com/HarveyGG/dotsync/master/pkg/completion/fish.fish"
   curl --create-dirs "$url" >> ~/.config/fish/completions/dotsync.fish

Any help for non-bash completion scripts would be much appreciated :)

Manual installation
===================

If you do not want to install dotsync with a package manager you can also just
add this repo as a git submodule to your dotfiles repo. That way you get dotsync
whenever you clone your dotfiles repo with no install necessary.  Note that if
you choose this route you will need to manually update dotsync to the newest
version if there is a new release by pulling in the newest changes into your
repo. To set this up, cd into your dotfiles repo and run the following::

   cd ~/.dotfiles
   git submodule add https://github.com/HarveyGG/dotsync
   git commit -m "Added dotsync submodule"


Now, whenever you clone your dotfiles repo you will have to pass an additional
flag to git to tell it to also clone the dotsync repo::

   git clone --recurse-submodules https://github.com/dotfiles/repo ~/.dotfiles

If you want to update the dotsync repo to the latest version run the following
inside your dotfiles repo::

   git submodule update --remote dotsync
   git commit -m "Updated dotsync"

Finally, to run dotsync it is easiest to set up something like an alias. You can
then also set up the bash completion in the same way as mentioned in `Shell
completion`_. This is an example entry of what you might want to put in your
``.bashrc`` file to make an alias (you'll probably want to update the path and
``python3`` command to match your setup)::

   alias dotsync="python3 ~/.dotfiles/dotsync/dotsync/__main__.py"
