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
pip install dotsync-cli
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

**Note:** Python and uv are not required - they will be automatically managed by the installer.

## Troubleshooting

### Command Not Found

If `dotsync` command is not found after installation:

**For install.sh users:**
```bash
# Add to your PATH
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

# Add to your shell config (~/.zshrc, ~/.bashrc, etc.)
echo 'export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**For Homebrew users:**
```bash
# Homebrew should handle PATH automatically
# If not, try:
brew doctor
```

**For pip users:**
```bash
# Find installation location
python3 -m pip show dotsync-cli | grep Location

# Add to PATH (usually one of these)
export PATH="$HOME/.local/bin:$PATH"
export PATH="$(python3 -m site --user-base)/bin:$PATH"
```

### uv Not Found (for install.sh users)

If you see "uv not found" error:

```bash
# Install uv manually
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or use Homebrew
brew install uv
```

### Permission Errors

If you encounter permission errors:

- **install.sh**: No sudo required, installs to `~/.local/bin`
- **Homebrew**: May need `sudo` for first-time Homebrew setup
- **pip**: Use `--user` flag: `pip install --user dotsync-cli`

