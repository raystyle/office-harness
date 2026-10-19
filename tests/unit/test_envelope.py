"""Envelope contract tests: exit codes, stdout/stderr split, filter paths."""

from __future__ import annotations

import json

from office_harness import envelope


def test_finish_json_envelope(capsys: object) -> None:
    g = envelope.Globals(json_mode=True)
    code = envelope.finish(g, {"x": 1})
    out = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert code == 0
    assert out == {"ok": True, "data": {"x": 1}}


def test_finish_full_output_meta(capsys: object) -> None:
    g = envelope.Globals(json_mode=True, full=True, command="doctor")
    code = envelope.finish(g, {"x": 1}, cta={"description": "d", "commands": []})
    out = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert code == 0
    assert out["meta"]["command"] == "office-harness doctor"
    assert out["meta"]["duration_ms"] >= 0
    assert out["meta"]["cta"] == {"description": "d", "commands": []}


def test_filter_single_path() -> None:
    assert envelope.filter_data({"a": {"b": 7}}, "a.b") == 7


def test_filter_multi_and_indices() -> None:
    data = {"items": [10, 20, 30], "n": 5}
    assert envelope.filter_data(data, "items[1]") == 20
    assert envelope.filter_data(data, "items[0,2]") == [10, 30]
    assert envelope.filter_data(data, "items[0],n") == [10, 5]


def test_filter_unknown_path_raises() -> None:
    try:
        envelope.filter_data({"a": 1}, "zzz")
    except KeyError:
        pass
    else:
        raise AssertionError("expected KeyError")


def test_json_format_conflict_detected() -> None:
    g, rest = envelope._split_global_flags(["--json", "--format", "json"])
    assert g.format_conflict is True
    assert rest == []


def test_stderr_error_single_line(capsys: object) -> None:
    e = envelope.StderrError(code="usage", message="bad flag", retryable=True)
    code = envelope.emit_error(e, envelope.EXIT_USAGE)
    err = capsys.readouterr().err  # type: ignore[attr-defined]
    lines = [ln for ln in err.splitlines() if ln.strip()]
    assert code == 2
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["code"] == "usage"
    assert payload["retryable"] is True
