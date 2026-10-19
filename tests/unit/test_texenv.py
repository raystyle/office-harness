"""texenv tests: delimiters, escaping table, NoEscape, round-trip rendering."""

from __future__ import annotations

from pathlib import Path

from office_harness.texenv import NoEscape, render, tex_escape


def test_tex_escape_table() -> None:
    assert tex_escape("a&b%c$d#e_f") == r"a\&b\%c\$d\#e\_f"
    assert tex_escape("{x}") == r"\{x\}"
    assert tex_escape("x~y^z") == r"x\textasciitilde{}y\^{}z"
    assert tex_escape("back\\slash") == "back\\textbackslash{}slash"


def test_noescape_passthrough() -> None:
    assert tex_escape(NoEscape(r"\emph{raw}")) == r"\emph{raw}"


def test_non_strings_untouched() -> None:
    assert tex_escape(42) == 42
    assert tex_escape(None) is None


def test_delimiters_do_not_clash_with_tex_braces(tmp_path: Path) -> None:
    tpl = tmp_path / "t.tex.j2"
    tpl.write_text(
        r"\section{\VAR{title | tex}}" "\n"
        r"\BLOCK{for item in items}" "\n"
        r"%- if loop.first" "\n"
        r"first: \VAR{item | tex}" "\n"
        r"%- endif" "\n"
        r"\BLOCK{endfor}" "\n"
        r"\#{this comment disappears}" "\n",
        encoding="utf-8",
    )
    out = render(str(tpl), {"title": "100% TeX & jinja", "items": ["a_b", "c%d"]})
    assert r"\section{100\% TeX \& jinja}" in out
    assert r"first: a\_b" in out
    # item[1] is not loop.first -> the if-block suppressed it entirely
    assert "c\\%d" not in out and "c%d" not in out
    assert "this comment disappears" not in out
    assert "{for item in items}" not in out  # block token fully consumed


def test_plain_tex_braces_survive(tmp_path: Path) -> None:
    tpl = tmp_path / "t.tex.j2"
    tpl.write_text(r"\begin{itemize} \item \VAR{x | tex} \end{itemize}", encoding="utf-8")
    out = render(str(tpl), {"x": "v"})
    assert r"\begin{itemize}" in out
    assert r"\end{itemize}" in out
