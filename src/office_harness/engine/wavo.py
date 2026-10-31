"""wavo engine client: local GPU audio transcription (whisper/parakeet gguf).

Wire contract is wavo's own: transcript rides stdout (``--srt`` subtitles /
``--json`` token timeline / default plain text), diagnostics ride stderr, so
this client uses the plain runner and judges success by exit code plus a
non-empty stdout. Pitfalls baked in:

- a missing model would prompt interactively (stdin is null under capture),
  so the client never relies on the prompt: callers pre-check with
  :func:`list_models`, or opt into wavo's ``-y`` auto-download via ``pull``;
- whisper-family models want ``--segment 30`` (split at pauses); the caller
  owns the default, the engine only forwards it;
- Chinese proper nouns are occasionally misheard (可研 -> 可言); formal
  deliverables need a terminology pass over the artifact.
"""

from __future__ import annotations

import re
from pathlib import Path

from office_harness.engine.base import TIMEOUT_COMPILE, TIMEOUT_READ, EngineStatus, discover, run_plain

ENV = "WAVO_BIN"

_VERSION_RE = re.compile(r"wavo (\S+)")

_FORMAT_FLAGS = {"srt": "--srt", "json": "--json", "text": None}


def status() -> EngineStatus:
    """Probe binary, path and version (never raises)."""
    try:
        binary = discover("wavo", ENV)
    except Exception as e:  # noqa: BLE001
        return EngineStatus("wavo", None, None, str(e))
    code, out, _ = run_plain(binary, ["--version"], TIMEOUT_READ)
    m = _VERSION_RE.search(out)
    version = m.group(1) if m else (out.strip() or None)
    return EngineStatus("wavo", binary, version if code == 0 else None)


def list_models(binary: Path | None = None) -> list[str]:
    """Names of locally pulled models (HF cache scan; empty list when none)."""
    binary = binary or discover("wavo", ENV)
    code, out, _ = run_plain(binary, ["list"], TIMEOUT_READ)
    if code != 0:
        return []
    names = []
    for line in out.strip().splitlines()[1:]:  # header: NAME SIZE PATH
        first = line.split()
        if first:
            names.append(first[0])
    return names


def transcribe(
    file: str,
    model: str = "whisper-turbo",
    segment: int = 30,
    fmt: str = "srt",
    pull: bool = False,
) -> tuple[bool, str, Path]:
    """Run one transcription; returns (ok, payload_or_stderr_tail, artifact).

    ``payload_or_stderr_tail`` is the stdout transcript on success (the caller
    writes it to the output file) or the last stderr lines on failure.
    """
    binary = discover("wavo", ENV)
    if fmt not in _FORMAT_FLAGS:
        raise ValueError(f"unknown wavo format: {fmt}")
    argv: list[str] = ["run", model, file, "--segment", str(segment)]
    flag = _FORMAT_FLAGS[fmt]
    if flag is not None:
        argv.append(flag)
    if pull:
        argv.append("-y")
    code, out, err = run_plain(binary, argv, TIMEOUT_COMPILE)
    payload = out.strip()
    ok = code == 0 and bool(payload)
    tail = payload if ok else "\n".join((err or "").strip().splitlines()[-6:])
    return ok, tail, artifact_for(file, fmt)


def artifact_for(file: str, fmt: str) -> Path:
    """Default artifact path: same stem as the audio, format-derived suffix."""
    suffix = {"srt": ".srt", "json": ".json", "text": ".txt"}[fmt]
    return Path(file).with_suffix(suffix)
