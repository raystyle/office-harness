"""inspect: officecli-engine passthrough (get/query/view html)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from office_harness import envelope
from office_harness.cmds.common import OpError, parse_opts
from office_harness.engine import officecli

_OPTS: dict[str, str | None] = {"--what": "<w>", "--path": "<p>", "--selector": "<s>"}


def run(g: envelope.Globals, tokens: list[str]) -> int:
    """Inspect one office document; ok:false from officecli maps to exit 1."""
    opts, positional = parse_opts(tokens, _OPTS)
    if len(positional) != 1:
        raise OpError("usage", "inspect takes exactly one file path")
    file = positional[0]
    if not Path(file).exists():
        raise OpError("file_not_found", f"file not found: {file}")
    what = opts.get("--what", "view")
    if what not in ("get", "query", "view"):
        raise OpError("usage", f"unknown face: {what} (get|query|view)")

    if what == "get":
        if "--path" not in opts:
            raise OpError("usage", "get requires --path (e.g. /body/p[1])")
        payload = officecli.get(file, opts["--path"])
    elif what == "query":
        if "--selector" not in opts:
            raise OpError("usage", "query requires --selector")
        payload = officecli.query(file, opts["--selector"])
    else:
        payload = officecli.view_html(file)

    if not payload.get("ok", False):
        err = payload.get("error", {})
        raise OpError("engine_reported", str(err.get("error", payload.get("data", "officecli ok:false"))))
    report: dict[str, Any] = {"mode": what, "payload": payload.get("data")}
    return envelope.finish(
        g, report, human=lambda d: print(str(d["payload"])[:2000])
    )
