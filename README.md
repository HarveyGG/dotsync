# dotsync

<div align="center">

![dotsync](https://img.shields.io/badge/dotsync-2.0.2-blue)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS-lightgrey)
![License](https://img.shields.io/badge/license-Non--Commercial-blue.svg)

**Mirror-only dotfiles manager — edit configs in `$HOME`, persist them to git, restore on new machines.**

[Features](#-features) • [Installation](#-installation) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [Contributing](#-contributing)

</div>

---

## ✨ Features

- **🏠 Home is source of truth** — edit dotfiles where tools expect them; the repo is a mirror
- **🎯 Easy organization** — categorize files with an intuitive filelist system
- **🔄 Multi-machine support** — share files between machines or keep separate versions in the same repo
- **🌲 Dynamic trees** — `@tree` entries re-scan on every `save`; no manual `scan` step
- **🔒 Encryption support** — encrypt sensitive dotfiles using GnuPG
- **📦 Minimal dependencies** — only requires `uv` (auto-installed) and git
- **🚀 Simple lifecycle** — `track` → `save` → `restore` on a new machine
- **🧪 Well tested** — comprehensive test suite ensuring reliability
- **📚 Great documentation** — full documentation at [ReadTheDocs](https://dotsync.readthedocs.io)

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
pip install dotsync-cli
```

## 📖 Quick Start

### Source machine (already has dotfiles)

```bash
# Start watching paths (creates ~/.dotfiles + git init on first use)
dotsync track ~/.zshrc shell
dotsync track ~/.config/nvim editor

# Mirror home → repo, commit, and push (prompts for remote if missing)
dotsync save
```

Your files stay as **regular files in `$HOME`**. dotsync copies content into the repo and pushes to GitHub by default.

### New machine

```bash
# Interactive wizard: Git URL → clone → pull latest → pick categories → copy
dotsync restore
```

Non-interactive:

```bash
dotsync restore --remote git@github.com:you/dotfiles.git --categories shell,editor --yes
```

### Upgrading from v1 (home symlinks into repo)

v2 assumes real files at home paths. If you used v1 link mode, run the one-off migration script **before** using v2:

```bash
python3 scripts/unsymlink_dotfiles_home.py --dry-run
python3 scripts/unsymlink_dotfiles_home.py --apply
```

See [docs/v2 migration guide](https://dotsync.readthedocs.io/en/latest/v2_migration.html) for details.

## 📋 Commands

| Command | Description |
|---------|-------------|
| `dotsync track <path> [category] [--encrypt]` | Add a path to the watch list; bootstraps repo on first use |
| `dotsync untrack <path> [--purge-repo]` | Stop watching; optionally delete mirror copy in repo |
| `dotsync list [categories]` | List watched paths, categories, encrypt flag, tree vs file |
| `dotsync list --top-level` | Same as `list`, but group by first-level path root (e.g. one row for `.cursor`) |
| `dotsync categories` | Show host groups and category definitions from filelist |
| `dotsync save [categories] [-m msg] [--dry-run] [--no-push]` | Walk `@tree` entries → mirror home → repo → commit → **push** |
| `dotsync restore [categories] [--dry-run]` | Pull latest repo, then copy repo → home (diff on conflict) |
| `dotsync passwd` | Set or change encryption password |
| `dotsync showpw` | Print stored encryption password (local machine only) |

### `@tree` entries (dynamic directories)

Add tree lines to `filelist`; membership is re-expanded on every `save`:

```
@tree:.config/nvim:editor
@tree:.local/share/my-app/custom-*:tools
```

Symlinks inside watched trees are **materialized** (target content copied into the repo), not stored as pointer-only.

For detailed usage, see the [documentation](https://dotsync.readthedocs.io).

## 📁 Repository Structure

```
~/.dotfiles/
├── .git/
├── filelist              # Watch list (atomic paths + @tree lines)
├── dotfiles/
│   ├── plain/            # Unencrypted mirrors
│   └── encrypt/          # Encrypted mirrors
├── .dotsync/             # Tree manifests and materialized symlink targets
└── .plugins/             # Plugin data (passwords, etc.)
```

## 🔐 Encryption Example

```bash
dotsync track --encrypt ~/.ssh/config tools
dotsync save
dotsync showpw    # local only — prints password from plugin store
dotsync passwd    # change encryption password
```

## 🎯 Use Cases

### Share configurations across machines

```
# filelist
macbook=shell,editor,common
.zshrc:shell,common
.vimrc:editor,common
.ssh/config:tools|encrypt
```

### Watch a whole config directory

```
@tree:.config/nvim:editor
```

New files under `.config/nvim` are picked up automatically on the next `save`.

### Quick machine setup

```bash
dotsync restore
```

No separate `init` or manual `git clone` required — the restore wizard handles bootstrap on a new machine.

## 📚 Documentation

For complete documentation, including:
- Detailed command reference
- Filelist and `@tree` syntax
- Encryption guide
- v2 migration from v1 link mode

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

### Black-box E2E tests

End-to-end scenarios invoke the real `dotsync` CLI in an isolated sandbox (`$HOME` and `DOTSYNC_REPO` confined to temporary directories). **37 black-box tests** cover **36 scenario IDs** below; together with unit/integration tests the full suite is **287 tests** (verified on release **v2.0.2**).

```bash
uv run pytest tests/blackbox/ -v      # E2E only
uv run pytest tests/ -v               # full suite
```

#### Supported scenarios (all passing)

| ID | Area | What it verifies | Status |
|----|------|------------------|--------|
| **L1** | Lifecycle | Full flow: `track` → `save` (push) → `restore` on a fresh machine | ✅ |
| **L2** | Lifecycle | `untrack` removes path from filelist; home file kept; mirror kept | ✅ |
| **L3** | Lifecycle | `untrack --purge-repo` deletes mirror; home file kept | ✅ |
| **L4** | Lifecycle | `track` bootstraps `~/.dotfiles` when no repo exists | ✅ |
| **L5a** | Lifecycle | Default `track` mirrors to repo immediately (auto-update) | ✅ |
| **L5b** | Lifecycle | `track --no-auto-update` defers mirror until `save` | ✅ |
| **M1** | Mirror | After save + restore, home paths stay **regular files**, not symlinks into repo | ✅ |
| **M2** | Mirror | Atomic file round-trip preserves byte-identical content | ✅ |
| **M3** | Mirror | Nested atomic paths restore as regular files, not symlinks | ✅ |
| **RP1** | Restore / pull | `restore` pulls remote HEAD **before** copying to home | ✅ |
| **RP2** | Restore / pull | Diverged local vs remote aborts restore with no home writes | ✅ |
| **RP3** | Restore / pull | `--skip-pull` uses stale local HEAD (unsafe path documented) | ✅ |
| **RP4** | Restore / pull | No `origin` remote: restore uses local HEAD | ✅ |
| **C1** | Conflicts | Unified diff shown; cancel aborts **entire** restore | ✅ |
| **C2** | Conflicts | Overwrite on first conflict continues restore for remaining paths | ✅ |
| **C3** | Conflicts | Identical home file skipped without prompting | ✅ |
| **C4** | Conflicts | `--conflict overwrite --non-interactive` applies all overwrites | ✅ |
| **C5** | Conflicts | `--conflict abort --non-interactive` exits without home writes | ✅ |
| **T1** | `@tree` | New file under watched tree picked up on second `save` | ✅ |
| **T2** | `@tree` | Glob `@tree` pattern excludes non-matching paths (e.g. `node_modules`) | ✅ |
| **T3** | `@tree` | Removing tree member prunes stale mirror from repo | ✅ |
| **T4** | `@tree` | `@tree` save → push → restore round-trip on clean home | ✅ |
| **S1** | Symlinks | Internal symlink inside tree materialized with manifest sidecar | ✅ |
| **S2** | Symlinks | External symlink content stored under `.dotsync/materialized/` | ✅ |
| **S3** | Symlinks | Broken symlink warns and skips; no corrupt mirror artifact | ✅ |
| **S4** | Symlinks | Dedup when symlink target is also watched in the same tree | ✅ |
| **S5** | Symlinks | Restore recreates internal user symlink when target exists | ✅ |
| **S6** | Symlinks | External symlink save → restore round-trip on fresh home | ✅ |
| **E1** | Encrypt | `track --encrypt` → `save` → `restore` round-trip (GPG + password) | ✅ |
| **E2** | Encrypt | `showpw` prints stored encryption password (local only) | ✅ |
| **E3** | Encrypt | `showpw` exits non-zero when no password configured | ✅ |
| **B1** | Boundaries | Empty filelist: `save` succeeds with no file operations | ✅ |
| **B2** | Boundaries | Declining remote URL prompt aborts `save` | ✅ |
| **B3** | Boundaries | Push to invalid remote exits non-zero | ✅ |
| **B4** | Boundaries | Binary conflict shows summary; cancel leaves home unchanged | ✅ |
| **B5** | Boundaries | `--no-push` prints durability warning | ✅ |
| **B6** | Boundaries | `save --non-interactive` without remote exits quickly (no hang) | ✅ |

**Capability map:** mirror-only home files (M), git push/pull safety (RP), conflict handling (C), dynamic `@tree` directories (T), symlink materialization (S), encryption (E), CLI edge cases (B), and end-to-end multi-machine setup (L).

Detailed step-by-step commands and assertions: [tests/blackbox/test_plan.md](tests/blackbox/test_plan.md).

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
- [PyPI Package](https://pypi.org/project/dotsync-cli/)

---

<div align="center">

Made with ❤️ by the dotsync community

[⭐ Star this repo](https://github.com/HarveyGG/dotsync) if you find it useful!

</div>
