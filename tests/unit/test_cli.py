"""Drift guards: registry <-> dispatch <-> manual <-> schema, four-way locked."""

from __future__ import annotations

import json

import pytest

from office_harness import cli, run


def test_llms_line_budget() -> None:
    text = cli.render_llms()
    assert len(text.splitlines()) <= 120, "manual exceeded the 120-line budget"


def test_every_command_in_llms() -> None:
    text = cli.render_llms()
    for name in cli.COMMANDS:
        assert f"### {name}" in text, f"command {name} missing from --llms"


def test_every_long_option_in_llms() -> None:
    text = cli.render_llms()
    for cmd in cli.COMMANDS.values():
        for opt in cmd.options:
            assert opt.flag in text, f"{cmd.name}: {opt.flag} missing from --llms"


def test_registry_dispatch_agreement() -> None:
    dispatched = set(run._DISPATCH)
    for name in cli.COMMANDS:
        assert name in dispatched, f"{name} registered but has no dispatch branch"
    for name in dispatched:
        assert name in cli.COMMANDS, f"dispatch {name} not registered"


def test_version_single_source() -> None:
    head = cli.render_help()
    v = cli.version()
    assert f"{cli.CLI_NAME}@{v}" in head
    assert v in cli.render_llms()
    assert cli.render_llms_json()["manifest"].endswith(v)


def test_llms_json_shape() -> None:
    payload = cli.render_llms_json()
    assert payload["manifest"].startswith("office-harness@")
    assert {c["name"] for c in payload["commands"]} == set(cli.COMMANDS)


def test_schema_covers_options() -> None:
    for name, cmd in cli.COMMANDS.items():
        schema = cli.render_schema(name)
        flags = [o["flag"] for o in schema["options"]]
        assert flags == [o.flag for o in cmd.options]


def test_bare_face_exit_zero(capsys: pytest.CaptureFixture[str]) -> None:
    code = run.main([])
    out = capsys.readouterr().out
    assert code == 0
    assert "--llms" in out


def test_unknown_command_is_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    code = run.main(["frobnicate"])
    err = capsys.readouterr().err
    assert code == 2
    payload = json.loads(err.strip().splitlines()[-1])
    assert payload["code"] == "usage"
