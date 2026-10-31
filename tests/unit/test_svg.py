"""svg command tests: spec build, judge threshold gate, optimise via fakes."""

from __future__ import annotations

import json
from pathlib import Path

from office_harness import run

_SPEC = {
    "width": 40,
    "height": 20,
    "viewBox": [0, 0, 40, 20],
    "children": [
        {"el": "Rect", "x": 0, "y": 0, "width": 40, "height": 20, "fill": "#eee"},
        {"el": "Text", "x": 4, "y": 14, "text": "hi"},
    ],
}


def test_svg_build_dryrun_and_apply(tmp_path: Path, capsys) -> None:
    data = tmp_path / "d.json"
    data.write_text(json.dumps(_SPEC), encoding="utf-8")
    code = run.main(["svg", "build", "--data", str(data), "--json", "--full-output"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["data"]["dryrun"] is True
    assert payload["data"]["would_write"].endswith("d.svg")
    code = run.main(["svg", "build", "--data", str(data), "--yes", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    body = Path(payload["data"]["out"]).read_text(encoding="utf-8")
    assert body.startswith("<svg") and "hi" in body


def test_svg_build_rejects_unknown_tag(tmp_path: Path, capsys) -> None:
    data = tmp_path / "bad.json"
    data.write_text(json.dumps({"children": [{"el": "Circl", "cx": 1}]}), encoding="utf-8")
    code = run.main(["svg", "build", "--data", str(data), "--yes"])
    err = json.loads(capsys.readouterr().err.strip().splitlines()[-1])
    assert code == 2
    assert err["code"] == "spec_invalid"
    assert "Circle" in err["message"]  # closest-match hint


def test_svg_judge_threshold_miss(fake_engine, svgtools_stub, tmp_path: Path, capsys) -> None:
    cand = tmp_path / "c.svg"
    cand.write_text("<svg xmlns='x'><rect width='1' height='1'/></svg>", encoding="utf-8")
    ref = tmp_path / "r.png"
    ref.write_bytes(b"png")
    fake_engine.script(
        ("agent-svgtools", "judge"),
        (0, json.dumps({"combined": 41.5, "pixel_match": 40.0, "ssim": 43.0}), ""),
    )
    code = run.main(["svg", "judge", "--ref", str(ref), str(cand), "--threshold", "80", "--json"])
    assert code == 1
    err = json.loads(capsys.readouterr().err.strip().splitlines()[-1])
    assert err["code"] == "below_threshold"
    assert "41.5" in err["message"]


def test_svg_judge_pass(fake_engine, svgtools_stub, tmp_path: Path, capsys) -> None:
    cand = tmp_path / "c.svg"
    cand.write_text("<svg xmlns='x'/>", encoding="utf-8")
    ref = tmp_path / "r.png"
    ref.write_bytes(b"png")
    fake_engine.script(
        ("agent-svgtools", "judge"),
        (0, json.dumps({"combined": 92.0, "pixel_match": 91.0, "ssim": 93.0}), ""),
    )
    code = run.main(["svg", "judge", "--ref", str(ref), str(cand), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["data"]["result"]["combined"] == 92.0
    argv = fake_engine.calls[-1]
    assert "--threshold" not in argv  # threshold 0 is not forwarded


def test_svg_optimise_apply(fake_engine, oxvg_stub, tmp_path: Path, capsys) -> None:
    src = tmp_path / "s.svg"
    src.write_text("<svg xmlns='x' width='10'></svg>", encoding="utf-8")
    fake_engine.script(("oxvg", "optimise"), (0, "<svg xmlns='x' width='10'/>", ""))
    code = run.main(["svg", "optimise", str(src), "--out", str(tmp_path / "s.min.svg"), "--yes", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["data"]["bytes_after"] <= payload["data"]["bytes_before"]
    assert (tmp_path / "s.min.svg").exists()
