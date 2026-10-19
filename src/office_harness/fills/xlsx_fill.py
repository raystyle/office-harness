"""xlsx fill via openpyxl: {{key}} anchors, whole-cell or inline.

Whole-cell anchors (``{{name}}`` alone) take typed values and list expansion
(items append as rows below, cloning the anchor cell's style). Inline anchors
inside longer text substitute as strings. Unresolved anchors stay literal.
"""

from __future__ import annotations

import re
from copy import copy
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

_WHOLE = re.compile(r"^\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}$")
_INLINE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")

# spill functions carry no spill metadata in openpyxl files: only the top-left
# cell gets a value and recalc reports zero errors on the truncated result
_SPILL_FUNCS = ("XLOOKUP", "XMATCH", "SORT", "FILTER", "UNIQUE", "SEQUENCE")


def _formula_lint(wb: Any) -> list[str]:
    """Formula-compatibility warnings (official xlsx-skill policy)."""
    warns: list[str] = []
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                v = cell.value
                if not isinstance(v, str) or not v.startswith("="):
                    continue
                ref = f"{ws.title}!{cell.coordinate}"
                if v[1:2].islower():
                    warns.append(f"{ref}: lowercase formula tell (engine parse failure): {v[:48]}")
                upper = v.upper()
                for fn in _SPILL_FUNCS:
                    if fn in upper:
                        warns.append(f"{ref}: spill function {fn} truncates without spill metadata")
    return warns


def _inline_sub(text: str, data: dict[str, Any]) -> tuple[str, int]:
    """Substitute inline anchors with scalar values; returns (text, hits)."""
    hits = 0

    def repl(m: re.Match[str]) -> str:
        nonlocal hits
        v = data.get(m.group(1))
        if isinstance(v, (list, dict)) or v is None:
            return m.group(0)  # unresolved or non-scalar stays literal
        hits += 1
        return str(v)

    return _INLINE.sub(repl, text), hits


def fill(template: str, data: dict[str, Any], out: str) -> dict[str, Any]:
    """Fill one xlsx template; returns a report dict."""
    wb = load_workbook(template)
    anchors = 0
    unresolved: list[str] = []
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if not isinstance(cell.value, str):
                    continue
                stripped = cell.value.strip()
                m = _WHOLE.match(stripped)
                if m:
                    key = m.group(1)
                    value = data.get(key)
                    if isinstance(value, list):
                        # list anchor: first item in place, rest appended below
                        cell.value = value[0] if value else None
                        anchors += 1
                        r = cell.row
                        for item in value[1:]:
                            r += 1
                            target = ws.cell(row=r, column=cell.column)
                            target.value = item
                            if cell.has_style:
                                target._style = copy(cell._style)  # noqa: SLF001 - style clone
                    elif value is not None:
                        cell.value = value
                        anchors += 1
                    else:
                        unresolved.append(key)
                    continue
                new_text, hits = _inline_sub(cell.value, data)
                if hits:
                    cell.value = new_text
                    anchors += hits
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(out_path))
    report: dict[str, Any] = {
        "engine": "openpyxl",
        "template": template,
        "out": str(out_path),
        "anchors": anchors,
        "bytes": out_path.stat().st_size,
    }
    if unresolved:
        report["unresolved"] = unresolved
    formula_warnings = _formula_lint(wb)
    if formula_warnings:
        report["formula_warnings"] = formula_warnings
    return report
