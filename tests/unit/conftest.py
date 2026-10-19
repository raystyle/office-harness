"""FakeEngine test seam + shared fixtures; no test touches a real engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import office_harness.engine.base as base


class FakeExecute:
    """Monkeypatch target for base._execute: replays canned (code, stdout, stderr)."""

    def __init__(self) -> None:
        self.canned: dict[str, tuple[int, str, str]] = {}
        self.calls: list[list[str]] = []

    def script(self, argv_prefix: tuple[str, ...], payload: tuple[int, str, str]) -> None:
        self.canned[argv_prefix] = payload

    def __call__(self, argv: list[str], timeout: int) -> tuple[int, str, str]:
        self.calls.append(list(argv))
        # normalize: the real discovery ladder yields absolute paths with
        # .exe suffixes; match on the stem of argv[0] plus the following args
        stem = Path(argv[0]).stem if argv else ""
        key = (stem, *argv[1:])
        for prefix, payload in self.canned.items():
            if key[: len(prefix)] == tuple(prefix):
                return payload
        raise AssertionError(f"unexpected engine call: {argv}")


@pytest.fixture()
def fake_engine(monkeypatch: pytest.MonkeyPatch) -> FakeExecute:
    fx = FakeExecute()
    monkeypatch.setattr(base, "_execute", fx)
    return fx


def envelope_ok(data: Any = None) -> str:
    import json

    return json.dumps({"ok": True, "data": data if data is not None else {}}, ensure_ascii=False)
