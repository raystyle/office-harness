"""read: reader-engine passthrough (extract/search), miss = exit 1."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from office_harness import envelope
from office_harness.cmds.common import MissError, OpError, parse_opts
from office_harness.engine import reader

_OPTS: dict[str, str | None] = {"--mode": "<m>", "--term": "<t>", "--expr": "<e>"}


def run(g: envelope.Globals, tokens: list[str]) -> int:
    """Extract or search one document; search miss is a business exit 1."""
    opts, positional = parse_opts(tokens, _OPTS)
    if len(positional) != 1:
        raise OpError("usage", "read takes exactly one file path")
    file = positional[0]
    if not Path(file).exists():
        raise OpError("file_not_found", f"file not found: {file}")
    mode = opts.get("--mode", "extract")
    if mode not in ("extract", "search", "query"):
        raise OpError("usage", f"unknown mode: {mode} (extract|search|query)")

    if mode == "search":
        if "--term" not in opts:
            raise OpError("usage", "search requires --term")
        payload = reader.search(file, opts["--term"])
        report: dict[str, Any] = {"mode": "search", "term": opts["--term"], "payload": payload}
        hits = payload.get("data", {}).get("hits") or payload.get("data", {}).get("results") or []
        if not hits:
            raise MissError("no_hit", f"no match for {opts['term']!r} in {file}")
        return envelope.finish(
            g, report, human=lambda d: print(f"{len(hits)} hit(s) for {d['term']}")
        )

    # extract (query lands with the mq docs; same reader op family)
    payload = reader.extract(file)
    report = {"mode": "extract", "payload": payload}
    return envelope.finish(
        g, report, human=lambda d: print(str(d["payload"].get("data", ""))[:2000])
    )
