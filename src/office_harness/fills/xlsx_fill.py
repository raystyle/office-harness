"""xlsx fill via openpyxl: {{key}} cell anchors, values typed by data.

Anchors are written as the cell's whole content (``{{name}}``). Lists under
key ``rows`` append row-blocks below the anchor's row, cloned from the anchor
row's formatting. Numbers stay numbers (openpyxl writes the data value as-is).
"""

from __future__ import annotations

import re
from copy import copy
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

_ANCHOR = re.compile(r"^\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}$")


def fill(template: str, data: dict[str, Any], out: str) -> dict[str, Any]:
    """Fill one xlsx template; returns a report dict."""
    wb = load_workbook(template)
    anchors = 0
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if not isinstance(cell.value, str):
                    continue
                m = _ANCHOR.match(cell.value.strip())
                if not m:
                    continue
                key = m.group(1)
                value = data.get(key, cell.value)
                rows = value if isinstance(value, list) else None
                if rows is None:
                    cell.value = value
                    anchors += 1
                    continue
                # list anchor: first row in place, rest appended below
                cell.value = rows[0] if rows else None
                anchors += 1
                r = cell.row
                for item in rows[1:]:
                    r += 1
                    target = ws.cell(row=r, column=cell.column)
                    target.value = item
                    if cell.has_style:
                        target._style = copy(cell._style)  # noqa: SLF001 - style clone
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
