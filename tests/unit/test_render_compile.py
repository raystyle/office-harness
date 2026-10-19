"""render/compile command tests: tmp files, FakeEngine for tectonic spawn."""

from __future__ import annotations

import json
from pathlib import Path

from office_harness import run


def test_render_roundtrip(tmp_path: Path, capsys) -> None:
    tpl = tmp_path / "t.tex.j2"
    tpl.write_text(r"\title{\VAR{x | tex}}" "\n" r"\VAR{n}", encoding="utf-8")
    data = tmp_path / "d.json"
    data.write_text(json.dumps({"x": "a&b", "n": 3}), encoding="utf-8")
    code = run.main(["render", str(tpl), "--data", str(data), "--out", str(tmp_path / "o.tex"), "--json"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["ok"] is True
    written = Path(out["data"]["out"]).read_text(encoding="utf-8")
    assert r"\title{a\&b}" in written
    assert "3" in written


def test_render_missing_data_is_op_error(tmp_path: Path, capsys) -> None:
    tpl = tmp_path / "t.tex.j2"
    tpl.write_text(r"\VAR{x}", encoding="utf-8")
    code = run.main(["render", str(tpl), "--data", str(tmp_path / "nope.json")])
    err = capsys.readouterr().err
    assert code == 2
    payload = json.loads(err.strip().splitlines()[-1])
    assert payload["code"] == "data_not_found"


def test_compile_missing_file(tmp_path: Path, capsys) -> None:
    code = run.main(["compile", str(tmp_path / "nope.tex")])
    payload = json.loads(capsys.readouterr().err.strip().splitlines()[-1])
    assert code == 2
    assert payload["code"] == "file_not_found"


def test_compile_ok_via_fake_engine(fake_engine, tmp_path: Path, capsys) -> None:
    tex = tmp_path / "ok.tex"
    tex.write_text(r"\documentclass{article}\begin{document}x\end{document}", encoding="utf-8")
    pdf = tmp_path / "ok.pdf"
    pdf.write_bytes(b"%PDF-fake")
    fake_engine.script(("tectonic", str(tex)), (0, "note: Writing `ok.pdf'\n", ""))
    code = run.main(["compile", str(tex), "--json"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["data"]["pdf"].endswith("ok.pdf")
    assert "Writing" in out["data"]["tail"]


def test_compile_failure_reports_tail(fake_engine, tmp_path: Path, capsys) -> None:
    tex = tmp_path / "bad.tex"
    tex.write_text("garbage", encoding="utf-8")
    fake_engine.script(("tectonic", str(tex)), (1, "error: undefined control sequence\n", ""))
    code = run.main(["compile", str(tex), "--json"])
    payload = json.loads(capsys.readouterr().err.strip().splitlines()[-1])
    assert code == 2
    assert payload["code"] == "compile_failed"
    assert "undefined control sequence" in payload["message"]

