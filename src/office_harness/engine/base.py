"""Engine client base: subprocess seam, wire protocol, timeouts, discovery.

One op = one external command invocation. The wire contract is: stdout must be
exactly one JSON envelope (officecli/reader already speak it; tectonic speaks
plain text and is wrapped by its own client). Protocol failure is judged on
the stdout SHAPE, never on the exit code. Diagnostics ride stderr, unparsed.

``_execute`` is the documented test seam — monkeypatch it (see
tests/unit/conftest.py FakeEngine).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TIMEOUT_READ = 30
TIMEOUT_WRITE = 120
TIMEOUT_COMPILE = 600
_TIMEOUT_ENV = "OFFICE_HARNESS_TIMEOUT"

OHMYENV = Path(r"D:\ohmyenv")


class OpError(Exception):
    """Engine op failure with a typed code; retryable only for timeouts."""

    def __init__(self, code: str, message: str, retryable: bool = False):
        """Store the typed code, message and retryability flag."""
        super().__init__(message)
        self.code = code
        self.retryable = retryable


def _env_timeout(default: int) -> int:
    raw = os.environ.get(_TIMEOUT_ENV)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def discover(tool: str, env_var: str) -> Path:
    r"""Discovery ladder: env override -> PATH -> D:\ohmyenv\<tool> glob."""
    raw = os.environ.get(env_var)
    if raw:
        p = Path(raw)
        if p.exists():
            return p
        raise OpError("engine_not_found", f"{env_var}={raw} does not exist")
    on_path = shutil.which(tool)
    if on_path:
        return Path(on_path)
    for cand in (OHMYENV / tool).glob(f"{tool}.exe"):
        return cand
    for cand in (OHMYENV / tool).glob(tool):
        return cand
    raise OpError("engine_not_found", f"{tool} not found (set {env_var} or extend PATH)")


def _execute(argv: list[str], timeout: int) -> tuple[int, str, str]:
    """Spawn one subprocess; return (exit_code, stdout, stderr).

    Test seam — monkeypatch me. CREATE_NO_WINDOW keeps consoles clean; on
    timeout the whole tree is killed so residents cannot leak.
    """
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            timeout=timeout,
            creationflags=creationflags,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise OpError("op_timeout", f"engine timed out after {timeout}s: {argv[0]}", retryable=True) from e
    out = (proc.stdout or b"").decode("utf-8", "replace")
    err = (proc.stderr or b"").decode("utf-8", "replace")
    return proc.returncode, out, err


def run_enveloped(binary: Path, argv: list[str], timeout: int = TIMEOUT_READ) -> dict[str, Any]:
    """Run an engine that answers with exactly one JSON envelope on stdout.

    Protocol failure = stdout not being one JSON object, judged regardless of
    exit code. An ok:false payload is returned as-is (business semantics live
    with the caller); a missing ok key is a protocol failure.
    """
    code, out, err = _execute([str(binary), *argv], timeout)
    stripped = out.strip()
    if not stripped.startswith("{") or "\n{" in stripped:
        raise OpError("engine_protocol", f"stdout is not one JSON object (exit {code})")
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as e:
        raise OpError("engine_protocol", f"stdout JSON parse failed: {e}") from e
    if not isinstance(payload, dict) or "ok" not in payload:
        raise OpError("engine_protocol", "stdout JSON lacks the ok key")
    return payload


def run_plain(binary: Path, argv: list[str], timeout: int = TIMEOUT_COMPILE) -> tuple[int, str, str]:
    """Run an engine with a plain-text contract (tectonic); caller interprets."""
    return _execute([str(binary), *argv], timeout)


@dataclass(frozen=True)
class EngineStatus:
    """One engine's probe result: path/version on success, problem otherwise."""

    name: str
    path: Path | None
    version: str | None
    problem: str | None = None
