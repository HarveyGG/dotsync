# Quick Start Guide

Get up and running with dotsync v2 in minutes.

## Installation

```bash
# Quick install (recommended)
curl -fsSL https://raw.githubusercontent.com/HarveyGG/dotsync/main/install.sh | bash

# Or using Homebrew (macOS/Linux)
brew tap HarveyGG/tap
brew install dotsync

# Or using pip
pip install dotsync-cli
```

## Your First Dotfiles Repository

v2 uses a **mirror-only** model: you edit files in `$HOME`, and `save` copies them into a git repo and pushes by default. dotsync never replaces home files with symlinks into the repo.

### 1. Track your first file

```bash
# Creates ~/.dotfiles and runs git init on first track
dotsync track ~/.zshrc shell
```

Category is optional — dotsync can infer it from the path.

### 2. Save (mirror + commit + push)

```bash
dotsync save
```

This will:
- Copy `.zshrc` from home into the repo mirror
- Create a git commit
- Push to `origin` (prompts for a remote URL if none is configured)

Use `--no-push` only when offline; it prints a warning that changes are not durable until pushed.

### 3. Track more paths or trees

```bash
dotsync track ~/.gitconfig tools
dotsync track ~/.config/nvim editor

# Or add a tree line to filelist for dynamic directories:
# @tree:.config/nvim:editor
```

Then save again:

```bash
dotsync save -m "Add git and nvim configs"
```

## Restore on a New Machine

```bash
# Install dotsync, then run the restore wizard
dotsync restore
```

The wizard will:
1. Prompt for your Git remote URL (if no local repo exists)
2. Clone to `~/.dotfiles` (or `$DOTSYNC_REPO`)
3. Run `git fetch` + `git pull --ff-only`
4. Show available categories — pick what to restore
5. Copy repo files to home paths (shows a diff before overwriting conflicts)

Non-interactive example:

```bash
dotsync restore \
  --remote https://github.com/yourusername/dotfiles.git \
  --categories shell,editor \
  --yes \
  --conflict overwrite
```

Files land as **regular files in `$HOME`**, not symlinks.

## Common Workflows

### Daily edit cycle

```bash
vim ~/.zshrc
dotsync save
```

### List and inspect

```bash
dotsync list
dotsync categories
dotsync save --dry-run -v    # preview planned mirror ops
git -C ~/.dotfiles diff      # inspect repo changes
```

### Encrypt sensitive files

```bash
dotsync track --encrypt ~/.ssh/config tools
dotsync save
dotsync showpw    # local machine only
dotsync passwd    # rotate password
```

### Stop watching a path

```bash
dotsync untrack ~/.old-config
dotsync untrack ~/.old-config --purge-repo   # also delete mirror in repo
dotsync save
```

### Organize by machine

Your `filelist` might look like:

```
macbook=shell,editor,common
.zshrc:shell,common
.vimrc:editor,common
.ssh/config:tools|encrypt
@tree:.config/nvim:editor
```

Restore only selected categories:

```bash
dotsync restore common shell
```

## Upgrading from v1

If v1 left symlinks in `$HOME` pointing into `~/.dotfiles`, convert them to real files **before** using v2:

```bash
python3 scripts/unsymlink_dotfiles_home.py --dry-run
python3 scripts/unsymlink_dotfiles_home.py --apply
```

See the [v2 migration guide](https://dotsync.readthedocs.io/en/latest/v2_migration.html).

## Tips

1. **`save` pushes by default** — durability means remote, not just local commit
2. **Use categories** — organize by purpose (shell, editor) or machine (laptop, server)
3. **Use `@tree` for directories** — new files appear on the next `save` without rescanning
4. **Restore pulls first** — always syncs repo from remote before copying to home
5. **Conflicts show a diff** — overwrite one file or cancel the entire restore

## Next Steps

- Read the [full documentation](https://dotsync.readthedocs.io)
- Explore the [filelist reference](https://dotsync.readthedocs.io/en/latest/filelist.html)
- Check the [cookbook](https://dotsync.readthedocs.io/en/latest/cookbook.html)
