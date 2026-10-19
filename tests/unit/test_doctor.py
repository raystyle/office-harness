"""doctor command tests via the FakeEngine seam (no real engine spawned)."""

from __future__ import annotations

import json

from office_harness import run


def envelope_ok(data=None) -> str:
    return json.dumps({"ok": True, "data": data if data is not None else {}}, ensure_ascii=False)


def test_doctor_json_with_faked_engines(fake_engine, pandoc_stub, capsys) -> None:
    fake_engine.script(("officecli", "--version"), (0, "1.0.160+raystyle-fork\n", ""))
    fake_engine.script(("reader", "--version"), (0, "reader 0.11.0\n", ""))
    fake_engine.script(("tectonic", "--version"), (0, "Tectonic 0.17.0\n", ""))
    fake_engine.script(("pandoc", "--version"), (0, "pandoc 3.12.1\n", ""))
    code = run.main(["doctor", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["ok"] is True
    engines = {e["name"]: e for e in out["data"]["engines"]}
    assert engines["officecli"]["version"] == "1.0.160+raystyle-fork"
    assert engines["reader"]["version"] == "reader 0.11.0"
    assert engines["tectonic"]["version"] == "0.17.0"
    assert engines["pandoc"]["version"] == "3.12.1"
    assert out["data"]["ok"] is True


def test_doctor_human_face(fake_engine, pandoc_stub, capsys) -> None:
    fake_engine.script(("officecli", "--version"), (0, "1.0.160\n", ""))
    fake_engine.script(("reader", "--version"), (0, "reader 0.11.0\n", ""))
    fake_engine.script(("tectonic", "--version"), (0, "Tectonic 0.17.0\n", ""))
    fake_engine.script(("pandoc", "--version"), (0, "pandoc 3.12.1\n", ""))
    code = run.main(["doctor"])
    captured = capsys.readouterr()
    assert code == 0
    assert "officecli: 1.0.160" in captured.out
    assert "pandoc: 3.12.1" in captured.out

