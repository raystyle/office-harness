"""transcribe: audio to srt/text/json via wavo (local GPU, whisper models)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from office_harness import envelope
from office_harness.cmds.common import MissError, OpError, parse_opts
from office_harness.engine import wavo

_OPTS: dict[str, str | None] = {
    "--model": "<m>",
    "--segment": "<secs>",
    "--to": "<fmt>",
    "--out": "<file>",
    "--pull": None,
    "--yes": None,
}

_FORMATS = ("srt", "text", "json")
_AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".flac", ".ogg"}


def run(g: envelope.Globals, tokens: list[str]) -> int:
    """Transcribe one audio file; dry-run until --yes."""
    opts, positional = parse_opts(tokens, _OPTS)
    if len(positional) != 1:
        raise OpError("usage", "transcribe takes exactly one audio path")
    src = Path(positional[0])
    if not src.exists():
        raise OpError("file_not_found", f"audio file not found: {src}")
    if src.suffix.lower() not in _AUDIO_EXTS:
        raise OpError(
            "unsupported_format",
            f"expected one of {sorted(_AUDIO_EXTS)}, got {src.suffix or 'none'}",
        )
    fmt = opts.get("--to", "srt")
    if fmt not in _FORMATS:
        raise OpError("unsupported_format", f"transcribe supports {_FORMATS}, got {fmt}")
    try:
        segment = int(opts.get("--segment", "30"))
    except ValueError:
        raise OpError("usage", "--segment expects an integer") from None
    if segment < 0:
        raise OpError("usage", "--segment must be >= 0 (0 = one pass)")
    model = opts.get("--model", "whisper-turbo")
    out = Path(opts.get("--out") or wavo.artifact_for(str(src), fmt))
    pull = "--pull" in opts

    if "--yes" not in opts:
        try:
            present = model in wavo.list_models()
        except Exception:  # noqa: BLE001 - the plan stays useful without the probe
            present = None
        plan: dict[str, Any] = {
            "dryrun": True,
            "src": str(src),
            "model": model,
            "to": fmt,
            "segment": segment,
            "model_present": present,
            "would_write": str(out),
        }
        cta = {
            "description": "Suggested command:",
            "commands": [
                {
                    "command": f"transcribe {src} --to {fmt} --yes",
                    "description": "run the transcription for real",
                }
            ],
        }
        return envelope.finish(g, plan, human=lambda d: print(f"dry-run: {d}"), cta=cta)

    if not pull and model not in wavo.list_models():
        raise MissError(
            "model_not_pulled",
            f"wavo model {model} is not in the local cache; rerun with --pull to download it",
            cta={
                "description": "Suggested command:",
                "commands": [
                    {
                        "command": f"transcribe {src} --to {fmt} --pull --yes",
                        "description": "download the missing model, then transcribe",
                    }
                ],
            },
        )

    ok, payload, _hint = wavo.transcribe(str(src), model=model, segment=segment, fmt=fmt, pull=pull)
    if not ok:
        raise OpError("transcribe_failed", f"wavo failed on {src}:\n{payload}")
    out.write_text(payload + "\n", encoding="utf-8", newline="")

    report: dict[str, Any] = {
        "dryrun": False,
        "src": str(src),
        "model": model,
        "to": fmt,
        "segment": segment,
        "out": str(out),
        "bytes": out.stat().st_size,
    }

    def human(d: dict[str, Any]) -> None:
        print(f"transcribed {d['src']} -> {d['out']} ({d['bytes']} bytes, {d['model']})")

    return envelope.finish(g, report, human=human)
