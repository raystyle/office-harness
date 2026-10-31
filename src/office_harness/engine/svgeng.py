"""SVG engine clients: agent-svgtools (judge/render/trace) and oxvg (optimise).

Wire contracts are the two CLIs' own:

- agent-svgtools speaks TOON/JSON on stdout (``--format json`` for machine
  use); exit 2 on a ``--threshold`` miss, so this client parses the JSON and
  leaves threshold semantics to the caller;
- oxvg writes optimised svg to stdout by default (``-o`` targets a file);
  diagnostics ride stderr, success is judged by exit code plus a non-empty
  stdout.

The build path does not spawn anything: it renders the svg.py object tree
in-process (pure python, typed, zero deps).
"""

from __future__ import annotations

import json
import re
from typing import Any

from office_harness.engine.base import (
    TIMEOUT_COMPILE,
    TIMEOUT_READ,
    EngineStatus,
    OpError,
    discover,
    run_plain,
)

SVGTOOLS_ENV = "AGENT_SVGTOOLS_BIN"
OXVG_ENV = "OXVG_BIN"

_VERSION_RE = re.compile(r"agent-svgtools (\S+)")
_OXVG_VERSION_RE = re.compile(r"oxvg (\S+)")


def svgtools_status() -> EngineStatus:
    """Probe agent-svgtools binary, path and version (never raises)."""
    try:
        binary = discover("agent-svgtools", SVGTOOLS_ENV)
    except Exception as e:  # noqa: BLE001
        return EngineStatus("agent-svgtools", None, None, str(e))
    code, out, _ = run_plain(binary, ["--version"], TIMEOUT_READ)
    m = _VERSION_RE.search(out)
    version = m.group(1) if m else (out.strip() or None)
    return EngineStatus("agent-svgtools", binary, version if code == 0 else None)


def oxvg_status() -> EngineStatus:
    """Probe oxvg binary, path and version (never raises)."""
    try:
        binary = discover("oxvg", OXVG_ENV)
    except Exception as e:  # noqa: BLE001
        return EngineStatus("oxvg", None, None, str(e))
    code, out, _ = run_plain(binary, ["--version"], TIMEOUT_READ)
    m = _OXVG_VERSION_RE.search(out)
    version = m.group(1) if m else (out.strip() or None)
    return EngineStatus("oxvg", binary, version if code == 0 else None)


def judge(
    reference: str,
    candidate: str,
    diff_image: str | None = None,
    threshold: int = 0,
) -> dict[str, Any]:
    """Score candidate svg against a raster reference; returns the parsed JSON.

    ``threshold`` is forwarded to agent-svgtools (exit 2 on a miss) but the
    caller owns business semantics: this client raises on any non-zero exit
    with the stderr tail, and returns the score envelope on success.
    """
    binary = discover("agent-svgtools", SVGTOOLS_ENV)
    argv = ["judge", "--format", "json"]
    if diff_image:
        argv += ["--diff-image", diff_image]
    if threshold > 0:
        argv += ["--threshold", str(threshold)]
    argv += [reference, candidate]
    code, out, err = run_plain(binary, argv, TIMEOUT_COMPILE)
    if code != 0:
        tail = "\n".join((err or out).strip().splitlines()[-6:])
        raise OpError("judge_failed", f"agent-svgtools judge failed (exit {code}):\n{tail}")
    try:
        return json.loads(out.strip())
    except json.JSONDecodeError as e:
        raise OpError("judge_protocol", f"judge stdout is not JSON: {e}") from e


def optimise(src: str) -> tuple[bool, str]:
    """Run one oxvg optimise to stdout; returns (ok, svg_payload_or_stderr_tail).

    oxvg's stdout IS the optimised svg (its ``-o`` exists but routing writes
    through the engine would make the artifact depend on engine fs behavior;
    this harness keeps engines text-only and lets the command layer write).
    """
    binary = discover("oxvg", OXVG_ENV)
    code, out_text, err = run_plain(binary, ["optimise", src], TIMEOUT_COMPILE)
    if code != 0:
        tail = "\n".join((err or out_text).strip().splitlines()[-6:])
        return False, tail
    payload = out_text.strip()
    return bool(payload), payload
