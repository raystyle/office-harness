"""convert: markdown to docx/pdf via pandoc (pdf rides the tectonic engine)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from office_harness import envelope
from office_harness.cmds.common import OpError, parse_opts
from office_harness.engine import pandoc

_OPTS: dict[str, str | None] = {
    "--to": "<fmt>",
    "--out": "<file>",
    "--pdf-engine": "<engine>",
    "--cjk-font": "<font>",
    "--yes": None,
}

_SUPPORTED = ("docx", "pdf")


def _derived_out(src: Path, to: str) -> Path:
    return src.with_suffix("." + to)


def run(g: envelope.Globals, tokens: list[str]) -> int:
    """Convert one markdown file to docx or pdf; dry-run until --yes."""
    opts, positional = parse_opts(tokens, _OPTS)
    if len(positional) != 1:
        raise OpError("usage", "convert takes exactly one markdown path")
    if "--to" not in opts:
        raise OpError("usage", "convert requires --to docx|pdf")
    to = opts["--to"]
    if to not in _SUPPORTED:
        raise OpError("unsupported_format", f"convert supports {_SUPPORTED}, got {to}")
    src = Path(positional[0])
    if not src.exists():
        raise OpError("file_not_found", f"markdown file not found: {src}")
    out = opts.get("--out") or str(_derived_out(src, to))
    pdf_engine = opts.get("--pdf-engine", "tectonic")
    cjk_font = opts.get("--cjk-font", "Microsoft YaHei")

    if "--yes" not in opts:
        plan = {
            "dryrun": True,
            "src": str(src),
            "to": to,
            "would_write": out,
            "pdf_engine": pdf_engine if to == "pdf" else None,
        }
        cta = {
            "description": "Suggested command:",
            "commands": [
                {
                    "command": f"convert {src} --to {to} --yes",
                    "description": "run the conversion for real",
                }
            ],
        }
        return envelope.finish(g, plan, human=lambda d: print(f"dry-run: {d}"), cta=cta)

    ok, tail, artifact = pandoc.convert(str(src), out, to, pdf_engine=pdf_engine, cjk_font=cjk_font)
    if not ok or not artifact.exists():
        raise OpError("convert_failed", f"pandoc failed on {src}:\n{tail}")

    report: dict[str, Any] = {
        "dryrun": False,
        "src": str(src),
        "to": to,
        "out": str(artifact),
        "bytes": artifact.stat().st_size,
    }
    if to == "pdf":
        report["pdf_engine"] = pdf_engine

    def human(d: dict[str, Any]) -> None:
        engine_note = f" via {d['pdf_engine']}" if d.get("pdf_engine") else ""
        print(f"converted {d['src']} -> {d['out']}{engine_note} ({d['bytes']} bytes)")

    return envelope.finish(g, report, human=human)
