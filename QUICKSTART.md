# Quick Start Guide

Get up and running with dotsync in minutes!

## Installation

```bash
# Quick install (recommended)
curl -fsSL https://raw.githubusercontent.com/HarveyGG/dotsync/main/install.sh | bash

# Or using Homebrew (macOS)
brew install dotsync

# Or using pip
pip install dotsync
```

## Your First Dotfiles Repository

### 1. Initialize

```bash
mkdir ~/.dotfiles && cd ~/.dotfiles
dotsync init
```

This creates:
- A git repository
- A `filelist` for managing your files
- Directory structure for organizing dotfiles

### 2. Add Your First File

```bash
# Add your zsh config
dotsync add ~/.zshrc

# It automatically infers the category (zsh) from the filename!
```

### 3. Sync to Repository

```bash
dotsync update
```

This will:
- Copy `.zshrc` to the repository
- Create a symlink from `~/.zshrc` to the repository version

### 4. Commit and Push

```bash
# Add remote (if using GitHub)
git remote add origin https://github.com/yourusername/dotfiles.git

# Commit your changes
dotsync commit

# Or manually
git add .
git commit -m "Add zsh configuration"
git push origin main
```

## Restore on New Machine

```bash
# Clone your dotfiles repo
git clone https://github.com/yourusername/dotfiles.git ~/.dotfiles
cd ~/.dotfiles

# Install dotsync (if not installed)
curl -fsSL https://raw.githubusercontent.com/HarveyGG/dotsync/main/install.sh | bash

# Restore all files
dotsync restore
```

Done! All your dotfiles are now symlinked and ready to use.

## Common Workflows

### Adding Multiple Files

```bash
dotsync add ~/.vimrc vim
dotsync add ~/.gitconfig git
dotsync add ~/.tmux.conf tmux
dotsync update
dotsync commit
```

### Encrypting Sensitive Files

```bash
# Add with encryption
dotsync add --encrypt ~/.ssh/id_rsa ssh

# Or convert existing file to encrypted
dotsync add ~/.aws/credentials aws
dotsync update
dotsync encrypt ~/.aws/credentials
dotsync update  # Re-encrypts with new encryption
```

### Organizing by Machine

Your `filelist` might look like:

```
.zshrc:zsh,workstation
.vimrc:vim,common
.ssh/config:ssh|encrypt,common
.bashrc:bash,server
```

- Files in `common` category: shared by all machines
- Files in `workstation` category: only on your workstation
- Files in `server` category: only on servers

Then restore specific categories:
```bash
dotsync restore common workstation  # Only restore common and workstation files
```

### Updating Files

```bash
# Edit your file normally
vim ~/.zshrc

# Sync changes back to repository
dotsync update

# Commit
dotsync commit
```

## Tips

1. **Always commit after updating**: `dotsync update && dotsync commit`
2. **Use categories wisely**: Organize by purpose (zsh, vim, git) or machine type
3. **Encrypt sensitive data**: Use `--encrypt` for API keys, tokens, SSH keys
4. **Check status**: Use `dotsync list` to see all managed files
5. **See differences**: Use `dotsync diff` before committing

## Next Steps

- Read the [full documentation](https://dotsync.readthedocs.io)
- Explore [advanced features](README.md#features)
- Check out [examples](https://dotsync.readthedocs.io/cookbook.html)

