"""Wire-protocol matrix: stdout shape judges, never the exit code."""

from __future__ import annotations

import pytest

from office_harness.engine import base
from office_harness.engine.base import OpError, run_enveloped


def test_non_json_stdout_fails_even_with_exit_zero(fake_engine) -> None:
    fake_engine.script(("officecli", "get"), (0, "plain text garbage\n", ""))
    with pytest.raises(OpError) as ei:
        run_enveloped(base.Path("officecli"), ["get", "f", "/"])
    assert ei.value.code == "engine_protocol"


def test_multiline_json_fails(fake_engine) -> None:
    fake_engine.script(("officecli", "get"), (0, '{"ok": true}\n{"ok": true}\n', ""))
    with pytest.raises(OpError):
        run_enveloped(base.Path("officecli"), ["get", "f", "/"])


def test_missing_ok_key_fails(fake_engine) -> None:
    fake_engine.script(("officecli", "get"), (0, '{"data": 1}', ""))
    with pytest.raises(OpError):
        run_enveloped(base.Path("officecli"), ["get", "f", "/"])


def test_ok_false_with_exit_zero_is_returned(fake_engine) -> None:
    fake_engine.script(("officecli", "get"), (0, '{"ok": false, "error": {"code": "not_found"}}', ""))
    payload = run_enveloped(base.Path("officecli"), ["get", "f", "/"])
    assert payload["ok"] is False


def test_ok_true_with_nonzero_exit_is_success(fake_engine) -> None:
    fake_engine.script(("reader", "search"), (1, '{"ok": true, "data": {"hits": []}}', ""))
    payload = run_enveloped(base.Path("reader"), ["search", "f", "x"])
    assert payload["ok"] is True
