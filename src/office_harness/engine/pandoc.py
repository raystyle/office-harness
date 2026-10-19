"""pandoc engine client: markdown (and friends) to docx/pdf conversion.

pandoc is the conversion bus; tectonic (already an engine) supplies the pdf
backend via ``--pdf-engine=tectonic``. Wire contract here is pandoc's own:
diagnostics on stderr, silence on success — so this client uses the plain
runner and judges success by exit code plus the artifact's existence.
"""

from __future__ import annotations

import re
from pathlib import Path

from office_harness.engine.base import TIMEOUT_COMPILE, TIMEOUT_READ, EngineStatus, discover, run_plain

ENV = "PANDOC_BIN"

_VERSION_RE = re.compile(r"pandoc (\S+)")


def status() -> EngineStatus:
    """Probe binary, path and version (never raises)."""
    try:
        binary = discover("pandoc", ENV)
    except Exception as e:  # noqa: BLE001
        return EngineStatus("pandoc", None, None, str(e))
    code, out, _ = run_plain(binary, ["--version"], TIMEOUT_READ)
    m = _VERSION_RE.search(out)
    version = m.group(1) if m else (out.strip() or None)
    return EngineStatus("pandoc", binary, version if code == 0 else None)


def _has_cjk(text: str) -> bool:
    """Report whether the text carries CJK codepoints (needs a CJK main font)."""
    return any("一" <= ch <= "鿿" or "㐀" <= ch <= "䶿" for ch in text)


def convert(
    src: str,
    out: str,
    to: str,
    pdf_engine: str = "tectonic",
    cjk_font: str = "Microsoft YaHei",
) -> tuple[bool, str, Path]:
    """Run one pandoc conversion; returns (ok, stderr_tail, artifact_path).

    A named pdf engine is resolved to its absolute path through our own
    discovery ladder first — pandoc's subprocess PATH may not include the
    ohmyenv tools, and a bare name would fail there. CJK sources get the
    template's CJKmainfont variable so the XeTeX path embeds a CJK-capable
    font (without it the text layer garbles; see room/office-mesh seq 18).
    """
    binary = discover("pandoc", ENV)
    argv = [src, "-o", out, "--from", "gfm"]
    if to == "pdf":
        engine_arg = pdf_engine
        if pdf_engine == "tectonic":
            from office_harness.engine import tectonic

            engine_arg = str(tectonic.discover("tectonic", tectonic.ENV))
        argv += ["--pdf-engine", engine_arg]
        try:
            source_text = Path(src).read_text(encoding="utf-8")
        except OSError:
            source_text = ""
        if _has_cjk(source_text):
            argv += ["-V", f"CJKmainfont={cjk_font}"]
    ok_code, _, err = run_plain(binary, argv, TIMEOUT_COMPILE)
    tail = "\n".join(err.strip().splitlines()[-6:])
    return ok_code == 0, tail, Path(out)
