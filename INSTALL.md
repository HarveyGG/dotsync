# Installation Guide

## Quick Install (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/HarveyGG/dotsync/main/install.sh | bash
```

**What it does:**
- Installs `uv` (if not present)
- Creates dotsync launcher
- On first run, automatically downloads Python + dotsync
- No Python installation required

## Homebrew (macOS/Linux)

```bash
brew tap HarveyGG/tap
brew install dotsync
```

## pip (Alternative)

```bash
pip install dotsync
```

## Verification

After installation, verify it works:

```bash
dotsync --version
dotsync --help
```

## Requirements

- Git
- GnuPG (optional, for encryption support)

Note: Python is not required - it will be automatically managed by dotsync.

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

