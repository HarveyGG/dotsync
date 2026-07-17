# Black-box E2E Test Plan (Task 16)

**Status:** Reviewed (Opus 4.8, 2026-07-16) — ready for harness implementation (Step 4). Do not execute until `conftest.py` exists.

**Scope:** End-to-end scenarios run in an isolated sandbox. Each scenario invokes the real `dotsync` CLI as a subprocess (not `main()` directly), with `$HOME` and `DOTSYNC_REPO` confined to temporary directories.

**Design reference:** [DESIGN.md](../../.vibe/dotsync-cli/.spec/tree-targets-safe-restore/DESIGN.md) — mirror-only model, pull-before-restore, conflict diff + abort-all, tree walk on save, symlink materialization.

**Success criteria mapped:** SC1–SC7 from DESIGN § Success criteria appear in assertions below.

---

## Sandbox conventions (harness Step 4)

| Variable / artifact | Purpose |
|---------------------|---------|
| `$SANDBOX` | pytest `tmp_path` root for the scenario |
| `$HOME` → `$SANDBOX/home` | Isolated user home; all watched paths live here |
| `DOTSYNC_REPO` → `$SANDBOX/repo` | Dotfiles git working copy (override default `~/.dotfiles`) |
| `$SANDBOX/bare.git` | Local bare remote for push/pull tests (`file://` URL) |
| `$SANDBOX/home2` | Second HOME for “fresh machine” restore (lifecycle) |
| CLI invocation | `uv run dotsync <args>` with `env={HOME, DOTSYNC_REPO}` and `cwd=$HOME` unless noted |
| Git identity | `GIT_AUTHOR_*` / `GIT_COMMITTER_*` set to fixed test values in sandbox env |
| Hostname pin | Monkeypatch or env override for `info.hostname` **or** always pass explicit `--categories`/positional categories — default categories are `['common', hostname]` and are machine-dependent |
| Repo prerequisites | Each non-init scenario must `git init` `$REPO` **and** create `filelist` before any command — `safety_checks` rejects `repo == home`, missing `.git`, or missing `filelist` (`dotsync/checks.py`) |
| Interactive input | Pre-scripted stdin via subprocess or `pexpect`; document expected prompts per scenario |
| Non-interactive save guard | Any `save --non-interactive` **without** `--no-push` requires `origin` pre-configured — otherwise `push_with_remote` calls `input()` and hangs or raises `EOFError` on closed stdin |
| Encrypt isolation | Before enabling E-series: confirm encrypt plugin writes **only** under `$REPO/.plugins/encrypt` (no user keyring/GPG/global state) |
| Isolation invariant | **No writes outside `$SANDBOX`** — verify with post-run path scan in harness |

**Repo layout (v2 mirror):**

- Atomic files: `$REPO/dotfiles/plain/<category>/<relpath>`
- Encrypted files: `$REPO/dotfiles/encrypt/<category>/<relpath>`
- Tree sidecars: `$REPO/.dotsync/manifests/<category>.json`
- External symlink materialization: `$REPO/.dotsync/materialized/<id>/...`

**Non-interactive flags (when prompts would block):**

| Situation | Flags |
|-----------|-------|
| Save without push (offline / faster tests) | `--no-push --non-interactive` |
| Save with prune confirm | `--yes --non-interactive` |
| Restore on clean home | `--non-interactive --conflict overwrite` |
| Restore with pull skipped (only when remote unchanged) | `--skip-pull` |
| Restore wizard / remote URL | `--remote file://... --categories ... --yes` |

**Cleanup (all scenarios):** pytest `tmp_path` teardown removes sandbox. No manual cleanup required unless a scenario notes a harness-side artifact to assert before teardown.

---

## Scenario index

| ID | Category | Priority |
|----|----------|----------|
| L1 | Lifecycle | P0 |
| L2 | Lifecycle | P0 |
| L3 | Lifecycle | P1 |
| L4 | Lifecycle | P1 |
| L5 | Lifecycle | P1 |
| M1 | Mirror-only | P0 |
| M2 | Mirror-only | P0 |
| M3 | Mirror-only | P1 |
| RP1 | Restore pull | P0 |
| RP2 | Restore pull | P0 |
| RP3 | Restore pull | P1 |
| RP4 | Restore pull | P2 |
| C1 | Conflicts | P0 |
| C2 | Conflicts | P0 |
| C3 | Conflicts | P0 |
| C4 | Conflicts | P1 |
| C5 | Conflicts | P1 |
| T1 | Trees | P0 |
| T2 | Trees | P0 |
| T3 | Trees | P1 |
| T4 | Trees | P1 |
| S1 | Symlinks | P0 |
| S2 | Symlinks | P0 |
| S3 | Symlinks | P1 |
| S4 | Symlinks | P1 |
| S5 | Symlinks | P2 |
| S6 | Symlinks | P0 |
| E1 | Encrypt | P1 |
| E2 | Encrypt | P1 |
| E3 | Encrypt | P2 |
| B1 | Boundaries | P1 |
| B2 | Boundaries | P0 |
| B3 | Boundaries | P0 |
| B4 | Boundaries | P1 |
| B5 | Boundaries | P2 |
| B6 | Boundaries | P0 |

---

## Lifecycle

### L1 — Full lifecycle: track → save (push) → restore on fresh HOME

**Maps to:** SC2, SC4, SC6, SC7

**Setup**

1. Create `$HOME`, empty `$REPO` (no repo yet).
2. Create `$SANDBOX/bare.git` (`git init --bare`).
3. Write `$HOME/.zshrc` with content `export ZSH=1\n`.
4. Write `$HOME/.vimrc` with content `set number\n`.

**Harness prerequisites (before first CLI call)**

1. After `track` bootstraps `$REPO`, run `git -C $REPO remote add origin file://$SANDBOX/bare.git` — **or** script stdin for the URL prompt on first `save`.
2. Note: `track` runs auto-update by default, so the mirror may exist **before** `save` (see L5).

**Commands**

```bash
# cwd=$HOME throughout
dotsync track .zshrc shell
dotsync track .vimrc editor
# origin pre-added in harness (see above); save pushes by default
dotsync save -m "initial dotfiles"
# Simulate new machine
rm -rf $SANDBOX/home2 && mkdir -p $SANDBOX/home2
# HOME=$SANDBOX/home2, DOTSYNC_REPO=$SANDBOX/home2/.dotfiles (default)
dotsync restore --remote file://$SANDBOX/bare.git --categories shell,editor --yes
```

**Assertions**

- After `track`: `$REPO/.git` exists; `filelist` contains `.zshrc` and `.vimrc`; mirror paths may already exist (auto-update).
- After `save`: exit 0; `git -C $REPO log -1` shows commit; `git -C $REPO ls-remote origin` has refs (push succeeded).
- Mirror paths exist: `dotfiles/plain/shell/.zshrc`, `dotfiles/plain/editor/.vimrc`.
- After restore on `home2`: both files exist under `home2` with original bytes.
- **SC1:** No path under `home2` is a dotsync home→repo symlink (`find home2 -type l` empty for managed paths; user symlinks recreated by `restore_symlinks` are allowed — see S5).
- `home2/.dotfiles` cloned and at same commit as post-save `$REPO`.

**Interactive note:** If origin is not pre-added, first `save` prompts for remote URL via `input()` — list L1 among interactive scenarios or always pre-add origin in harness.

**Cleanup**

- pytest `tmp_path` teardown.

---

### L2 — Untrack removes from filelist; home file preserved

**Setup**

1. Init repo at `$REPO` with `filelist` containing `.profile:common\n`.
2. Write `$HOME/.profile` with `profile content`.
3. `dotsync save --no-push --non-interactive common`.

**Commands**

```bash
dotsync untrack .profile
dotsync list common
```

**Assertions**

- Exit 0 for untrack.
- `.profile` absent from `$REPO/filelist`.
- `$HOME/.profile` still exists with `profile content` (not deleted from home).
- Repo mirror `$REPO/dotfiles/plain/common/.profile` still present (no `--purge-repo`).

**Cleanup**

- pytest teardown.

---

### L3 — Untrack with `--purge-repo` deletes mirror copy

**Setup**

1. Same as L2 through save.
2. Confirm mirror exists at `dotfiles/plain/common/.profile`.

**Commands**

```bash
dotsync untrack --purge-repo .profile
```

**Assertions**

- Exit 0.
- `.profile` not in `filelist`.
- Mirror path `dotfiles/plain/common/.profile` does not exist.
- `$HOME/.profile` still present locally.

**Cleanup**

- pytest teardown.

---

### L4 — Track bootstraps repo when missing (implicit init)

**Setup**

1. `$HOME` only; no `$REPO`, no `~/.dotfiles` under sandbox home.
2. `$HOME/.gitconfig` with `[user]\n\tname = Test\n`.

**Commands**

```bash
dotsync track .gitconfig tools
```

**Assertions**

- Exit 0.
- `$HOME/.dotfiles/.git` exists (default repo location when `DOTSYNC_REPO` unset).
- `filelist` contains `.gitconfig`.
- `$HOME/.gitconfig` unchanged (still regular file at home).

**Cleanup**

- pytest teardown.

---

### L5 — `track` auto-update side effects

**Setup**

1. `$HOME` only; no `$REPO` yet.
2. Write `$HOME/.zshrc` with `export ZSH=1\n`.

**Commands (default auto-update)**

```bash
dotsync track .zshrc shell
```

**Assertions (auto-update on)**

- Exit 0.
- Mirror `dotfiles/plain/shell/.zshrc` exists **immediately** (before any explicit `save`).
- `$HOME/.zshrc` is a regular file, not a symlink to `$REPO`.
- Document: auto-update swallows sync exceptions and still returns 0 — harness may assert mirror bytes, not exit code alone.

**Variant (`--no-auto-update`)**

```bash
# fresh sandbox
dotsync track --no-auto-update .zshrc shell
```

**Assertions (auto-update off)**

- `filelist` contains `.zshrc`.
- Mirror path `dotfiles/plain/shell/.zshrc` does **not** exist until a subsequent `save`.

**Cleanup**

- pytest teardown.

---

## Mirror-only

### M1 — Home never becomes repo symlink after save + restore

**Maps to:** SC1

**Setup**

1. Init `$REPO`; filelist: `.bashrc:shell\n`.
2. `$HOME/.bashrc` → `shell config v1`.

**Commands**

```bash
dotsync save --no-push --non-interactive shell
dotsync restore shell --non-interactive --skip-pull --conflict overwrite
```

**Assertions**

- After save: `$HOME/.bashrc` is a regular file (`test ! -L $HOME/.bashrc`).
- After restore: still regular file, not symlink to `$REPO`.
- Content byte-identical to repo mirror `dotfiles/plain/shell/.bashrc`.
- Grep `$HOME` for symlinks pointing into `$REPO`: none for managed path.

**Cleanup**

- pytest teardown.

---

### M2 — Byte-identical round-trip (atomic file)

**Maps to:** SC1, SC2

**Setup**

1. filelist: `.config/app/settings.json:editor\n`.
2. Create nested file with multi-line UTF-8 content including non-ASCII (e.g. `café\nline2\n`).

**Commands**

```bash
dotsync save --no-push --non-interactive editor
# Wipe home copy
rm -rf $HOME/.config
dotsync restore editor --non-interactive --skip-pull --conflict overwrite
```

**Assertions**

- `sha256sum` (or equivalent) of home file equals pre-save hash.
- File mode preserved where platform supports (`copy2` semantics).

**Cleanup**

- pytest teardown.

---

### M3 — Nested tree paths restore as regular files (no link mode)

**Setup**

1. filelist with three atomic entries under `.mockdir/...` (hidden + nested), matching integration test layout.
2. Populate tree under `$HOME/.mockdir`.

**Commands**

```bash
dotsync save --no-push --non-interactive mock
rm -rf $HOME/.mockdir
dotsync restore mock --non-interactive --skip-pull --conflict overwrite
```

**Assertions**

- Every restored path under `.mockdir` is a regular file.
- No `$HOME` path is symlink.

**Cleanup**

- pytest teardown.

---

## Restore pull

### RP1 — Pull runs before any home copy

**Maps to:** SC7

**Setup**

1. Publish content to `$SANDBOX/bare.git` from a “source” repo (filelist + mirrored `.file:common`).
2. Local `$REPO` has `origin` → bare; **behind** remote (new commit on bare only).
3. Empty `$HOME` (file missing locally).

**Commands**

```bash
dotsync restore common --non-interactive --conflict overwrite
```

**Assertions**

- stdout contains `Restoring from commit <sha>` where `<sha>` matches remote HEAD (not stale local HEAD).
- `$HOME/.file` created with remote version bytes.
- Harness log or git trace shows fetch/pull before first file write (order: pull → copy).

**Cleanup**

- pytest teardown.

---

### RP2 — Diverged repo aborts restore (no home writes)

**Maps to:** SC7

**Setup**

1. `$REPO` with `origin`, local and remote diverged (non-FF pull impossible).
2. filelist + mirrored file in repo; `$HOME/.file` absent.

**Commands**

```bash
dotsync restore common --non-interactive --conflict overwrite
```

**Assertions**

- Exit code non-zero.
- stderr/log contains exact dotsync message `Failed to pull latest changes` (do **not** assert on git's diverged/non-FF wording — git stderr is not captured by `Git.run`).
- Raw git stderr may appear on the test process stderr; harness should tolerate it.
- `$HOME/.file` still absent (no partial restore).

**Cleanup**

- pytest teardown.

---

### RP3 — `--skip-pull` uses local HEAD without fetch

**Setup**

1. Same as RP1 (local behind remote) but user explicitly opts out of pull.
2. Local mirror has version `local-content`; remote has `remote-content`.

**Commands**

```bash
dotsync restore common --skip-pull --non-interactive --conflict overwrite
```

**Assertions**

- Exit 0.
- `$HOME/.file` content is `local-content` (stale local repo applied).
- No fetch/pull in git trace (document as **unsafe** path per DESIGN).

**Cleanup**

- pytest teardown.

---

### RP4 — No remote: restore uses local HEAD with informational message

**Setup**

1. `$REPO` initialized, no `origin`; filelist + one saved file.
2. Clean `$HOME`.

**Commands**

```bash
dotsync restore common -vv --non-interactive --conflict overwrite
```

**Assertions**

- Exit 0.
- stdout contains `Restoring from commit <local sha>` where `<local sha>` matches `git -C $REPO rev-parse HEAD`.
- At `-vv`, log contains debug line `No remote configured; using local repository`.
- File restored from local repo mirror.
- Do **not** use `--skip-pull` here — with `--skip-pull` the no-remote debug path is bypassed.

**Cleanup**

- pytest teardown.

---

## Conflicts

### C1 — Unified diff shown; cancel aborts entire restore

**Maps to:** SC6

**Setup**

1. filelist: `.file1:common\n.file2:common\n`.
2. Save both to repo via `save --no-push`.
3. `$HOME/.file1` → `home-one\n` (differs); `$HOME/.file2` → `home-two\n` (differs).

**Commands**

```bash
# Interactive: when prompted after diff for file1, answer cancel ('c')
dotsync restore common
```

**Assertions**

- Exit code non-zero.
- stdout contains unified diff markers (`---`, `+++`, `-home-one`, `+repo-one` or equivalent).
- `$HOME/.file1` unchanged (`home-one`).
- `$HOME/.file2` unchanged (`home-two`) — **no later files written** after cancel.

**Cleanup**

- pytest teardown.

---

### C2 — Overwrite continues restore for remaining paths

**Maps to:** SC6

**Setup**

1. Same file pair as C1.

**Commands**

```bash
# Interactive: answer overwrite ('o') on file1 conflict
dotsync restore common
```

**Assertions**

- Exit 0.
- `$HOME/.file1` matches repo version.
- `$HOME/.file2` matches repo version (restore continued).

**Cleanup**

- pytest teardown.

---

### C3 — Identical home file skipped without prompt

**Setup**

1. filelist: `.same:common\n`.
2. Save; keep identical copy at `$HOME/.same`.

**Commands**

```bash
# stdin must not be read — harness fails if input() invoked
dotsync restore common --non-interactive --skip-pull
```

**Assertions**

- Exit 0.
- No diff output for `.same`.
- File unchanged.

**Cleanup**

- pytest teardown.

---

### C4 — Non-interactive `--conflict overwrite` applies all

**Setup**

1. Two conflicting files as in C1.

**Commands**

```bash
dotsync restore common --non-interactive --conflict overwrite --skip-pull
```

**Assertions**

- Exit 0.
- Both home files match repo.

**Cleanup**

- pytest teardown.

---

### C5 — Non-interactive `--conflict abort` exits without writes

**Setup**

1. Single conflicting file `.conflict:common`.

**Commands**

```bash
dotsync restore common --non-interactive --conflict abort --skip-pull
```

**Assertions**

- Exit non-zero.
- Home file unchanged.

**Cleanup**

- pytest teardown.

---

## Trees

### T1 — New file under `@tree` picked up on second save (no scan)

**Maps to:** SC5

**Setup**

1. filelist: `@tree:.config/myapp:editor\n`.
2. `$HOME/.config/myapp/settings.json` → `{"v":1}`.
3. First save.

**Commands**

```bash
dotsync save --no-push --non-interactive editor
echo '{"v":1,"new":true}' > $HOME/.config/myapp/plugins.json
dotsync save --no-push --non-interactive editor
```

**Assertions**

- After second save: mirror includes `dotfiles/plain/editor/.config/myapp/plugins.json`.
- Git commit includes new file.
- No separate `scan` command used.

**Cleanup**

- pytest teardown.

---

### T2 — Glob filter on `@tree` excludes non-matching paths

**Setup**

1. filelist: `@tree:.agents/skills/vibe-module-*:tools\n`.
2. Create:
   - `.agents/skills/vibe-module-foo/SKILL.md`
   - `.agents/skills/vibe-module-bar/SKILL.md`
   - `.agents/skills/other-module/SKILL.md`
   - `.agents/skills/vibe-module-baz/node_modules/pkg/index.js`

**Commands**

```bash
dotsync save --no-push --non-interactive tools
```

**Assertions**

- Mirrors exist for `vibe-module-foo` and `vibe-module-bar` only.
- `other-module` not mirrored.
- No path under mirror contains `node_modules`.

**Cleanup**

- pytest teardown.

---

### T3 — Prune stale repo file after tree member removed (with confirm)

**Setup**

1. filelist: `@tree:.config/myapp:editor\n`.
2. Save with `settings.json` and `old.json`.
3. Delete `$HOME/.config/myapp/old.json`.

**Commands**

```bash
# Interactive: confirm prune with 'y'
dotsync save --no-push editor
# Or non-interactive:
dotsync save --no-push --yes --non-interactive editor
```

**Assertions**

- `old.json` absent from repo mirror after save.
- `settings.json` still present.
- **Interactive variant only:** user saw deletion list before confirm (`confirm_prune` skips the list under `--non-interactive`).

**Cleanup**

- pytest teardown.

---

### T4 — Tree save + restore round-trip on clean home

**Maps to:** SC5, SC1

**Setup**

1. filelist: `@tree:.config/nvim:editor\n`.
2. `$HOME/.config/nvim/init.lua` → `require('plugins')\n`.

**Commands**

```bash
dotsync save --no-push --non-interactive editor
rm -rf $HOME/.config
dotsync restore editor --non-interactive --skip-pull --conflict overwrite
```

**Assertions**

- Restored `init.lua` bytes match original.
- Not a symlink.

**Cleanup**

- pytest teardown.

---

## Symlinks

### S1 — Internal symlink materialized (target inside tree)

**Maps to:** SC3

**Setup**

1. filelist: `@tree:.config/app:editor\n`.
2. `$HOME/.config/app/real.txt` → `hello`.
3. `$HOME/.config/app/link.txt` → symlink to `real.txt`.

**Commands**

```bash
dotsync save --no-push --non-interactive editor
```

**Assertions**

- Repo contains bytes at `dotfiles/plain/editor/.config/app/real.txt` (or canonical path per manifest).
- Sidecar `$REPO/.dotsync/manifests/editor.json` lists `link.txt` with `kind: symlink`, `target: real.txt`.
- Pointer-only symlink not stored as lone symlink file in mirror (content materialized).

**Cleanup**

- pytest teardown.

---

### S2 — External symlink (T6) materialized under `.dotsync/materialized/`

**Maps to:** SC3

**Setup**

1. `$SANDBOX/external/secret.cfg` → `external-data`.
2. filelist: `@tree:.config/app:tools\n`.
3. `$HOME/.config/app/link.cfg` → symlink to `$SANDBOX/external/secret.cfg`.

**Commands**

```bash
dotsync save --no-push --non-interactive tools
```

**Assertions**

- Materialized path under `$REPO/.dotsync/materialized/` contains `external-data`.
- Manifest entry `canonical_repo_path` starts with `.dotsync/materialized/`.
- Sidecar records absolute external target string.

**Cleanup**

- pytest teardown.

---

### S3 — Broken symlink: warn and skip (no mirror artifact)

**Setup**

1. filelist: `@tree:.config/app:editor\n`.
2. `$HOME/.config/app/broken.txt` → symlink to `missing.txt` (target does not exist).

**Commands**

```bash
dotsync save --no-push --non-interactive editor
```

**Assertions**

- Exit 0 (save continues).
- stderr/log contains warning mentioning `broken symlink` and `.config/app/broken.txt`.
- No mirror file created for broken link.
- Manifest empty or omits broken entry.

**Cleanup**

- pytest teardown.

---

### S4 — Dedup when symlink target also watched (A → B, both in tree)

**Setup**

1. filelist: `@tree:.config/app:editor\n`.
2. `real.txt` and `link.txt` → `real.txt` as in unit test.

**Commands**

```bash
dotsync save --no-push --non-interactive editor
```

**Assertions**

- Single canonical content blob in repo for `real.txt`.
- No duplicate mirror at `link.txt` path.
- Manifest has one entry aliasing link → canonical.

**Cleanup**

- pytest teardown.

---

### S5 — Restore recreates internal symlink when target exists in tree

**Setup**

1. Complete S1 save.
2. Wipe `$HOME/.config/app`.

**Commands**

```bash
dotsync restore editor --non-interactive --skip-pull --conflict overwrite
```

**Assertions**

- `$HOME/.config/app/real.txt` regular file with `hello`.
- `link.txt` is a **user** symlink to `real.txt` (expected per `restore_symlinks` when relative target exists in restored tree) — this does **not** violate SC1 (no dotsync home→repo symlinks).
- External/absolute targets are copied as regular files, not recreated as symlinks (`tree.py` 264–268).

**Cleanup**

- pytest teardown.

---

### S6 — External symlink save→restore round-trip

**Maps to:** SC3

**Setup**

1. Same as S2: `$SANDBOX/external/secret.cfg` → `external-data`; filelist `@tree:.config/app:tools`; `$HOME/.config/app/link.cfg` → symlink to external file.
2. Complete S2 save first.

**Commands**

```bash
rm -rf $HOME/.config/app
dotsync restore tools --non-interactive --skip-pull --conflict overwrite
```

**Assertions**

- `$HOME/.config/app/link.cfg` exists with content `external-data` (regular file copy when external target cannot be recreated as symlink).
- **Known implementation risk:** save writes materialized bytes under `plugin_dir/.dotsync/materialized/…` but `restore_symlinks` reads from `dotsync_repo/.dotsync/materialized/…` — this scenario may **fail** and expose a save/restore path mismatch. Treat failure as a visible bug, not a flaky test.

**Cleanup**

- pytest teardown.

---

## Encrypt

### E1 — track --encrypt → save → restore round-trip

**Maps to:** SC3 (encrypted content materialized as ciphertext in repo)

**Prerequisite:** Encrypt plugin isolation verified (writes only under `$REPO/.plugins/encrypt`; see sandbox conventions).

**Setup**

1. Init repo; set password via stdin for `dotsync passwd` (e.g. `testpass123`).
2. `$HOME/.secret` → `plaintext secret\n`.

**Commands**

```bash
dotsync track --encrypt .secret private
dotsync save --no-push --non-interactive private
rm $HOME/.secret
dotsync restore private --non-interactive --skip-pull --conflict overwrite
# Provide same password if prompted on restore
```

**Assertions**

- Mirror under `dotfiles/encrypt/private/.secret` exists and differs from plaintext.
- After restore: `$HOME/.secret` decrypts to original plaintext (byte match).
- Home file is regular file, not symlink.

**Cleanup**

- pytest teardown.

---

### E2 — showpw prints stored password (local only)

**Setup**

1. After E1 `passwd` with known password.

**Commands**

```bash
dotsync showpw
```

**Assertions**

- Exit 0.
- stdout trimmed equals configured password.
- Document in test docstring: local-only security warning per CLI help.

**Cleanup**

- pytest teardown.

---

### E3 — showpw exits non-zero when no password configured

**Setup**

1. Fresh repo; encrypted filelist entry but no `passwd` run.

**Commands**

```bash
dotsync showpw
```

**Assertions**

- Exit non-zero.
- stderr explains missing password.

**Cleanup**

- pytest teardown.

---

## Boundaries

### B1 — Empty filelist: save succeeds with no file ops

**Setup**

1. Init `$REPO`; filelist empty (only comments or blank).

**Commands**

```bash
dotsync save --no-push --non-interactive
```

**Assertions**

- Exit 0.
- No files under `dotfiles/` created.
- Optional: commit may still occur for metadata-only or no commit — assert per implementation (document actual behavior).

**Cleanup**

- pytest teardown.

---

### B2 — Missing remote: user declines URL → save aborts

**Maps to:** SC2 (push required for durability)

**Setup**

1. Repo without `origin`; filelist + home file ready.

**Commands**

```bash
# Interactive: empty line or 'n' when prompted for remote URL
dotsync save common
```

**Assertions**

- Exit non-zero.
- Log contains `Aborted` or equivalent.
- Local mirror may exist but push not attempted / no silent success message claiming durability.

**Cleanup**

- pytest teardown.

---

### B3 — Push failure exits non-zero

**Maps to:** SC2

**Setup**

1. `origin` points to bare repo that **rejects** push (harness: bare with `receive.denyCurrentBranch` or push to read-only remote).
2. filelist + content ready.

**Commands**

```bash
dotsync save common --non-interactive
```

**Assertions**

- Exit non-zero.
- stderr/log contains push failure message.
- Local commit may exist; test documents that durability goal failed.

**Cleanup**

- pytest teardown.

---

### B4 — Binary conflict shows summary instead of text diff

**Maps to:** SC6 (binary / encrypted diff path)

**Setup**

1. filelist: `.bin:common\n`.
2. Save a small binary blob (e.g. `printf '\x00\x01\x02\xff' > $HOME/.bin`).
3. Overwrite `$HOME/.bin` with different bytes before restore.

**Commands**

```bash
dotsync restore common
# Send 'c' (cancel) via stdin or pexpect when prompt appears — do not leave restore hanging
```

**Assertions**

- stdout/stderr contains `Binary files differ: $HOME/.bin` (NUL-byte detection per `interaction.show_restore_diff`).
- Does **not** dump raw binary to terminal.
- Prompt offers overwrite / cancel.
- After cancel (`c`): exit non-zero; `$HOME/.bin` unchanged (original conflicting bytes).

**Cleanup**

- pytest teardown.

---

### B5 — `--no-push` prints durability warning

**Setup**

1. Normal save-ready repo with origin configured.

**Commands**

```bash
dotsync save --no-push --non-interactive common
```

**Assertions**

- Exit 0.
- stderr/log contains warning that assets are not durable until pushed (wording per implementation).

**Cleanup**

- pytest teardown.

---

### B6 — Non-interactive save without remote must not hang

**Maps to:** SC2

**Setup**

1. Init `$REPO` with `filelist` + home file ready; **no** `origin`.

**Commands**

```bash
dotsync save --non-interactive common
# No --no-push — exercises push_with_remote path
```

**Assertions**

- Exits non-zero **without hanging** (closed stdin → `EOFError` today; harness must use timeout).
- Does not print success/durability message claiming push succeeded.
- Document harness rule: all other non-interactive `save` calls must pre-add `origin` or pass `--no-push`.

**Cleanup**

- pytest teardown.

---

## Harness implementation notes (Step 4 — not in scope for Step 1)

- Map each scenario ID to a pytest parametrized case or explicit function in `test_scenarios.py`.
- Provide `sandbox_factory` fixture: creates HOME, REPO, optional bare remote, sets env, returns paths + `run_dotsync(*args)` helper.
- Mark suite: `@pytest.mark.blackbox` (register in `pyproject.toml`).
- For interactive scenarios (C1, C2, T3, B2, B4, **L1** if origin not pre-added): use stdin pipe, `pexpect`, or pre-add origin in harness.
- Treat default `save` (without `--no-push`) and single-file `track` auto-update restore as **potentially interactive** even when `--non-interactive` is set elsewhere — `push_with_remote` and auto-update restore can call `input()`.
- Priority P0 scenarios should pass before P1/P2 in CI ordering if runtime is constrained.
- Suggested CI gate order: pull-safety (RP) + conflicts (C) + boundaries (B), then mirror/lifecycle/trees/symlinks, then encrypt.

---

## Review checklist (Opus 4.8 gate)

- [x] All DESIGN success criteria SC1–SC7 covered by at least one scenario.
- [x] Sandbox isolation assumptions updated (safety_checks, hostname pin, encrypt isolation, non-interactive save guard).
- [ ] Missing edge cases still deferred: v1 deprecation alias warnings, `@tree:…|encrypt`, multi-candidate selection (`--candidate`), large-file / permission errors.
- [x] Priority ordering adjusted (S6, B6 → P0; E1 → P1; L5 added).
- [x] Assertions observable via subprocess exit code + filesystem + stdout/stderr only.

---

## Opus 4.8 review summary (2026-07-16)

**Review date:** 2026-07-16  
**Reviewer:** Opus 4.8 (T16 Step 2 gate)  
**Status:** Feedback merged into this plan (Step 3).

### Key findings

1. **External symlink restore gap (SC3):** Save writes materialized external content under `plugin_dir/.dotsync/materialized/` but restore reads from `dotsync_repo/.dotsync/materialized/` — S6 added as P0 round-trip to expose or verify fix.
2. **Non-interactive save / no remote (SC2):** `push_with_remote` calls `input()` unconditionally when no origin — B6 added as P0 hang guard; sandbox convention documents the rule.
3. **`track` auto-update conflation:** Default `track` mirrors immediately and may invoke interactive restore — L5 added; L1 notes mirror may pre-exist before `save`.
4. **RP2/RP4 assertion fixes:** RP2 asserts only dotsync's `Failed to pull latest changes` (not git stderr); RP4 drops `--skip-pull`, uses `-vv`, asserts `Restoring from commit <sha>`.
5. **Sandbox hardening:** Documented `safety_checks` prerequisites, hostname pinning, encrypt plugin isolation, and post-run sandbox scan.
6. **Harness risks:** Closed stdin → `EOFError` on unexpected prompts; git stderr not captured; non-interactive restore over differing files requires `--conflict overwrite`.

**Review feedback:** Merged — see scenarios S6, B6, L5 and updated sandbox conventions above.

---

## Harness completion review (2026-07-16)

**Reviewer:** Opus 4.8 (blackbox-harness-complete T0)

### Key findings (implementation plan)

1. **No TwoMachineSandbox** — existing `Sandbox` + `home2` already covers dual-machine; thin helpers only.
2. **DEVNULL stdin default** — `run_dotsync` must default to closed stdin so C3/B6 non-prompt assertions are meaningful.
3. **`unset_repo` for L4** — pop `DOTSYNC_REPO` so track bootstraps default `~/.dotfiles`.
4. **No hostname env pin** — `info.hostname` is import-time; always pass explicit categories.
5. **S6 bug note stale** — save/restore both use `dotsync_repo` for `.dotsync/materialized/`; treat as round-trip assertion.
6. **E1 pexpect; E2/E3 seed passwd file** — no pexpect for showpw tests.
7. **Docker deferred** — home2 satisfies dual-machine; Docker optional non-gating follow-up.

**Plan:** `.vibe/dotsync-cli/.spec/blackbox-harness-complete/IMPLEMENTATION_PLAN.md`

---

## Implementation status

| Scenario | Test function | Module | Status |
|----------|---------------|--------|--------|
| L1 | `test_l1_full_lifecycle_track_save_restore` | `test_scenarios.py` | ✅ Pass |
| L2 | `test_l2_untrack_preserves_home_file` | `test_lifecycle.py` | ✅ Pass |
| L3 | `test_l3_untrack_purge_repo_deletes_mirror` | `test_lifecycle.py` | ✅ Pass |
| L4 | `test_l4_track_bootstraps_dotfiles` | `test_lifecycle.py` | ✅ Pass |
| L5 (auto-update on) | `test_l5_track_auto_update_creates_mirror_immediately` | `test_lifecycle.py` | ✅ Pass |
| L5 (`--no-auto-update`) | `test_l5_track_no_auto_update_defers_mirror_until_save` | `test_lifecycle.py` | ✅ Pass |
| M1 | `test_m1_home_never_becomes_repo_symlink` | `test_scenarios.py` | ✅ Pass |
| M2 | `test_m2_byte_identical_round_trip_atomic_file` | `test_mirror.py` | ✅ Pass |
| M3 | `test_m3_nested_tree_paths_restore_as_regular_files` | `test_mirror.py` | ✅ Pass |
| RP1 | `test_rp1_pull_runs_before_home_copy` | `test_scenarios.py` | ✅ Pass |
| RP2 | `test_rp2_diverged_repo_aborts_restore` | `test_scenarios.py` | ✅ Pass |
| RP3 | `test_rp3_skip_pull_uses_local_head_without_fetch` | `test_restore_pull.py` | ✅ Pass |
| RP4 | `test_rp4_no_remote_restore_uses_local_head` | `test_restore_pull.py` | ✅ Pass |
| C1 | `test_c1_unified_diff_cancel_aborts_entire_restore` | `test_scenarios.py` | ✅ Pass |
| C2 | `test_c2_overwrite_continues_restore_for_remaining_paths` | `test_conflicts.py` | ✅ Pass |
| C3 | `test_c3_identical_home_file_skipped_without_prompt` | `test_conflicts.py` | ✅ Pass |
| C4 | `test_c4_non_interactive_conflict_overwrite_applies_all` | `test_conflicts.py` | ✅ Pass |
| C5 | `test_c5_non_interactive_conflict_abort_exits_without_writes` | `test_conflicts.py` | ✅ Pass |
| T1 | `test_t1_new_tree_file_picked_up_on_second_save` | `test_scenarios.py` | ✅ Pass |
| T2 | `test_t2_glob_filter_on_tree_excludes_non_matching_paths` | `test_trees.py` | ✅ Pass |
| T3 | `test_t3_prune_stale_repo_file_after_tree_member_removed` | `test_trees.py` | ✅ Pass |
| T4 | `test_t4_tree_save_restore_roundtrip_on_clean_home` | `test_trees.py` | ✅ Pass |
| S1 | `test_s1_internal_symlink_materialized` | `test_scenarios.py` | ✅ Pass |
| S2 | `test_s2_external_symlink_materialized_under_dotsync_materialized` | `test_symlinks.py` | ✅ Pass |
| S3 | `test_s3_broken_symlink_warn_and_skip` | `test_symlinks.py` | ✅ Pass |
| S4 | `test_s4_dedup_when_link_target_also_watched` | `test_symlinks.py` | ✅ Pass |
| S5 | `test_s5_restore_recreates_internal_symlink_when_target_exists` | `test_symlinks.py` | ✅ Pass |
| S6 | `test_s6_external_symlink_save_restore_roundtrip` | `test_scenarios.py` | ✅ Pass |
| E1 | `test_e1_encrypt_track_save_restore_roundtrip` | `test_encrypt.py` | ✅ Pass |
| E2 | `test_e2_showpw_prints_stored_password` | `test_encrypt.py` | ✅ Pass |
| E3 | `test_e3_showpw_exits_nonzero_when_no_passwd` | `test_encrypt.py` | ✅ Pass |
| B1 | `test_b1_empty_filelist_save_succeeds_with_no_file_ops` | `test_boundaries.py` | ✅ Pass |
| B2 | `test_b2_decline_remote_url_aborts_save` | `test_boundaries.py` | ✅ Pass |
| B3 | `test_b3_push_failure_exits_nonzero` | `test_boundaries.py` | ✅ Pass |
| B4 | `test_b4_binary_conflict_shows_summary_and_cancel` | `test_boundaries.py` | ✅ Pass |
| B5 | `test_b5_no_push_prints_durability_warning` | `test_boundaries.py` | ✅ Pass |
| B6 | `test_b6_non_interactive_save_without_remote_does_not_hang` | `test_scenarios.py` | ✅ Pass |

**Summary:** 36 scenario IDs → 37 pytest functions (L5 split into auto-update on/off variants). Last verified: 2026-07-16.
