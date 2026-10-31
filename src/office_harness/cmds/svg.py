"""svg: build (svg.py) / judge (agent-svgtools) / optimise (oxvg) toolchain."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from office_harness import envelope
from office_harness.cmds.common import MissError, OpError, parse_opts
from office_harness.cmds.render import load_data
from office_harness.engine import svgeng
from office_harness.svgspec import build as spec_build

_OPTS: dict[str, str | None] = {
    "--data": "<file>",
    "--out": "<file>",
    "--ref": "<image>",
    "--diff-image": "<png>",
    "--threshold": "<n>",
    "--in-place": None,
    "--yes": None,
}


def run(g: envelope.Globals, tokens: list[str]) -> int:
    """Dispatch the svg subcommand (build | judge | optimise)."""
    opts, positional = parse_opts(tokens, _OPTS)
    if not positional:
        raise OpError("usage", "svg requires a subcommand: build | judge | optimise")
    sub, rest = positional[0].lower(), positional[1:]
    if sub == "build":
        return _build(g, opts, rest)
    if sub == "judge":
        return _judge(g, opts, rest)
    if sub == "optimise":
        return _optimise(g, opts, rest)
    raise OpError("usage", f"unknown svg subcommand: {sub} (build | judge | optimise)")


def _build(g: envelope.Globals, opts: dict[str, Any], rest: list[str]) -> int:
    """Structured json/yaml spec -> svg file; dry-run until --yes."""
    if rest:
        raise OpError("usage", "svg build takes options only (--data required)")
    if "--data" not in opts:
        raise OpError("usage", "svg build requires --data <spec.json>")
    data_path = opts["--data"]
    spec = load_data(data_path)
    src_stem = Path(str(data_path)).with_suffix(".svg")
    out = Path(opts.get("--out") or src_stem)

    if "--yes" not in opts:
        plan = {
            "dryrun": True,
            "op": "build",
            "data": str(data_path),
            "would_write": str(out),
        }
        cta = {
            "description": "Suggested command:",
            "commands": [
                {"command": f"svg build --data {data_path} --out {out} --yes",
                 "description": "render the svg for real"}
            ],
        }
        return envelope.finish(g, plan, human=lambda d: print(f"dry-run: {d}"), cta=cta)

    try:
        payload = spec_build(spec)
    except ValueError as e:
        raise OpError("spec_invalid", str(e)) from None
    out.write_text(payload + "\n", encoding="utf-8", newline="")
    report: dict[str, Any] = {
        "dryrun": False,
        "op": "build",
        "data": str(data_path),
        "out": str(out),
        "bytes": out.stat().st_size,
    }

    def human(d: dict[str, Any]) -> None:
        print(f"built {d['out']} ({d['bytes']} bytes)")

    return envelope.finish(g, report, human=human)


def _judge(g: envelope.Globals, opts: dict[str, Any], rest: list[str]) -> int:
    """Score a candidate svg against a reference raster (ro)."""
    if len(rest) != 1:
        raise OpError("usage", "svg judge takes exactly one candidate svg path")
    candidate = rest[0]
    if not Path(candidate).exists():
        raise OpError("file_not_found", f"candidate svg not found: {candidate}")
    if "--ref" not in opts:
        raise OpError("usage", "svg judge requires --ref <reference raster>")
    reference = opts["--ref"]
    if not Path(reference).exists():
        raise OpError("file_not_found", f"reference image not found: {reference}")
    try:
        threshold = int(opts.get("--threshold", "0"))
    except ValueError:
        raise OpError("usage", "--threshold expects an integer") from None
    diff_image = opts.get("--diff-image")

    result = svgeng.judge(reference, candidate, diff_image=diff_image, threshold=threshold)
    score = result.get("combined") if isinstance(result.get("combined"), (int, float)) else None
    report: dict[str, Any] = {"op": "judge", "ref": reference, "candidate": candidate, "result": result}

    def human(d: dict[str, Any]) -> None:
        r = d["result"]
        print(f"judged {d['candidate']} vs {d['ref']}")
        for key, value in r.items():
            if not isinstance(value, (list, dict)):
                print(f"  {key}: {value}")

    if threshold > 0 and (score is None or score < threshold):
        raise MissError(
            "below_threshold",
            f"combined score {score} is below threshold {threshold}",
            cta={
                "description": "Next steps:",
                "commands": [
                    {"command": f"svg judge --ref {reference} {candidate} --diff-image diff.png",
                     "description": "see the error regions heatmap"}
                ],
            },
        )
    return envelope.finish(g, report, human=human)


def _optimise(g: envelope.Globals, opts: dict[str, Any], rest: list[str]) -> int:
    """Compress an svg via oxvg; dry-run until --yes (in-place or --out)."""
    if len(rest) != 1:
        raise OpError("usage", "svg optimise takes exactly one svg path")
    src = Path(rest[0])
    if not src.exists():
        raise OpError("file_not_found", f"svg file not found: {src}")
    in_place = "--in-place" in opts
    out = Path(opts["--out"]) if opts.get("--out") else (src if in_place else src.with_suffix(".min.svg"))
    if opts.get("--out") and in_place:
        raise OpError("usage", "pick either --out <file> or --in-place, not both")

    if "--yes" not in opts:
        plan = {
            "dryrun": True,
            "op": "optimise",
            "src": str(src),
            "would_write": str(out),
            "in_place": in_place,
        }
        cta = {
            "description": "Suggested command:",
            "commands": [
                {"command": f"svg optimise {src} --out {out} --yes",
                 "description": "run oxvg optimise for real"}
            ],
        }
        return envelope.finish(g, plan, human=lambda d: print(f"dry-run: {d}"), cta=cta)

    before = src.stat().st_size
    ok, payload = svgeng.optimise(str(src))
    if not ok:
        raise OpError("optimise_failed", f"oxvg failed on {src}:\n{payload}")
    out.write_text(payload + "\n", encoding="utf-8", newline="")
    after = out.stat().st_size
    report: dict[str, Any] = {
        "dryrun": False,
        "op": "optimise",
        "src": str(src),
        "out": str(out),
        "bytes_before": before,
        "bytes_after": after,
        "saved_pct": round((1 - after / before) * 100, 1) if before else 0.0,
    }

    def human(d: dict[str, Any]) -> None:
        print(
            f"optimised {d['src']} -> {d['out']}"
            f" ({d['bytes_before']} -> {d['bytes_after']} bytes, -{d['saved_pct']}%)"
        )

    return envelope.finish(g, report, human=human)
