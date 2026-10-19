"""pptx fill via python-pptx: {{key}} anchors + {{for:name}} slide duplication.

Design stance (industry lesson): jinja-in-pptx dies on PowerPoint's run
splitting, so our templates own the runs — one ``{{key}}`` per shape. The
rewriter joins each paragraph's runs, substitutes, then writes the result
into the first run and blanks the rest, immune to how Word/PPT split runs.

A slide whose notes contain ``{{for:name}}`` is duplicated once per item of
``data[name]``; each copy's anchors resolve against the item (dict items
merge over the global context, scalars are exposed as ``item``).
"""

from __future__ import annotations

import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from pptx import Presentation

_ANCHOR = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*\}\}")
_FOR = re.compile(r"\{\{\s*for:([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


def _iter_text_frames(shape: Any) -> list[Any]:
    """All text frames of one shape, descending into groups."""
    frames: list[Any] = []
    if shape.has_text_frame:
        frames.append(shape.text_frame)
    if getattr(shape, "shapes", None):
        for sub in shape.shapes:
            frames.extend(_iter_text_frames(sub))
    return frames


def _apply_anchors(text_frame: Any, context: dict[str, Any]) -> int:
    """Rewrite {{key}} anchors in one text frame; returns the hit count."""
    hits = 0

    def lookup(match: re.Match[str]) -> str:
        nonlocal hits
        key = match.group(1)
        value: Any = context
        for part in key.split("."):
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return match.group(0)  # unresolved anchors stay literal
        hits += 1
        return str(value)

    for para in text_frame.paragraphs:
        if not para.runs:
            continue
        full = "".join(run.text for run in para.runs)
        if not _ANCHOR.search(full):
            continue
        replaced = _ANCHOR.sub(lookup, full)
        para.runs[0].text = replaced
        for run in para.runs[1:]:
            run.text = ""
    return hits


def _notes_text(slide: Any) -> str:
    if not slide.has_notes_slide:
        return ""
    return slide.notes_slide.notes_text_frame.text or ""


def _duplicate_slide(prs: Any, source: Any) -> Any:
    """One slide clone: add_slide(same layout), then copy shape XML over."""
    dest = prs.slides.add_slide(source.slide_layout)
    for shp in list(dest.shapes):
        shp._element.getparent().remove(shp._element)  # noqa: SLF001 - drop layout placeholders
    for shp in source.shapes:
        dest.shapes._spTree.append(deepcopy(shp._element))  # noqa: SLF001
    return dest


def _expand_for_slides(prs: Any, data: dict[str, Any]) -> int:
    """Duplicate {{for:name}} slides per data row; returns clones added.

    Clones append at the deck end in row order (v0.1 ordering contract).
    Each clone's anchors resolve against its row (dict rows merge over the
    global context; scalars are exposed as ``item``); the source slide keeps
    its own anchors for the global context and loses the for-marker.
    """
    clones = 0
    for slide in list(prs.slides):
        m = _FOR.search(_notes_text(slide))
        if not m:
            continue
        rows = data.get(m.group(1))
        if not isinstance(rows, list) or not rows:
            continue
        for row in rows:
            clone = _duplicate_slide(prs, slide)
            clones += 1
            ctx = {**data, **row} if isinstance(row, dict) else {**data, "item": row}
            for shape in clone.shapes:
                for tf in _iter_text_frames(shape):
                    _apply_anchors(tf, ctx)
        if slide.has_notes_slide:
            ntf = slide.notes_slide.notes_text_frame
            ntf.text = _FOR.sub("", ntf.text or "")
    return clones


def fill(template: str, data: dict[str, Any], out: str) -> dict[str, Any]:
    """Fill one pptx template; returns a report dict."""
    prs = Presentation(template)
    clones = _expand_for_slides(prs, data)
    anchors = 0
    for slide in prs.slides:
        for shape in slide.shapes:
            for tf in _iter_text_frames(shape):
                anchors += _apply_anchors(tf, data)
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out_path))
    return {
        "engine": "python-pptx",
        "template": template,
        "out": str(out_path),
        "anchors": anchors,
        "clones": clones,
        "bytes": out_path.stat().st_size,
    }
