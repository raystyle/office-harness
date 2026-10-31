"""transcribe command tests: dry-run face, model gate and fake-engine apply."""

from __future__ import annotations

import json
from pathlib import Path

from office_harness import run


def test_transcribe_dryrun_and_usage(tmp_path: Path, fake_engine, wavo_stub, capsys) -> None:
    src = tmp_path / "meeting.m4a"
    src.write_bytes(b"fake-audio")
    fake_engine.script(("wavo", "list"), (0, "NAME SIZE PATH\nwhisper-turbo 0.89 GB x\n", ""))
    code = run.main(["transcribe", str(src), "--json", "--full-output"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["data"]["dryrun"] is True
    assert payload["data"]["model_present"] is True
    assert payload["data"]["would_write"].endswith("meeting.srt")
    assert payload["meta"]["cta"]["commands"][0]["command"].endswith("--yes")
    code = run.main(["transcribe"])
    err = json.loads(capsys.readouterr().err.strip().splitlines()[-1])
    assert code == 2
    assert err["code"] == "usage"
    code = run.main(["transcribe", str(src), "--to", "vtt"])
    err = json.loads(capsys.readouterr().err.strip().splitlines()[-1])
    assert code == 2
    assert err["code"] == "unsupported_format"
    code = run.main(["transcribe", str(tmp_path / "nope.m4a")])
    err = json.loads(capsys.readouterr().err.strip().splitlines()[-1])
    assert code == 2
    assert err["code"] == "file_not_found"


def test_transcribe_missing_model_miss_with_pull_cta(
    tmp_path: Path, fake_engine, wavo_stub, capsys
) -> None:
    src = tmp_path / "m.mp3"
    src.write_bytes(b"fake-audio")
    fake_engine.script(("wavo", "list"), (0, "NAME SIZE PATH\n", ""))
    code = run.main(["transcribe", str(src), "--yes", "--json"])
    assert code == 1
    err = json.loads(capsys.readouterr().err.strip().splitlines()[-1])
    assert err["code"] == "model_not_pulled"
    assert "--pull" in err["cta"]["commands"][0]["command"]


def test_transcribe_apply_via_fake_engine(tmp_path: Path, fake_engine, wavo_stub, capsys) -> None:
    src = tmp_path / "meeting.m4a"
    src.write_bytes(b"fake-audio")
    fake_engine.script(("wavo", "list"), (0, "NAME SIZE PATH\nwhisper-turbo 0.89 GB x\n", ""))
    srt_body = "1\n00:00:01,000 --> 00:00:02,000\nhello\n"
    fake_engine.script(("wavo", "run", "whisper-turbo", str(src)), (0, srt_body, ""))
    code = run.main(["transcribe", str(src), "--yes", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["data"]["to"] == "srt"
    assert payload["data"]["bytes"] > 0
    argv = fake_engine.calls[-1]
    assert argv[1:4] == ["run", "whisper-turbo", str(src)]
    assert "--srt" in argv and "--segment" in argv and "30" in argv
    assert "-y" not in argv  # without --pull the model gate already passed
    assert Path(payload["data"]["out"]).read_text(encoding="utf-8").startswith("1\n")
