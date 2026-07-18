"""Black-box test helpers (pexpect, encrypt passwd seeding)."""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from tests.blackbox.conftest import Sandbox

from dotsync.plugins.encrypt import key_stretch
from tests.blackbox.conftest import DotsyncResult, dotsync_argv


def run_dotsync_pexpect(
    sb: Sandbox,
    *args: str,
    responses: Sequence[str] = (),
    timeout: float = 120,
    cwd: Path | None = None,
    home: Path | None = None,
    repo: Path | None = None,
    unset_repo: bool = False,
    extra_env: dict | None = None,
) -> DotsyncResult:
    """Run dotsync with pexpect for TTY/password prompts (E1)."""
    import pexpect

    env = sb.env_for(home=home, repo=repo, unset_repo=unset_repo)
    if extra_env:
        env.update(extra_env)
    work_cwd = str(cwd or home or sb.home)

    prompts = [
        "Enter new password: ",
        "Re-enter new password: ",
        "Encryption password: ",
    ]
    response_iter = iter(responses)
    output_buffer = io.StringIO()

    argv = dotsync_argv(*args)
    child = pexpect.spawn(
        argv[0],
        argv[1:],
        cwd=work_cwd,
        env=env,
        encoding="utf-8",
        timeout=timeout,
    )
    child.logfile_read = output_buffer

    while True:
        try:
            idx = child.expect(prompts + [pexpect.EOF], timeout=timeout)
        except pexpect.TIMEOUT as exc:
            child.close(force=True)
            raise AssertionError(
                f"dotsync timed out for args={args!r}; output={output_buffer.getvalue()!r}"
            ) from exc
        if idx == len(prompts):
            break
        try:
            response = next(response_iter)
        except StopIteration as exc:
            child.close(force=True)
            raise AssertionError(
                f"Unexpected password prompt {prompts[idx]!r} for args={args!r}; "
                f"output={output_buffer.getvalue()!r}"
            ) from exc
        child.sendline(response)

    try:
        child.expect(pexpect.EOF, timeout=timeout)
    except pexpect.TIMEOUT:
        pass

    child.close()
    combined = output_buffer.getvalue()
    returncode = child.exitstatus
    if returncode is None:
        returncode = child.signalstatus if child.signalstatus is not None else -1

    sb.assert_isolated()
    return DotsyncResult(
        returncode=returncode,
        stdout=combined,
        stderr="",
        combined=combined,
    )


def seed_encrypt_passwd(
    sb: Sandbox,
    password: str,
    *,
    repo: Path | None = None,
) -> Path:
    """Write ``$REPO/.plugins/encrypt/passwd`` for E2/E3 without ``dotsync passwd``."""
    repo_dir = repo or sb.repo
    passwd_dir = repo_dir / ".plugins" / "encrypt"
    passwd_dir.mkdir(parents=True, exist_ok=True)
    passwd_path = passwd_dir / "passwd"

    salt = os.urandom(32)
    key = key_stretch(password.encode(), salt)
    data = {"pword": key, "salt": salt.hex(), "secret": password}
    passwd_path.write_text(json.dumps(data))

    return passwd_path
