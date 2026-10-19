"""compile: .tex -> PDF via the tectonic engine client."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from office_harness import envelope
from office_harness.cmds.common import OpError, parse_opts
from office_harness.engine import tectonic

_OPTS: dict[str, str | None] = {"--out": "<dir>", "--search-path": "<dir>"}


def run(g: envelope.Globals, tokens: list[str]) -> int:
    """Compile one .tex; report pdf path + output tail; failures exit 2."""
    opts, positional = parse_opts(tokens, _OPTS)
    if len(positional) != 1:
        raise OpError("usage", "compile takes exactly one .tex path")
    file = positional[0]
    if not Path(file).exists():
        raise OpError("file_not_found", f"tex file not found: {file}")

    search_paths = opts.get("--search-path", [])
    if isinstance(search_paths, str):
        search_paths = [search_paths]
    outdir = opts.get("--out")

    ok, tail = tectonic.compile_tex(file, outdir=outdir, search_paths=search_paths)
    pdf = tectonic.pdf_path_for(file)
    if not ok:
        raise OpError("compile_failed", f"tectonic failed on {file}:\n{tail}")

    report: dict[str, Any] = {"tex": file, "pdf": str(pdf), "tail": tail}

    def human(d: dict[str, Any]) -> None:
        print(f"compiled {d['tex']} -> {d['pdf']}")

    return envelope.finish(g, report, human=human)

