r"""texenv: LaTeX-safe jinja environment.

Delimiters follow the mbr/latex scheme so jinja never fights TeX braces:
variable ``\\VAR{name}``, block ``\\BLOCK{for x in xs} ... \\BLOCK{endfor}``,
comment ``\\#{...}``, line-statement prefix ``%-`` and line comment ``%# ``.
autoescape stays OFF (jinja's built-in escaping is HTML-only); data values go
through the ``tex`` filter instead, aligned with the PyLaTeX escape table —
minus its ``-`` -> ``{-}`` substitution (breaks hyphens, PyLaTeX#369).
"""

from __future__ import annotations

import re
from typing import Any

from jinja2 import Environment

TEX_MAP = [
    ("\\", r"\textbackslash{}"),
    ("&", r"\&"),
    ("%", r"\%"),
    ("$", r"\$"),
    ("#", r"\#"),
    ("_", r"\_"),
    ("{", r"\{"),
    ("}", r"\}"),
    ("~", r"\textasciitilde{}"),
    ("^", r"\^{}"),
]

# single pass: a multi-step str.replace chain would re-escape the braces the
# earlier steps just produced (\textbackslash{} -> \textbackslash\{\})
_TEX_SUB = re.compile("|".join(re.escape(src) for src, _ in TEX_MAP))
_TEX_DST = dict(TEX_MAP)


class NoEscape(str):
    """A str subclass that the tex filter passes through verbatim."""


def tex_escape(value: Any) -> Any:
    """Escape TeX specials; NoEscape instances and non-strings pass through."""
    if isinstance(value, NoEscape):
        return str(value)
    if not isinstance(value, str):
        return value
    return _TEX_SUB.sub(lambda m: _TEX_DST[m.group(0)], value)


def make_env(**kwargs: Any) -> Environment:
    """Build the LaTeX-safe environment with the tex filter registered."""
    env = Environment(
        block_start_string=r"\BLOCK{",
        block_end_string="}",
        variable_start_string=r"\VAR{",
        variable_end_string="}",
        comment_start_string=r"\#{",
        comment_end_string="}",
        line_statement_prefix="%-",
        line_comment_prefix="%#",
        autoescape=False,
        **kwargs,
    )
    env.filters["tex"] = tex_escape
    return env


def render(template_path: str, data: dict[str, Any]) -> str:
    """Render one .tex.j2 template to a .tex string."""
    env = make_env()
    with open(template_path, encoding="utf-8") as fh:
        src = fh.read()
    return env.from_string(src).render(**data)
