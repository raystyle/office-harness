"""reader engine client: version probe + extract/search/query ops.

Exit-code semantics (reader contract): 0 hit, 1 miss, 2 error. A miss is a
business result, not an engine failure, so run() surfaces it as miss=None.
"""

from __future__ import annotations

import json
from typing import Any

from office_harness.engine.base import TIMEOUT_READ, EngineStatus, discover, run_plain

ENV = "READER_BIN"


def status() -> EngineStatus:
    """Probe binary, path and version (never raises)."""
    try:
        binary = discover("reader", ENV)
    except Exception as e:  # noqa: BLE001
        return EngineStatus("reader", None, None, str(e))
    code, out, _ = run_plain(binary, ["--version"], TIMEOUT_READ)
    version = out.strip() or None if code == 0 else None
    return EngineStatus("reader", binary, version)


def extract(file: str) -> dict[str, Any]:
    """Reader extract in json form: per-page/section text."""
    binary = discover("reader", ENV)
    code, out, err = run_plain(binary, ["extract", file, "--format", "json"], TIMEOUT_READ * 2)
    if code == 2:
        raise RuntimeError(err.strip() or "reader extract failed")
    return json.loads(out)


def search(file: str, term: str) -> dict[str, Any]:
    """Reader search: hits as json; exit 1 (miss) is a business result."""
    binary = discover("reader", ENV)
    code, out, err = run_plain(binary, ["search", file, term, "--format", "json"], TIMEOUT_READ)
    if code == 2:
        raise RuntimeError(err.strip() or "reader search failed")
    return json.loads(out)


def query(file: str, expr: str) -> tuple[int, dict[str, Any]]:
    """Reader mq query: returns (exit_code, payload); 0 hit / 1 miss / 2 error."""
    binary = discover("reader", ENV)
    code, out, err = run_plain(binary, ["query", file, expr, "--format", "json"], TIMEOUT_READ)
    if code == 2:
        raise RuntimeError(err.strip() or "reader query failed")
    return code, json.loads(out)
