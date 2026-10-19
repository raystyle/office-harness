"""officecli engine client: version probe + inspection ops (get/query/view)."""

from __future__ import annotations

from typing import Any

from office_harness.engine.base import TIMEOUT_READ, EngineStatus, discover, run_enveloped, run_plain

ENV = "OFFICECLI_BIN"


def status() -> EngineStatus:
    """Probe binary, path and version (never raises; problems ride the report)."""
    try:
        binary = discover("officecli", ENV)
    except Exception as e:  # noqa: BLE001 - status reports, never raises
        return EngineStatus("officecli", None, None, str(e))
    code, out, _ = run_plain(binary, ["--version"], TIMEOUT_READ)
    version = out.strip() or None if code == 0 else None
    return EngineStatus("officecli", binary, version)


def get(file: str, path: str) -> dict[str, Any]:
    """Officecli get: one element by path, JSON envelope passthrough."""
    return run_enveloped(discover("officecli", ENV), ["get", file, path, "--json"], TIMEOUT_READ)


def query(file: str, selector: str) -> dict[str, Any]:
    """Officecli query: css-like selector match, JSON envelope passthrough."""
    return run_enveloped(discover("officecli", ENV), ["query", file, selector, "--json"], TIMEOUT_READ)


def view_html(file: str) -> dict[str, Any]:
    """Officecli view html: rendered snapshot for agents to look at."""
    return run_enveloped(discover("officecli", ENV), ["view", file, "html"], TIMEOUT_READ * 2)
