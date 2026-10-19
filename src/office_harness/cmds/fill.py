"""fill: dispatch docx/pptx/xlsx templates to the matching library fill."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from office_harness import envelope
from office_harness.cmds.common import OpError, parse_opts
from office_harness.cmds.render import load_data
from office_harness.fills import docx_fill, pptx_fill, xlsx_fill

_OPTS: dict[str, str | None] = {"--data": "<file>", "--out": "<file>", "--yes": None}

_FILLERS = {".docx": docx_fill.fill, ".pptx": pptx_fill.fill, ".xlsx": xlsx_fill.fill}


def _derived_out(template: Path) -> Path:
    return template.with_name(template.stem + "-out" + template.suffix)


def run(g: envelope.Globals, tokens: list[str]) -> int:
    """Fill the template with data; dry-run report until --yes."""
    opts, positional = parse_opts(tokens, _OPTS)
    if len(positional) != 1:
        raise OpError("usage", "fill takes exactly one template path")
    if "--data" not in opts:
        raise OpError("usage", "fill requires --data <file>")
    template = Path(positional[0])
    if not template.exists():
        raise OpError("file_not_found", f"template not found: {template}")
    filler = _FILLERS.get(template.suffix.lower())
    if filler is None:
        raise OpError("unsupported_format", f"fill supports {sorted(_FILLERS)}, got {template.suffix}")
    data = load_data(opts["--data"])
    out = opts.get("--out") or str(_derived_out(template))

    if "--yes" not in opts:
        plan = {
            "dryrun": True,
            "template": str(template),
            "data": opts["--data"],
            "would_write": out,
            "engine": filler.__module__.rsplit(".", 1)[-1],
        }
        cta = {
            "description": "Suggested command:",
            "commands": [
                {
                    "command": f"fill {template} --data {opts['--data']} --yes",
                    "description": "apply for real (writes the output file)",
                }
            ],
        }
        return envelope.finish(g, plan, human=lambda d: print(f"dry-run: {d}"), cta=cta)

    report: dict[str, Any] = filler(str(template), data, out)
    report["dryrun"] = False

    def human(d: dict[str, Any]) -> None:
        print(f"filled {d['template']} -> {d['out']} ({d['bytes']} bytes, engine {d['engine']})")

    return envelope.finish(g, report, human=human)
