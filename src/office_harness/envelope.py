"""Envelope: global-flag scanning, machine/human output, error channel, exit codes.

Contract (single outward truth, mirrored by cli.py faces):

- stdout: JSON ``{"ok": true, "data": ...}`` (indent 2, ensure_ascii False);
  ``--full-output`` adds ``meta {command, duration_ms, cta?}``.
- stderr: single-line JSON ``{"code", "message", "retryable"?, "cta"?}``.
- exit codes: 0 success / 1 business miss / 2 usage or system error.
- human face: default format ``toon``; each command passes a ``human=`` render
  callback used only when not machine mode.
- bare invocation is handled in cli.py (two-line face, exit 0).
"""

from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Any

EXIT_OK = 0
EXIT_MISS = 1
EXIT_USAGE = 2

FORMAT_FAMILIES = ("toon", "json", "yaml", "md")


class UsageError(Exception):
    """Raised for flag-level misuse; maps to exit 2 with a stderr envelope."""


@dataclass
class Globals:
    """Parsed global flags plus dispatch context for one invocation."""

    json_mode: bool = False
    full: bool = False
    filter_spec: str | None = None
    format_family: str = "toon"
    format_conflict: bool = False
    command: str | None = None
    t0: float = field(default_factory=time.perf_counter)


def _apply_format(g: Globals, val: str) -> None:
    if val == "json":
        if g.json_mode:
            g.format_conflict = True
        g.json_mode = True
    else:
        g.json_mode = False
        g.format_family = val


def _split_global_flags(argv: list[str]) -> tuple[Globals, list[str]]:
    """Value-aware, position-independent scan for the seven global flags.

    ``--json`` and ``--format json`` are mutually exclusive at this layer;
    giving both raises a UsageError via the conflict marker on Globals.
    """
    g = Globals()
    rest: list[str] = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--json":
            if g.json_mode:
                g.format_conflict = True
            g.json_mode = True
        elif a == "--full-output":
            g.full = True
        elif a == "--filter-output":
            if i + 1 >= len(argv):
                raise UsageError("--filter-output requires a value: --filter-output <keys>")
            i += 1
            g.filter_spec = argv[i]
        elif a.startswith("--filter-output="):
            g.filter_spec = a.split("=", 1)[1]
        elif a == "--format":
            if i + 1 >= len(argv):
                raise UsageError("--format requires a value: toon|json|yaml|md")
            i += 1
            _apply_format(g, argv[i])
        elif a.startswith("--format="):
            _apply_format(g, a.split("=", 1)[1])
        else:
            rest.append(a)
        i += 1
    return g, rest


@dataclass
class StderrError:
    """Single-line stderr JSON error, the machine-readable failure channel."""

    code: str
    message: str
    retryable: bool = False
    cta: dict[str, Any] | None = None


def emit_error(e: StderrError, exit_code: int = EXIT_USAGE) -> int:
    """Write the single-line stderr JSON and return the exit code (never raises)."""
    payload: dict[str, Any] = {"code": e.code, "message": e.message}
    if e.retryable:
        payload["retryable"] = True
    if e.cta is not None:
        payload["cta"] = e.cta
    sys.stderr.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return exit_code


def print_json(obj: Any) -> None:
    """Write one pretty JSON object to stdout (indent 2, non-ASCII kept)."""
    sys.stdout.write(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


_SEG = re.compile(r"^([^[\]]+)((?:\[[^\]]*\])*)$")
_IDX = re.compile(r"\[([^\]]*)\]")


def _walk(data: Any, path: str) -> Any:
    """Walk one comma-free path: dot nesting, optional [i] / [i,j] indices."""
    cur = data
    for seg in path.split("."):
        if seg == "":
            continue
        m = _SEG.match(seg)
        if m is None:
            raise KeyError(path)
        key, idxstr = m.group(1), m.group(2)
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            raise KeyError(path)
        for idx in _IDX.finditer(idxstr):
            body = idx.group(1)
            if not body:
                raise KeyError(path)
            if "," in body:
                if not isinstance(cur, list):
                    raise KeyError(path)
                picks = [int(n) for n in body.split(",")]
                cur = [cur[n] for n in picks]
            else:
                n = int(body)
                if not isinstance(cur, list) or not -len(cur) <= n < len(cur):
                    raise KeyError(path)
                cur = cur[n]
    return cur


def filter_data(data: Any, spec: str | None) -> Any:
    """Apply ``--filter-output`` comma paths: ``a.b,items[0,2],x[0].name``.

    Commas inside brackets do NOT split paths (items[0,2] is one path). Single
    path returns the value itself; multiple paths return a list in the given
    order. Unknown paths raise KeyError (caller renders as usage error).
    """
    if spec is None:
        return data
    paths: list[str] = []
    cur_path: list[str] = []
    depth = 0
    for ch in spec:
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            paths.append("".join(cur_path).strip())
            cur_path = []
        else:
            cur_path.append(ch)
    paths.append("".join(cur_path).strip())
    paths = [p for p in paths if p]
    if not paths:
        return data
    values = [_walk(data, p) for p in paths]
    return values[0] if len(values) == 1 else values


def finish(
    g: Globals,
    data: Any,
    human: Any = None,
    cta: dict[str, Any] | None = None,
) -> int:
    """Emit the success envelope (or the human face) and return 0.

    Field order is insertion order; never alphabetized (dev-cli AF:59).
    """
    if g.json_mode or g.filter_spec is not None or human is None or g.format_family != "toon":
        try:
            payload_data = filter_data(data, g.filter_spec)
        except KeyError as exc:
            raise UsageError(f"filter path not found: {exc.args[0]}") from exc
        payload: dict[str, Any] = {"ok": True, "data": payload_data}
        if g.full:
            meta: dict[str, Any] = {
                "command": f"office-harness {g.command or ''}".strip(),
                "duration_ms": int((time.perf_counter() - g.t0) * 1000),
            }
            if cta is not None:
                meta["cta"] = cta
            payload["meta"] = meta
        print_json(payload)
    else:
        if callable(human):
            human(data)
        else:
            print_json(data)
    return EXIT_OK
