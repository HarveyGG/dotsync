# dotsync

<div align="center">

![dotsync](https://img.shields.io/badge/dotsync-2.0.2-blue)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS-lightgrey)
![License](https://img.shields.io/badge/license-Non--Commercial-blue.svg)

**Mirror-only dotfiles manager — edit configs in `$HOME`, mirror them to git, restore on new machines.**

[Install](#installation) • [Quick start](#quick-start) • [Commands](#commands) • [Filelist](#filelist) • [Test coverage](#test-coverage) • [Docs](https://dotsync.readthedocs.io)

</div>

---

dotsync watches paths under your home directory, copies their content into a git repo (default `~/.dotfiles`), and pushes to a remote. Config files **stay as regular files in `$HOME`** — the repo is a mirror, not a symlink farm. Use categories to sync subsets of your dotfiles per machine; use `@tree` lines to watch whole directories that grow over time.

## Installation

**Quick install** (installs `uv` if needed; first run ~30s, then instant):

```bash
curl -fsSL https://raw.githubusercontent.com/HarveyGG/dotsync/main/install.sh | bash
```

**Homebrew:**

```bash
brew tap HarveyGG/tap
brew install dotsync
```

**pip:**

```bash
pip install dotsync-cli
```

Requires **git**. Runtime uses **uv** to resolve the CLI (handled by the install methods above).

## Quick start

**Machine that already has your configs:**

```bash
dotsync track ~/.zshrc shell
dotsync track ~/.config/nvim editor
dotsync save    # mirror → commit → push (prompts for remote on first push)
```

**New machine:**

```bash
dotsync restore
# or non-interactive:
dotsync restore --remote git@github.com:you/dotfiles.git --categories shell,editor --yes
```

`track` bootstraps `~/.dotfiles` and `git init` on first use. `restore` clones (or uses an existing repo), pulls latest, then copies mirrors back to `$HOME`.

## Filelist

Watch rules live in `~/.dotfiles/filelist`:

```
# path:category[,category...]  optional |encrypt
.zshrc:shell,common
.ssh/config:tools|encrypt

# whole directory — re-scanned on every save
@tree:.config/nvim:editor
@tree:.local/share/my-app/custom-*:tools

# host → category groups (optional)
macbook=shell,editor,common
```

- **Atomic paths** — single files (or expanded directory contents when added via `track` on a directory).
- **`@tree`** — dynamic membership; new files under the pattern are picked up on the next `save`. Globs supported (`*`, `?`, `[…]`).
- **Symlinks inside trees** — targets are materialized into the repo (internal links keep layout; external targets go under `.dotsync/materialized/`).

## Commands

| Command | Description |
|---------|-------------|
| `init [dir]` | Create repo skeleton at `~/.dotfiles` (or given path) |
| `track <path> [category] [--encrypt] [--no-auto-update]` | Add to filelist; mirrors immediately unless `--no-auto-update` |
| `untrack <path> [--purge-repo]` | Stop watching; home file kept |
| `encrypt <path>` | Convert an already-tracked plain path to encrypted |
| `list [categories] [--top-level]` | List watched paths; each row shows `(file\|tree, plain\|encrypt)` plus categories; `@tree` entries are summarized by directory, not expanded |
| `categories` | Show category groups from filelist |
| `save [categories] [-m msg] [--dry-run] [--no-push]` | Expand `@tree`, mirror home → repo, commit, push |
| `restore [categories] [--remote URL] [--yes] [--skip-pull] [--conflict …]` | Pull (unless skipped), then repo → home; diff on conflict |
| `update [categories]` | Mirror home → repo without commit |
| `diff [categories]` | Show git diff plus pending mirror changes |
| `commit [-m msg]` | Commit staged repo changes |
| `clean [categories]` | Remove repo mirrors no longer in filelist |
| `passwd` | Set or change encryption password |
| `showpw` | Print stored encryption password (local machine only) |

Common flags: `--non-interactive`, `--dry-run`, `--encrypt`, `--keep-going`.

Full reference: [ReadTheDocs](https://dotsync.readthedocs.io).

## Test coverage

**291 tests** total (**37** black-box E2E scenarios against the real CLI in an isolated sandbox). All scenarios below pass on **v2.0.4**.

```bash
uv run pytest tests/blackbox/ -v
uv run pytest tests/ -v
```

| ID | Area | What it verifies |
|----|------|------------------|
| L1 | Lifecycle | `track` → `save` (push) → `restore` on a fresh machine |
| L2 | Lifecycle | `untrack` removes from filelist; home file kept |
| L3 | Lifecycle | `untrack --purge-repo` deletes mirror |
| L4 | Lifecycle | `track` bootstraps repo when missing |
| L5a | Lifecycle | Default `track` mirrors immediately |
| L5b | Lifecycle | `track --no-auto-update` defers mirror until `save` |
| M1 | Mirror | Home paths stay regular files after save + restore |
| M2 | Mirror | Atomic file round-trip is byte-identical |
| M3 | Mirror | Nested paths restore as files, not symlinks |
| RP1 | Pull | `restore` pulls remote before copying to home |
| RP2 | Pull | Diverged repo aborts restore with no home writes |
| RP3 | Pull | `--skip-pull` uses local HEAD only |
| RP4 | Pull | No remote: restore from local HEAD |
| C1 | Conflicts | Cancel on diff aborts entire restore |
| C2 | Conflicts | Overwrite continues for remaining paths |
| C3 | Conflicts | Identical home file skipped without prompt |
| C4 | Conflicts | `--conflict overwrite --non-interactive` |
| C5 | Conflicts | `--conflict abort --non-interactive` |
| T1 | `@tree` | New tree member picked up on second `save` |
| T2 | `@tree` | Glob excludes non-matching paths |
| T3 | `@tree` | Removed member pruned from repo mirror |
| T4 | `@tree` | Tree save → restore on clean home |
| S1 | Symlinks | Internal symlink materialized with manifest |
| S2 | Symlinks | External symlink under `.dotsync/materialized/` |
| S3 | Symlinks | Broken symlink skipped cleanly |
| S4 | Symlinks | Dedup when link target also watched |
| S5 | Symlinks | Restore recreates internal symlink |
| S6 | Symlinks | External symlink save → restore round-trip |
| E1 | Encrypt | Encrypt track → save → restore |
| E2 | Encrypt | `showpw` prints stored password |
| E3 | Encrypt | `showpw` fails when no password set |
| B1 | Boundaries | Empty filelist save is a no-op |
| B2 | Boundaries | Declined remote URL aborts save |
| B3 | Boundaries | Push failure exits non-zero |
| B4 | Boundaries | Binary conflict; cancel leaves home unchanged |
| B5 | Boundaries | `--no-push` durability warning |
| B6 | Boundaries | Save without remote exits quickly (no hang) |

Scenario details: [tests/blackbox/test_plan.md](tests/blackbox/test_plan.md).

## Contributing

```bash
git clone https://github.com/HarveyGG/dotsync.git && cd dotsync
uv sync
uv run pytest tests/
```

Pull requests welcome.

## License

Non-Commercial License — free for personal, educational, and non-profit use. See [LICENSE](LICENSE). Commercial use requires permission: harvey.wanghy@gmail.com

## Links

- [Documentation](https://dotsync.readthedocs.io)
- [Issues](https://github.com/HarveyGG/dotsync/issues)
- [PyPI](https://pypi.org/project/dotsync-cli/)
