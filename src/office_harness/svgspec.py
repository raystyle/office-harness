"""svgspec: declarative json/yaml spec -> svg.py element tree -> svg string.

The spec is a plain dict tree aimed at agents: every node is
``{"el": <tag>, ...attrs, "children": [node...]}`` (text via ``"text"``).
Tags map onto svg.py classes (typed, zero-dep, full SVG standard coverage);
unknown tags are refused with the closest known names in the error.

Transform values accept either the svg.py typed form
(``{"translate": {"x": 10, "y": 10}}``) or a raw attribute string
(``"translate(10 10)"``) — the raw form is wrapped in ``extra``-free
serialization by emitting it through svg.Transform subclasses where a typed
class exists, else via the generic ``extra`` dict on the element.
"""

from __future__ import annotations

import difflib
from typing import Any

import svg
from svg._transforms import Matrix, Rotate, Scale, SkewX, SkewY, Translate

_TEXT_KEY = "text"
_CHILDREN_KEY = "children"
_EL_KEY = "el"

_TRANSFORM_TYPES: dict[str, type] = {
    "translate": Translate,
    "rotate": Rotate,
    "scale": Scale,
    "matrix": Matrix,
    "skewx": SkewX,
    "skewy": SkewY,
}


def _known_tags() -> list[str]:
    return [n for n in dir(svg) if n[:1].isupper() and isinstance(getattr(svg, n), type)]


def _coerce_transform(value: Any) -> Any:
    """Accept a raw transform string or a typed dict; pass lists through."""
    if isinstance(value, str):
        # raw attribute form: parse the leading function name and reuse the
        # typed class so serialization stays canonical
        head = value.split("(", 1)[0].strip().lower()
        cls = _TRANSFORM_TYPES.get(head)
        if cls is None:
            return value  # svg.py tolerates raw strings via extra; caller's risk
        inner = value.split("(", 1)[1].rsplit(")", 1)[0] if "(" in value else ""
        parts = [p.strip() for p in inner.replace(",", " ").split()] if inner else []
        try:
            if cls is Translate:
                return Translate(x=float(parts[0]), y=float(parts[1]) if len(parts) > 1 else 0)
            if cls is Rotate:
                return Rotate(a=float(parts[0]), x=float(parts[1]) if len(parts) > 1 else 0,
                              y=float(parts[2]) if len(parts) > 2 else 0)
            if cls is Scale:
                return Scale(x=float(parts[0]), y=float(parts[1]) if len(parts) > 1 else None)
            if cls is Matrix:
                return Matrix(a=float(parts[0]), b=float(parts[1]), c=float(parts[2]),
                              d=float(parts[3]), e=float(parts[4]), f=float(parts[5]))
            if cls is SkewX:
                return SkewX(a=float(parts[0]))
            return SkewY(a=float(parts[0]))
        except (IndexError, ValueError):
            return value
    if isinstance(value, dict):
        (name, kw), = value.items()
        cls = _TRANSFORM_TYPES[name.lower()]
        return cls(**kw)
    return value


def _build_node(node: Any) -> Any:
    """Recursively build one svg.py element from a spec node."""
    if isinstance(node, str):
        return node  # svg.py accepts raw strings inside elements lists
    if not isinstance(node, dict) or _EL_KEY not in node:
        raise ValueError(f"spec node must be a dict with an '{_EL_KEY}' key: {node!r}")
    node = dict(node)  # never mutate the caller's spec
    tag = node.pop(_EL_KEY)
    cls = getattr(svg, tag, None)
    if cls is None or not isinstance(cls, type):
        close = difflib.get_close_matches(tag, _known_tags(), n=3)
        raise ValueError(f"unknown svg element: {tag} (closest: {', '.join(close) or 'none'})")
    attrs: dict[str, Any] = {}
    children: list[Any] = list(node.pop(_CHILDREN_KEY, []) or [])
    if _TEXT_KEY in node:
        attrs[_TEXT_KEY] = node.pop(_TEXT_KEY)
    for key, value in node.items():
        if key == "transform":
            values = value if isinstance(value, list) else [value]
            attrs["transform"] = [_coerce_transform(v) for v in values]
        elif key == "viewBox" and isinstance(value, (list, tuple)):
            attrs["viewBox"] = " ".join(str(v) for v in value)
        elif key == "points" and isinstance(value, (list, tuple)):
            attrs["points"] = [(v[0], v[1]) for v in value]
        else:
            attrs[key] = value
    built = [c if isinstance(c, str) else _build_node(c) for c in children]
    if built:
        attrs["elements"] = built
    return cls(**attrs)


def build(spec: dict[str, Any]) -> str:
    """Render a full spec (the root svg node) to an svg string."""
    root = dict(spec)
    if root.get(_EL_KEY, "SVG") != "SVG":
        raise ValueError("spec root must be an SVG node (or omit 'el')")
    root.setdefault(_EL_KEY, "SVG")
    return str(_build_node(root))
