"""convert command tests: dry-run face + fake-engine apply paths."""

from __future__ import annotations

import json
from pathlib import Path

from office_harness import run


def _md(path: Path) -> Path:
    path.write_text(
        "# 标题\n\n正文段落,带 **加粗** 与列表:\n\n- 甲\n- 乙\n\n| 列 | 值 |\n|---|---|\n| a | 1 |\n",
        encoding="utf-8",
    )
    return path


def test_convert_dryrun_and_usage(tmp_path: Path, capsys) -> None:
    src = _md(tmp_path / "d.md")
    code = run.main(["convert", str(src), "--to", "docx", "--json", "--full-output"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["data"]["dryrun"] is True
    assert payload["meta"]["cta"]["commands"][0]["command"].endswith("--yes")
    code = run.main(["convert", str(src)])
    err = json.loads(capsys.readouterr().err.strip().splitlines()[-1])
    assert code == 2
    assert err["code"] == "usage"
    code = run.main(["convert", str(src), "--to", "epub"])
    err = json.loads(capsys.readouterr().err.strip().splitlines()[-1])
    assert code == 2
    assert err["code"] == "unsupported_format"


def test_convert_docx_via_fake_engine(fake_engine, pandoc_stub, tmp_path: Path, capsys) -> None:
    src = _md(tmp_path / "c.md")
    out = tmp_path / "c.docx"
    out.write_bytes(b"PK-fake-docx")
    fake_engine.script(("pandoc", str(src)), (0, "", ""))
    code = run.main(["convert", str(src), "--to", "docx", "--out", str(out), "--yes", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["data"]["to"] == "docx"
    assert payload["data"]["bytes"] > 0
    convert_call = fake_engine.calls[0]
    assert "--pdf-engine" not in convert_call  # docx never passes a pdf engine


def test_convert_pdf_passes_pdf_engine(fake_engine, pandoc_stub, tmp_path: Path, capsys) -> None:
    src = _md(tmp_path / "p.md")
    out = tmp_path / "p.pdf"
    out.write_bytes(b"%PDF-fake")
    fake_engine.script(("pandoc", str(src)), (0, "", ""))
    code = run.main(["convert", str(src), "--to", "pdf", "--out", str(out), "--yes", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["data"]["pdf_engine"] == "tectonic"
    argv = " ".join(fake_engine.calls[0])
    # named engine resolves to an absolute path (pandoc PATH may lack it)
    assert "--pdf-engine" in argv and "tectonic.exe" in argv
    # CJK source triggers the CJK main-font variable
    assert "-V CJKmainfont=Microsoft YaHei" in argv
