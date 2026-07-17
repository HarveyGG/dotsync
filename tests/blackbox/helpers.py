"""Black-box test helpers (pexpect, encrypt passwd seeding)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from tests.blackbox.conftest import Sandbox

from tests.blackbox.conftest import DotsyncResult


def run_dotsync_pexpect(
    sb: Sandbox,
    *args: str,
    responses: Sequence[str] = (),
    timeout: float = 120,
    **kwargs,
) -> DotsyncResult:
    """Run dotsync with pexpect for TTY/password prompts (E1).

    Stub for Task 6 — interactive passwd/track/save/restore flows.
    """
    raise NotImplementedError("pexpect wrapper for E1 — implement in Task 6")


def seed_encrypt_passwd(
    sb: Sandbox,
    password: str,
    *,
    repo: Path | None = None,
) -> Path:
    """Write ``$REPO/.plugins/encrypt/passwd`` for E2/E3 without ``dotsync passwd``.

    Stub for Task 6 — seed JSON with salt/hash/secret matching EncryptPlugin format.
    """
    raise NotImplementedError("passwd seed helper for E2/E3 — implement in Task 6")
