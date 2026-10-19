"""tectonic engine client: version probe + compile with pitfalls baked in.

Pitfalls learned on this machine (see room/office-mesh R-receipts):
- TEXINPUTS with Windows paths is NOT honored; use ``-Z search-path=<dir>``.
- bundle has no biber; biblatex backend=biber templates need a bibtex patch.
- fonts are found by FILE (ctex fontsets) but not by NAME (fontspec on
  Windows fontconfig); templates should prefer system font names.
- the bundle freezes at the TeXLive 2022 expl3 layer; templates written
  against newer pregenerated variants (e.g. regex_split:nVN) need a compat
  shim: cs_generate_variant:Nn on the FULL base signature (:nnN, not :nN).
"""

from __future__ import annotations

import re
from pathlib import Path

from office_harness.engine.base import TIMEOUT_COMPILE, TIMEOUT_READ, EngineStatus, discover, run_plain

ENV = "TECTONIC_BIN"

_VERSION_RE = re.compile(r"Tectonic (\S+)")


def status() -> EngineStatus:
    """Probe binary, path and version (never raises)."""
    try:
        binary = discover("tectonic", ENV)
    except Exception as e:  # noqa: BLE001
        return EngineStatus("tectonic", None, None, str(e))
    code, out, _ = run_plain(binary, ["--version"], TIMEOUT_READ)
    m = _VERSION_RE.search(out)
    version = m.group(1) if m else (out.strip() or None)
    return EngineStatus("tectonic", binary, version if code == 0 else None)


def compile_tex(
    file: str, outdir: str | None = None, search_paths: list[str] | None = None
) -> tuple[bool, str]:
    """Compile one .tex; returns (ok, tail_of_output) — caller wraps the story."""
    binary = discover("tectonic", ENV)
    argv = []
    for sp in search_paths or []:
        argv += ["-Z", f"search-path={sp}"]
    if outdir:
        argv += ["-o", outdir]
    argv.append(file)
    code, out, err = run_plain(binary, argv, TIMEOUT_COMPILE)
    tail = "\n".join((out + err).strip().splitlines()[-6:])
    return code == 0, tail


def pdf_path_for(file: str) -> Path:
    """Return the pdf path tectonic writes for ``file`` (same stem, same dir)."""
    return Path(file).with_suffix(".pdf")
