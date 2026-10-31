"""kami command tests: build fill, render via engine seam, check gates."""

from __future__ import annotations

import json
from pathlib import Path

from office_harness import run
from office_harness.engine import kami as kami_engine

_FILLS = {"fills": {"{{A}}": ["甲"], "{{B}}": ["乙", "丙"]}}


def _template(tmp_path: Path) -> Path:
    tpl = tmp_path / "t.html"
    tpl.write_text("<html><body>{{A}}/{{B}}/{{B}}</body></html>", encoding="utf-8")
    return tpl


def test_kami_build_dryrun_and_apply(tmp_path: Path, capsys) -> None:
    tpl = _template(tmp_path)
    data = tmp_path / "fills.json"
    data.write_text(json.dumps(_FILLS), encoding="utf-8")
    code = run.main(["kami", "build", str(tpl), "--data", str(data), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["data"]["dryrun"] is True

    code = run.main(["kami", "build", str(tpl), "--data", str(data),
                     "--out", str(tmp_path / "out.html"), "--yes", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    body = Path(payload["data"]["out"]).read_text(encoding="utf-8")
    assert body == "<html><body>甲/乙/丙</body></html>"
    assert payload["data"]["placeholders_left"] == 0


def test_kami_build_exhausted_placeholder(tmp_path: Path, capsys) -> None:
    """值多于占位符出现次数 = fills_invalid;值少于出现次数不算错(left 会报)。"""
    tpl = tmp_path / "once.html"
    tpl.write_text("<html><body>{{A}}</body></html>", encoding="utf-8")
    data = tmp_path / "over.json"
    data.write_text(json.dumps({"fills": {"{{A}}": ["甲", "乙"]}}), encoding="utf-8")
    code = run.main(["kami", "build", str(tpl), "--data", str(data), "--yes"])
    err = json.loads(capsys.readouterr().err.strip().splitlines()[-1])
    assert code == 2
    assert err["code"] == "fills_invalid"
    assert "exhausted" in err["message"]


def test_kami_build_leftover_reported(tmp_path: Path, capsys) -> None:
    """值少于占位符出现次数:成功但 placeholders_left > 0,由 check 面把门。"""
    tpl = _template(tmp_path)
    data = tmp_path / "short.json"
    data.write_text(json.dumps({"fills": {"{{A}}": ["甲"], "{{B}}": ["乙"]}}), encoding="utf-8")
    code = run.main(["kami", "build", str(tpl), "--data", str(data), "--yes", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["data"]["placeholders_left"] == 1


def test_kami_render_via_engine_seam(tmp_path: Path, capsys, monkeypatch) -> None:
    html = tmp_path / "doc.html"
    html.write_text("<html><body>x</body></html>", encoding="utf-8")

    def fake_render(html_path: Path, pdf_path: Path) -> int:
        pdf_path.write_bytes(b"%PDF-1.4 fake")
        return 3

    monkeypatch.setattr(kami_engine, "render_pdf", fake_render)
    code = run.main(["kami", "render", str(html), "--out", str(tmp_path / "o.pdf"),
                     "--yes", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["data"]["pages"] == 3
    assert Path(payload["data"]["pdf"]).exists()


def test_kami_check_gates_placeholders(tmp_path: Path, capsys) -> None:
    dirty = tmp_path / "dirty.html"
    dirty.write_text("<html><body>{{A}} 好</body></html>", encoding="utf-8")
    code = run.main(["kami", "check", str(dirty), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0  # 成功信封
    assert payload["data"]["ok"] is False
    assert any("unfilled" in i for i in payload["data"]["issues"])

    clean = tmp_path / "clean.html"
    clean.write_text("<html><body>技战法好</body></html>", encoding="utf-8")
    code = run.main(["kami", "check", str(clean), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["data"]["ok"] is True


def test_kami_check_coverage_with_vendored_content(tmp_path: Path, capsys) -> None:
    html = tmp_path / "doc.html"
    html.write_text("<html><body>智能无损攻击模拟系统 技战法200+</body></html>", encoding="utf-8")
    content = tmp_path / "content.json"
    content.write_text(json.dumps({"content": {"title": "智能无损攻击模拟系统",
                                               "note": "技战法200+"}}), encoding="utf-8")
    code = run.main(["kami", "check", str(html), "--content", str(content), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["data"]["ok"] is True
    assert payload["data"]["checked"] == 2

    missing = tmp_path / "missing.json"
    missing.write_text(json.dumps({"content": {"title": "不存在的标题"}}), encoding="utf-8")
    code = run.main(["kami", "check", str(html), "--content", str(missing), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["ok"] is False
    assert payload["data"]["issues"]
