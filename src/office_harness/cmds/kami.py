"""kami: build (fill template) / render (native weasyprint PDF) / check (gates)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from office_harness import envelope
from office_harness.cmds.common import OpError, parse_opts
from office_harness.engine import kami as kami_engine

_OPTS: dict[str, str | None] = {
    "--data": "<file>",
    "--out": "<file>",
    "--pages": None,
    "--content": "<file>",
    "--yes": None,
}


def run(g: envelope.Globals, tokens: list[str]) -> int:
    """Dispatch the kami subcommand (build | render | check)."""
    opts, positional = parse_opts(tokens, _OPTS)
    if not positional:
        raise OpError("usage", "kami requires a subcommand: build | render | check")
    sub, rest = positional[0].lower(), positional[1:]
    if sub == "build":
        return _build(g, opts, rest)
    if sub == "render":
        return _render(g, opts, rest)
    if sub == "check":
        return _check(g, opts, rest)
    raise OpError("usage", f"unknown kami subcommand: {sub} (build | render | check)")


def _build(g: envelope.Globals, opts: dict[str, Any], rest: list[str]) -> int:
    """Fill a vendored kami template with ordered placeholder values; dry-run until --yes."""
    if len(rest) != 1:
        raise OpError("usage", "kami build <template.html> --data <fills.json> [--out <f>]")
    if "--data" not in opts:
        raise OpError("usage", "kami build requires --data <fills.json>")
    tpl_dir = kami_engine.KAMI_ROOT / "templates"
    name = rest[0]
    src = Path(name) if "/" in name or "\\" in name or Path(name).is_absolute() else tpl_dir / name
    if not src.is_file():
        raise OpError("not_found", f"template not found: {src}")
    out = Path(opts.get("--out") or src.stem + ".filled.html")

    if "--yes" not in opts:
        plan = {
            "dryrun": True,
            "op": "build",
            "template": str(src),
            "data": opts["--data"],
            "would_write": str(out),
        }
        cta = {
            "description": "Suggested command:",
            "commands": [
                {"command": f"kami build {name} --data {opts['--data']} --out {out} --yes",
                 "description": "fill the template for real"}
            ],
        }
        return envelope.finish(g, plan, human=lambda d: print(f"dry-run: {d}"), cta=cta)

    spec = json.loads(Path(str(opts["--data"])).read_text(encoding="utf-8"))
    fills: dict[str, Any] = spec.get("fills", spec)
    html = src.read_text(encoding="utf-8")
    for ph, values in fills.items():
        for v in values if isinstance(values, list) else [values]:
            if ph not in html:
                raise OpError("fills_invalid", f"placeholder exhausted: {ph}")
            html = html.replace(ph, str(v), 1)
    out.write_text(html, encoding="utf-8", newline="")
    report: dict[str, Any] = {
        "dryrun": False,
        "op": "build",
        "template": str(src),
        "out": str(out),
        "placeholders_left": html.count("{{"),
    }
    return envelope.finish(g, report, human=lambda d: print(f"ok: {d['out']}"))


def _render(g: envelope.Globals, opts: dict[str, Any], rest: list[str]) -> int:
    """HTML -> PDF via native Windows weasyprint (QEMU GTK stack); --pages adds PNGs."""
    if len(rest) != 1:
        raise OpError("usage", "kami render <doc.html> [--out <f>] [--pages]")
    html = Path(rest[0])
    if not html.is_file():
        raise OpError("not_found", f"html not found: {html}")
    out = Path(opts.get("--out") or html.with_suffix(".pdf").name)

    if "--yes" not in opts:
        plan = {
            "dryrun": True,
            "op": "render",
            "html": str(html),
            "would_write": str(out),
            "pages": "--pages" in opts,
        }
        cta = {
            "description": "Suggested command:",
            "commands": [
                {"command": f"kami render {html} --out {out} --yes"
                            + (" --pages" if "--pages" in opts else ""),
                 "description": "render the PDF for real"}
            ],
        }
        return envelope.finish(g, plan, human=lambda d: print(f"dry-run: {d}"), cta=cta)

    try:
        pages = kami_engine.render_pdf(html, out)
    except OSError as e:
        raise OpError("engine_fail", f"weasyprint native render failed: {e}") from None
    report: dict[str, Any] = {
        "dryrun": False,
        "op": "render",
        "html": str(html),
        "pdf": str(out),
        "pages": pages,
    }
    if "--pages" in opts:
        imgs = kami_engine.page_images(out, out.parent / (out.stem + "-visual"))
        report["page_images"] = [str(p) for p in imgs]
    human_note = f"ok: {out} ({pages} page(s))"
    if "--pages" in opts:
        human_note += f", {len(report['page_images'])} page image(s)"
    return envelope.finish(g, report, human=lambda d: print(human_note))


def _check(g: envelope.Globals, opts: dict[str, Any], rest: list[str]) -> int:
    """Run placeholder and content-coverage gates over a filled HTML."""
    if not rest:
        raise OpError("usage", "kami check <doc.html> [--content <content.json>]")
    html_path = Path(rest[0])
    if not html_path.is_file():
        raise OpError("not_found", f"html not found: {html_path}")
    raw = html_path.read_text(encoding="utf-8")

    issues: list[str] = []
    n_placeholders = raw.count("{{")
    if n_placeholders:
        issues.append(f"unfilled placeholders: {n_placeholders}")

    checked = skipped = 0
    if "--content" in opts:
        content_path = Path(str(opts["--content"]))
        if not content_path.is_file():
            raise OpError("not_found", f"content json not found: {content_path}")
        try:
            html_visibility = kami_engine.import_kami_module("html_visibility")
            content_mod = kami_engine.import_kami_module("content")
        except ImportError as e:
            raise OpError("engine_fail", f"vendored kami scripts unavailable: {e}") from None
        text, _amb = html_visibility.visible_html_evidence(raw)
        spec = json.loads(content_path.read_text(encoding="utf-8"))
        cov_issues, checked, skipped = content_mod.coverage_issues(
            spec.get("content", spec), text)
        issues.extend(cov_issues)

    report: dict[str, Any] = {
        "op": "check",
        "html": str(html_path),
        "issues": issues,
        "checked": checked,
        "skipped": skipped,
        "ok": not issues,
    }
    if issues:
        # 业务未过(占位符/覆盖未清)按 read/search 惯例走 MISS(1):成功信封 + 退出码 1
        report["ok"] = False
        return envelope.finish(
            g, report,
            human=lambda d: print(f"NOT READY: {len(d['issues'])} issue(s): " + "; ".join(d["issues"])))
    return envelope.finish(g, report, human=lambda d: print("READY: 0 issue(s)"))
