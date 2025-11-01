# dotsync

<div align="center">

![dotsync](https://img.shields.io/badge/dotsync-2.2.9-blue)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS-lightgrey)
![License](https://img.shields.io/badge/license-Non--Commercial-blue.svg)

**A powerful and versatile dotfiles manager that makes managing your configuration files across multiple machines effortless.**

[Features](#-features) • [Installation](#-installation) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [Contributing](#-contributing)

</div>

---

## ✨ Features

- **🎯 Easy Organization** - Categorize and organize your dotfiles with an intuitive filelist system
- **🔄 Multi-Machine Support** - Share files between machines or keep separate versions in the same repo
- **🔒 Encryption Support** - Encrypt sensitive dotfiles using GnuPG
- **🔗 Flexible Linking** - Use symlinks or copy files (hard mode) based on your needs
- **📦 Zero Dependencies**
- **🚀 Simple Commands** - Intuitive CLI with commands like `add`, `update`, `restore`, `encrypt`
- **🧪 Well Tested** - Comprehensive test suite ensuring reliability
- **📚 Great Documentation** - Full documentation available at [ReadTheDocs](https://dotsync.readthedocs.io)

## 🚀 Installation

### Quick Install (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/HarveyGG/dotsync/main/install.sh | bash
```

**Features:**
- ✅ No Python installation required
- ✅ Zero dependencies
- ✅ Cross-platform (macOS, Linux)
- ⚡ First run ~30s, then instant

### Homebrew (macOS/Linux)

```bash
brew tap HarveyGG/tap
brew install dotsync
```

### pip (Alternative)

```bash
pip install dotsync
```


## 📖 Quick Start

### 1. Initialize a dotfiles repository

```bash
# Automatically creates ~/.dotfiles if it doesn't exist
dotsync init

# Or specify a custom directory
dotsync init ~/my-dotfiles
```

### 2. Add a configuration file

```bash
# Add a file (automatically infers category from path)
dotsync add ~/.zshrc

# Add with specific category
dotsync add ~/.vimrc vim

# Add with encryption
dotsync add --encrypt ~/.ssh/id_rsa ssh
```

### 3. Sync files to repository

```bash
dotsync update
```

This will:
- Copy your files to the repository
- Create symlinks in your home directory pointing to the repository

### 4. Restore on a new machine

```bash
git clone https://github.com/yourusername/dotfiles.git ~/.dotfiles
cd ~/.dotfiles
dotsync restore
```

## 📋 Common Commands

| Command | Description |
|---------|-------------|
| `dotsync init [directory]` | Initialize a new dotfiles repository (default: ~/.dotfiles) |
| `dotsync add <file> [category]` | Add a new file to management |
| `dotsync add --encrypt <file> [category]` | Add a file with encryption |
| `dotsync update` | Sync files from home to repository |
| `dotsync restore` | Restore files from repository to home |
| `dotsync encrypt <file>` | Convert existing file to encrypted |
| `dotsync unmanage <file>` | Stop managing a file |
| `dotsync list` | List all managed files |
| `dotsync diff` | Show differences between home and repo |
| `dotsync commit` | Commit changes to git |
| `dotsync clean` | Remove files from home that are in repo |
| `dotsync passwd` | Change encryption password |

For detailed usage, see the [documentation](https://dotsync.readthedocs.io).

## 📁 Repository Structure

After initialization, your repository will look like:

```
~/.dotfiles/
├── .git/
├── filelist          # List of managed files
├── dotfiles/
│   ├── plain/       # Unencrypted files
│   │   ├── common/
│   │   ├── zsh/
│   │   └── vim/
│   └── encrypt/     # Encrypted files
│       └── ssh/
└── .plugins/        # Plugin data (passwords, etc.)
```

## 🔐 Encryption Example

```bash
# Add a file with encryption
dotsync add --encrypt ~/.cursor/mcp.json cursor

# The file will be encrypted in the repository
# When you sync, it's automatically decrypted to your home directory

# Convert an existing plain file to encrypted
dotsync encrypt ~/.ssh/config

# Change encryption password
dotsync passwd
```

## 🎯 Use Cases

### Share Configurations Across Machines

Keep your workstation and server dotfiles in the same repository, organized by categories:

```
filelist:
.zshrc:zsh,workstation
.vimrc:vim,common
.ssh/config:ssh|encrypt
```

### Quick Machine Setup

```bash
# On a new machine
git clone https://github.com/yourusername/dotfiles.git ~/.dotfiles
cd ~/.dotfiles
dotsync restore

# Or if the repository doesn't exist yet
dotsync init  # Creates ~/.dotfiles automatically
```

### Encrypt Sensitive Files

Keep API keys, tokens, and other sensitive data encrypted in your repository while still managing them with dotsync.

## 📚 Documentation

For complete documentation, including:
- Detailed command reference
- Advanced usage patterns
- Encryption guide
- Migration from v1.x

Visit: **[https://dotsync.readthedocs.io](https://dotsync.readthedocs.io)**

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
git clone https://github.com/HarveyGG/dotsync.git
cd dotsync
uv sync
```

### Running Tests

```bash
uv run pytest tests/
```

## 📝 License

This project is licensed under a Non-Commercial License. See the [LICENSE](LICENSE) file for details.

**Summary:**
- ✅ Free for personal, educational, and non-profit use
- ✅ View, modify, and distribute the source code
- ❌ Commercial use is not permitted without explicit permission

For commercial licensing inquiries, please contact: harvey.wanghy@gmail.com

## 🔗 Links

- [Documentation](https://dotsync.readthedocs.io)
- [Issue Tracker](https://github.com/HarveyGG/dotsync/issues)
- [PyPI Package](https://pypi.org/project/dotsync/)

---

<div align="center">

Made with ❤️ by the dotsync community

[⭐ Star this repo](https://github.com/HarveyGG/dotsync) if you find it useful!

</div>
