"""Black-box E2E sandbox harness for dotsync CLI subprocess tests."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

import pytest

# Fixed git identity for reproducible commits inside sandboxes.
GIT_AUTHOR_NAME = "Dotsync Blackbox"
GIT_AUTHOR_EMAIL = "blackbox@test.dotsync.local"

# Project root (dotsync repo containing pyproject.toml).
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def dotsync_argv(*args: str) -> list[str]:
    """CLI argv for subprocess runs: uv locally, python -m dotsync in CI."""
    if shutil.which("uv"):
        return ["uv", "run", "dotsync", *args]
    return [sys.executable, "-m", "dotsync", *args]


@dataclass
class DotsyncResult:
    returncode: int
    stdout: str
    stderr: str
    combined: str


@dataclass
class Sandbox:
    """Isolated HOME + DOTSYNC_REPO environment for one scenario."""

    root: Path
    home: Path
    repo: Path
    bare: Optional[Path] = None
    home2: Optional[Path] = None
    _env: dict = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self.home.mkdir(parents=True, exist_ok=True)
        self.repo.mkdir(parents=True, exist_ok=True)
        self._env = self._base_env(home=self.home, repo=self.repo)

    @staticmethod
    def _base_env(*, home: Path, repo: Path) -> dict:
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(home),
                "USERPROFILE": str(home),
                "DOTSYNC_REPO": str(repo),
                "GIT_AUTHOR_NAME": GIT_AUTHOR_NAME,
                "GIT_AUTHOR_EMAIL": GIT_AUTHOR_EMAIL,
                "GIT_COMMITTER_NAME": GIT_AUTHOR_NAME,
                "GIT_COMMITTER_EMAIL": GIT_AUTHOR_EMAIL,
                "XDG_CONFIG_HOME": str(home / ".config"),
                "XDG_CACHE_HOME": str(home / ".cache"),
                "XDG_DATA_HOME": str(home / ".local" / "share"),
            }
        )
        return env

    def env_for(
        self,
        *,
        home: Optional[Path] = None,
        repo: Optional[Path] = None,
        unset_repo: bool = False,
    ) -> dict:
        h = home or self.home
        r = repo or self.repo
        if h == self.home and r == self.repo:
            env = dict(self._env)
        else:
            env = self._base_env(home=h, repo=r)
        if unset_repo:
            env.pop("DOTSYNC_REPO", None)
        return env

    def init_bare_remote(self) -> Path:
        self.bare = self.root / "bare.git"
        self.bare.mkdir(parents=True, exist_ok=True)
        self.git_cmd("init", "--bare", cwd=self.bare)
        return self.bare

    def init_home2(self) -> Path:
        self.home2 = self.root / "home2"
        self.home2.mkdir(parents=True, exist_ok=True)
        return self.home2

    def bare_url(self) -> str:
        if self.bare is None:
            raise ValueError("bare remote not initialized; call init_bare_remote() first")
        return f"file://{self.bare.resolve()}"

    def run_dotsync(
        self,
        *args: str,
        cwd: Optional[Path] = None,
        home: Optional[Path] = None,
        repo: Optional[Path] = None,
        stdin: Optional[str] = None,
        timeout: float = 120,
        extra_env: Optional[dict] = None,
        unset_repo: bool = False,
    ) -> DotsyncResult:
        cmd = dotsync_argv(*args)
        env = self.env_for(home=home, repo=repo, unset_repo=unset_repo)
        if extra_env:
            env.update(extra_env)
        run_kwargs = {
            "cwd": str(cwd or home or self.home),
            "env": env,
            "text": True,
            "capture_output": True,
            "timeout": timeout,
        }
        if stdin is not None:
            run_kwargs["input"] = stdin
        else:
            run_kwargs["stdin"] = subprocess.DEVNULL
        proc = subprocess.run(cmd, **run_kwargs)
        result = DotsyncResult(
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            combined=proc.stdout + proc.stderr,
        )
        self.assert_isolated()
        return result

    def git_cmd(
        self,
        *args: str,
        cwd: Optional[Path] = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        work = cwd or self.repo
        env = self.env_for()
        return subprocess.run(
            ["git", *args],
            cwd=str(work),
            env=env,
            text=True,
            capture_output=True,
            check=check,
        )

    def init_repo(self, filelist: str = "", *, commit: bool = True) -> None:
        """Initialize git repo + filelist (safety_checks prerequisites)."""
        if not (self.repo / ".git").exists():
            self.git_cmd("init", cwd=self.repo)
        flist_path = self.repo / "filelist"
        flist_path.write_text(filelist)
        if commit:
            self.git_cmd("add", "filelist", cwd=self.repo)
            status = self.git_cmd("status", "--porcelain", cwd=self.repo, check=True)
            if status.stdout.strip():
                self.git_cmd(
                    "commit", "-m", "init filelist",
                    cwd=self.repo,
                )

    def write_home(self, relpath: str, content: str, *, home: Optional[Path] = None) -> Path:
        target = (home or self.home) / relpath.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return target

    def add_origin(self, bare: Optional[Path] = None) -> None:
        remote = bare or self.bare
        if remote is None:
            raise ValueError("no bare remote")
        url = f"file://{remote.resolve()}"
        existing = self.git_cmd("remote", cwd=self.repo, check=False)
        if "origin" in existing.stdout.split():
            self.git_cmd("remote", "set-url", "origin", url, cwd=self.repo)
        else:
            self.git_cmd("remote", "add", "origin", url, cwd=self.repo)

    def head_sha(self, *, cwd: Optional[Path] = None) -> str:
        return self.git_cmd("rev-parse", "HEAD", cwd=cwd or self.repo).stdout.strip()

    def ls_remote_head(self) -> str:
        out = self.git_cmd("ls-remote", "--heads", "origin", cwd=self.repo).stdout
        for line in out.splitlines():
            sha, _ref = line.split("\t", 1)
            return sha
        raise AssertionError("no heads on origin")

    def mirror_path(self, category: str, relpath: str) -> Path:
        return self.repo / "dotfiles" / "plain" / category / relpath.lstrip("/")

    def save_no_push(self, *categories: str) -> DotsyncResult:
        args: List[str] = ["save", "--no-push", "--non-interactive"]
        args.extend(categories)
        return self.run_dotsync(*args)

    def restore(
        self,
        *categories: str,
        skip_pull: bool = False,
        conflict: Optional[str] = None,
        extra_args: Sequence[str] = (),
        **kwargs,
    ) -> DotsyncResult:
        args: List[str] = ["restore", *categories, "--non-interactive"]
        if skip_pull:
            args.append("--skip-pull")
        if conflict:
            args.extend(["--conflict", conflict])
        args.extend(extra_args)
        return self.run_dotsync(*args, **kwargs)

    def restore_fresh(
        self,
        home: Path,
        *categories: str,
        conflict: str = "overwrite",
        extra_args: Sequence[str] = (),
        **kwargs,
    ) -> DotsyncResult:
        """Restore onto a fresh HOME (e.g. home2) from bare remote."""
        if self.bare is None:
            raise ValueError("bare remote not initialized; call init_bare_remote() first")
        home_repo = home / ".dotfiles"
        args: List[str] = [
            "restore",
            "--remote",
            self.bare_url(),
            "--categories",
            ",".join(categories),
            "--yes",
        ]
        if conflict:
            args.extend(["--conflict", conflict])
        args.extend(extra_args)
        return self.run_dotsync(
            *args,
            cwd=home,
            home=home,
            repo=home_repo,
            **kwargs,
        )

    def assert_isolated(self) -> None:
        """Fail if anything outside the sandbox root was modified."""
        root = self.root.resolve()
        for path in root.rglob("*"):
            try:
                path.resolve().relative_to(root)
            except ValueError as exc:
                raise AssertionError(f"sandbox path escaped root: {path}") from exc

    def symlinks_pointing_into_repo(self, home: Optional[Path] = None) -> List[Path]:
        base = home or self.home
        repo_real = self.repo.resolve()
        found: List[Path] = []
        if not base.exists():
            return found
        for dirpath, dirnames, filenames in os.walk(base):
            # Do not descend into the dotfiles repo clone under home.
            if Path(dirpath).resolve() == repo_real:
                dirnames.clear()
                continue
            names: Iterable[str] = list(dirnames) + list(filenames)
            for name in names:
                p = Path(dirpath) / name
                if p.is_symlink():
                    try:
                        target = p.resolve()
                    except OSError:
                        continue
                    if repo_real in target.parents or target == repo_real:
                        found.append(p)
        return found


@pytest.fixture
def sandbox_factory(tmp_path):
    """Factory fixture: each call returns a fresh Sandbox."""

    def _factory(*, with_bare: bool = False, with_home2: bool = False) -> Sandbox:
        sb = Sandbox(root=tmp_path, home=tmp_path / "home", repo=tmp_path / "repo")
        if with_bare:
            sb.init_bare_remote()
        if with_home2:
            sb.init_home2()
        return sb

    return _factory


def publish_to_bare(
    sb: Sandbox,
    filelist: str,
    home_files: dict,
    *,
    categories: Optional[Sequence[str]] = None,
) -> str:
    """Push dotfiles content to sb.bare from a throwaway source repo; return remote HEAD sha."""
    if sb.bare is None:
        sb.init_bare_remote()

    source_home = sb.root / "source_home"
    source_home.mkdir(exist_ok=True)
    work = sb.root / "publish_work"
    work.mkdir(exist_ok=True)

    env = sb.env_for(home=source_home, repo=work)
    subprocess.run(
        dotsync_argv("init"),
        cwd=str(work),
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    (work / "filelist").write_text(filelist)
    sb.git_cmd("add", "filelist", cwd=work)
    sb.git_cmd("commit", "-m", "add filelist", cwd=work)

    for rel, content in home_files.items():
        path = source_home / rel.lstrip("/")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    cats = list(categories) if categories else ["common"]
    subprocess.run(
        dotsync_argv("save", "--no-push", "--non-interactive", *cats),
        cwd=str(work),
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    sb.git_cmd("add", ".", cwd=work)
    status = sb.git_cmd("status", "--porcelain", cwd=work)
    if status.stdout.strip():
        sb.git_cmd("commit", "-m", "mirror dotfiles", cwd=work)

    url = sb.bare_url()
    sb.git_cmd("remote", "add", "origin", url, cwd=work)
    branch = sb.git_cmd("rev-parse", "--abbrev-ref", "HEAD", cwd=work).stdout.strip()
    sb.git_cmd("push", "-u", "origin", branch, cwd=work)

    return sb.git_cmd("rev-parse", "HEAD", cwd=work).stdout.strip()


def setup_repo_behind_remote(sb: Sandbox, filelist: str, remote_content: str) -> str:
    """Bare has newer content than sb.repo; return expected remote HEAD sha."""
    first_sha = publish_to_bare(
        sb,
        filelist,
        {".file": "initial-version\n"},
        categories=["common"],
    )

    work = sb.root / "advance_work"
    work.mkdir(exist_ok=True)
    clone = work / "clone"
    sb.git_cmd("clone", sb.bare_url(), str(clone), cwd=sb.root)
    mirror = clone / "dotfiles" / "plain" / "common" / ".file"
    mirror.write_text(remote_content)
    sb.git_cmd("add", ".", cwd=clone)
    sb.git_cmd("commit", "-m", "remote advance", cwd=clone)
    sb.git_cmd("push", "origin", "HEAD", cwd=clone)
    remote_sha = sb.git_cmd("rev-parse", "HEAD", cwd=clone).stdout.strip()

    # Replace sb.repo with a clone pinned to the older commit.
    if sb.repo.exists():
        shutil.rmtree(sb.repo)
    sb.git_cmd("clone", sb.bare_url(), str(sb.repo), cwd=sb.root)
    sb.git_cmd("reset", "--hard", first_sha, cwd=sb.repo)
    return remote_sha


def setup_diverged_repo(sb: Sandbox, filelist: str) -> None:
    """Local repo and origin have diverged histories."""
    publish_to_bare(sb, filelist, {".file": "initial\n"}, categories=["common"])
    sb.init_repo(filelist)
    sb.add_origin()
    sb.git_cmd("fetch", "origin", cwd=sb.repo)
    branch = sb.git_cmd("rev-parse", "--abbrev-ref", "HEAD", cwd=sb.repo).stdout.strip()
    if branch == "HEAD":
        branch = "master"
        sb.git_cmd("checkout", "-B", "master", "FETCH_HEAD", cwd=sb.repo)
    else:
        sb.git_cmd("reset", "--hard", "FETCH_HEAD", cwd=sb.repo)

    # Remote advances.
    work = sb.root / "remote_work"
    work.mkdir(exist_ok=True)
    sb.git_cmd("clone", sb.bare_url(), str(work / "clone"), cwd=sb.root)
    clone = work / "clone"
    mirror = clone / "dotfiles" / "plain" / "common" / ".file"
    mirror.write_text("remote-version\n")
    sb.git_cmd("add", ".", cwd=clone)
    sb.git_cmd("commit", "-m", "remote change", cwd=clone)
    sb.git_cmd("push", "origin", "HEAD", cwd=clone)

    # Local diverges.
    local_mirror = sb.mirror_path("common", ".file")
    local_mirror.parent.mkdir(parents=True, exist_ok=True)
    local_mirror.write_text("local-version\n")
    sb.git_cmd("add", ".", cwd=sb.repo)
    sb.git_cmd("commit", "-m", "local change", cwd=sb.repo)
