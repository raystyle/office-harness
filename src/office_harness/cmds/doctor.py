"""doctor: self-check engines and libraries; report versions and problems."""

from __future__ import annotations

from typing import Any

from office_harness import envelope
from office_harness.engine import officecli, pandoc, reader, tectonic


def _lib_version(modname: str) -> tuple[str | None, str | None]:
    """Import one library and report (version, problem); never raises."""
    try:
        mod = __import__(modname)
        return (getattr(mod, "__version__", None), None)
    except Exception as e:  # noqa: BLE001 - report, never raise
        return (None, str(e))


def run(g: envelope.Globals, tokens: list[str]) -> int:
    """Probe engines and libraries, then emit the health report."""
    if tokens:
        raise ValueError("doctor takes no arguments")
    engines = []
    for probe in (officecli.status, reader.status, tectonic.status, pandoc.status):
        st = probe()
        engines.append(
            {
                "name": st.name,
                "path": str(st.path) if st.path else None,
                "version": st.version,
                "problem": st.problem,
            }
        )
    libs = []
    for modname in ("jinja2", "docxtpl", "pptx", "openpyxl", "yaml", "pydantic"):
        v, problem = _lib_version(modname)
        libs.append({"name": modname, "version": v, "problem": problem})
    ok = all(not e["problem"] for e in engines) and all(not lib["problem"] for lib in libs)
    report: dict[str, Any] = {"ok": ok, "engines": engines, "libs": libs}

    def human(d: dict[str, Any]) -> None:
        for e in d["engines"]:
            state = e["version"] or e["problem"] or "?"
            print(f"{e['name']}: {state}")
        for lib in d["libs"]:
            state = lib["version"] or lib["problem"] or "?"
            print(f"{lib['name']}: {state}")

    return envelope.finish(g, report, human=human)
