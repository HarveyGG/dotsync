"""Black-box encrypt scenarios E1–E3 from tests/blackbox/test_plan.md."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from tests.blackbox.conftest import Sandbox
from tests.blackbox.helpers import run_dotsync_pexpect, seed_encrypt_passwd

pytestmark = pytest.mark.blackbox

TEST_PASSWORD = "testpass123"


def _gpg_available() -> bool:
    try:
        subprocess.run(["gpg", "--version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def _pexpect_available() -> bool:
    try:
        import pexpect  # noqa: F401
    except ImportError:
        return False
    return True


@pytest.fixture
def gpg_sandbox():
    """Sandbox root outside pytest's ``pytest-of-*`` dir (gpg-agent breaks there)."""
    root = Path(tempfile.mkdtemp(prefix="dotsync-bb-"))
    sb = Sandbox(root=root, home=root / "home", repo=root / "repo")
    try:
        yield sb
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _encrypt_writes_only_under_repo_plugins(sb) -> bool:
    plugins_root = sb.repo / ".plugins"
    if not plugins_root.exists():
        return True
    allowed = plugins_root.resolve()
    for path in plugins_root.rglob("*"):
        if path.is_file():
            try:
                path.resolve().relative_to(allowed)
            except ValueError:
                return False
    return True


@pytest.mark.skipif(
    not _gpg_available(),
    reason="gpg not available",
)
@pytest.mark.skipif(
    not _pexpect_available(),
    reason="pexpect not available",
)
def test_e1_encrypt_track_save_restore_roundtrip(gpg_sandbox):
    """E1: passwd + track --encrypt → save → restore round-trip (SC3)."""
    sb = gpg_sandbox
    sb.init_repo("")
    sb.write_home(".secret", "plaintext secret\n")

    result = run_dotsync_pexpect(
        sb,
        "passwd",
        responses=[TEST_PASSWORD, TEST_PASSWORD],
    )
    assert result.returncode == 0, result.combined
    assert _encrypt_writes_only_under_repo_plugins(sb)

    result = run_dotsync_pexpect(
        sb,
        "track",
        "--encrypt",
        ".secret",
        "private",
        responses=[TEST_PASSWORD, TEST_PASSWORD],
    )
    assert result.returncode == 0, result.combined

    result = run_dotsync_pexpect(
        sb,
        "save",
        "--no-push",
        "--non-interactive",
        "private",
        responses=[TEST_PASSWORD],
    )
    assert result.returncode == 0, result.combined

    encrypted = sb.repo / "dotfiles" / "encrypt" / "private" / ".secret"
    assert encrypted.exists()
    assert encrypted.read_text() != "plaintext secret\n"

    (sb.home / ".secret").unlink()
    result = run_dotsync_pexpect(
        sb,
        "restore",
        "private",
        "--non-interactive",
        "--skip-pull",
        "--conflict",
        "overwrite",
        responses=[TEST_PASSWORD],
    )
    assert result.returncode == 0, result.combined

    restored = sb.home / ".secret"
    assert restored.exists()
    assert not restored.is_symlink()
    assert restored.read_text() == "plaintext secret\n"


def test_e2_showpw_prints_stored_password(sandbox_factory):
    """E2: showpw prints seeded password (local machine only — do not log stdout)."""
    sb = sandbox_factory()
    sb.init_repo(".secret:private|encrypt\n")
    seed_encrypt_passwd(sb, TEST_PASSWORD)

    result = sb.run_dotsync("showpw")
    assert result.returncode == 0, result.combined
    assert result.stdout.strip() == TEST_PASSWORD


def test_e3_showpw_exits_nonzero_when_no_passwd(sandbox_factory):
    """E3: showpw exits non-zero when no encryption password is configured."""
    sb = sandbox_factory()
    sb.init_repo(".secret:private|encrypt\n")

    result = sb.run_dotsync("showpw")
    assert result.returncode != 0
    assert "No encryption password configured" in result.combined
