"""render: .tex.j2 template + json/yaml data -> .tex via texenv."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from office_harness import envelope
from office_harness.cmds.common import OpError, parse_opts
from office_harness.texenv import render as tex_render

_OPTS: dict[str, str | None] = {"--data": "<file>", "--out": "<file>"}


def load_data(path: str) -> dict[str, Any]:
    """Load json or yaml data by extension (json default for unknown)."""
    p = Path(path)
    if not p.exists():
        raise OpError("data_not_found", f"data file not found: {path}")
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() in (".yaml", ".yml"):
        loaded = yaml.safe_load(text)
    else:
        loaded = json.loads(text)
    if not isinstance(loaded, dict):
        raise OpError("data_invalid", "data root must be an object/mapping")
    return loaded


def run(g: envelope.Globals, tokens: list[str]) -> int:
    """Render the template with data; write .tex next to it or to --out."""
    opts, positional = parse_opts(tokens, _OPTS)
    if len(positional) != 1:
        raise OpError("usage", "render takes exactly one template path")
    template = positional[0]
    if "--data" not in opts:
        raise OpError("usage", "render requires --data <file>")

    data = load_data(opts["--data"])
    rendered = tex_render(template, data)

    tpl_path = Path(template)
    out_path = Path(opts.get("--out", str(tpl_path.with_suffix(""))))
    if out_path.suffix != ".tex":
        out_path = out_path.with_suffix(".tex")
    out_path.write_text(rendered, encoding="utf-8")

    report = {
        "template": template,
        "data": opts["--data"],
        "out": str(out_path),
        "bytes": len(rendered.encode("utf-8")),
    }

    def human(d: dict[str, Any]) -> None:
        print(f"rendered {d['template']} + {d['data']} -> {d['out']} ({d['bytes']} bytes)")

    return envelope.finish(g, report, human=human)

