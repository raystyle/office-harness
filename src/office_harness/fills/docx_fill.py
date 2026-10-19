"""docx fill via docxtpl: jinja tags live in the Word document itself."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from docxtpl import DocxTemplate


def fill(template: str, data: dict[str, Any], out: str) -> dict[str, Any]:
    """Render one docxtpl template; returns a small report dict."""
    tpl = DocxTemplate(template)
    tpl.render(data)
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tpl.save(str(out_path))
    return {"engine": "docxtpl", "template": template, "out": str(out_path), "bytes": out_path.stat().st_size}
