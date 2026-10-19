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
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if not isinstance(cell.value, str):
                    continue
                stripped = cell.value.strip()
                m = _WHOLE.match(stripped)
                if m:
                    key = m.group(1)
                    value = data.get(key, cell.value)
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
                    else:
                        cell.value = value
                        anchors += 1
                    continue
                new_text, hits = _inline_sub(cell.value, data)
                if hits:
                    cell.value = new_text
                    anchors += hits
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(out_path))
    return {
        "engine": "openpyxl",
        "template": template,
        "out": str(out_path),
        "anchors": anchors,
        "bytes": out_path.stat().st_size,
    }
