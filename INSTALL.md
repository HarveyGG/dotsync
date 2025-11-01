# Installation Guide

dotsync can be installed in several ways:

## Quick Install (Recommended)

The easiest way to install dotsync is using our installation script:

```bash
curl -fsSL https://raw.githubusercontent.com/HarveyGG/dotsync/main/install.sh | bash
```

This script will:
- Check for Python 3.6+
- Install pip if needed
- Install dotsync using pip
- Provide instructions for adding to PATH if needed

## Homebrew (macOS)

If you have Homebrew installed:

```bash
brew install dotsync
```

Or if you want to install from the formula directly:

```bash
brew install HarveyGG/dotsync/dotsync
```

## pip

```bash
pip install dotsync
```

Or with pip3:

```bash
pip3 install dotsync
```

### User Installation (No sudo)

To install without requiring sudo:

```bash
pip install --user dotsync
```

Then add `~/.local/bin` to your PATH:

```bash
# For bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# For zsh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

## Manual Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/HarveyGG/dotsync.git
   cd dotsync
   ```

2. Install:
   ```bash
   python3 setup.py install
   ```

   Or in development mode:
   ```bash
   pip install -e .
   ```

## Verification

After installation, verify it works:

```bash
dotsync --version
dotsync --help
```

## Requirements

- Python 3.6 or later
- Git
- GnuPG (optional, for encryption support)

## Troubleshooting

### Command Not Found

If `dotsync` command is not found after installation:

1. Check if dotsync is installed:
   ```bash
   python3 -m pip list | grep dotsync
   ```

2. Find the installation location:
   ```bash
   python3 -m pip show -f dotsync | grep Location
   ```

3. Add the binary directory to your PATH:
   ```bash
   # Usually one of these:
   export PATH="$HOME/.local/bin:$PATH"
   export PATH="/usr/local/bin:$PATH"
   export PATH="$(python3 -m site --user-base)/bin:$PATH"
   ```

### Permission Errors

If you encounter permission errors during installation:

- Use `--user` flag: `pip install --user dotsync`
- Or use `sudo`: `sudo pip install dotsync` (not recommended)

### Python Version Issues

Make sure you're using Python 3.6 or later:

```bash
python3 --version
```

If you need to install a newer Python version:
- **macOS**: `brew install python3`
- **Linux**: Use your distribution's package manager or [pyenv](https://github.com/pyenv/pyenv)

