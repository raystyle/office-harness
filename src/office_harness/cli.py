"""cli.py: the COMMANDS registry and the four outward faces.

The registry is the single outward source of truth. ``--help``, ``--llms``
and ``--schema`` are all projections of COMMANDS; nothing here is hand-synced
with anything else. Drift is locked by tests/unit/test_cli.py (tree walk,
line budget, version injection).

Do not hand-maintain any face: add/edit a Command entry and every face moves.
"""

from __future__ import annotations

import importlib.metadata
from dataclasses import dataclass
from typing import Any

from office_harness import __version__

CLI_NAME = "office-harness"

_ENV_VARS: dict[str, str] = {
    "OFFICE_HARNESS_TIMEOUT": "override every engine op timeout (seconds)",
    "OFFICECLI_BIN": "officecli binary override (discovery ladder: env -> PATH -> ohmyenv)",
    "READER_BIN": "reader binary override (same ladder)",
    "TECTONIC_BIN": "tectonic binary override (same ladder)",
}


@dataclass(frozen=True)
class Opt:
    """One per-command option as shown on the help and schema faces."""

    flag: str
    val: str | None  # None = boolean flag; else the value placeholder
    desc: str
    enum: tuple[str, ...] = ()
    default: str | None = None

    def spec(self) -> dict[str, Any]:
        """Schema-face projection of one option (flag, value, enum, default)."""
        d: dict[str, Any] = {"flag": self.flag, "description": self.desc}
        if self.val is not None:
            d["value"] = self.val
        else:
            d["boolean"] = True
        if self.enum:
            d["enum"] = list(self.enum)
        if self.default is not None:
            d["default"] = self.default
        return d


@dataclass(frozen=True)
class Command:
    """One registry leaf; kind group|leaf decides the help shape."""

    name: str
    kind: str  # "leaf" | "group"
    summary: str
    usage: str = ""
    args: tuple[dict[str, Any], ...] = ()
    options: tuple[Opt, ...] = ()
    examples: tuple[tuple[str, str], ...] = ()
    hints: tuple[str, ...] = ()  # ro | idem | destr | dryrun

    def opt(self, flag: str) -> Opt | None:
        """Return the option registered under ``flag``, if any."""
        for o in self.options:
            if o.flag == flag:
                return o
        return None


def _leaf(name: str, summary: str, **kw: Any) -> tuple[str, Command]:
    return name, Command(name=name, kind="leaf", summary=summary, **kw)


OPT_YES = Opt("--yes", None, "apply for real (default is a dry-run report)")
OPT_OUT = Opt("--out", "<file>", "output path (default: derived from data/template name)")
OPT_JSON_DATA = Opt("--data", "<file>", "json/yaml data file")


def _registry() -> dict[str, Command]:
    c: dict[str, Command] = {}
    c.update(
        [
            _leaf(
                "render",
                "Render a .tex.j2 template with data via the LaTeX-safe jinja environment",
                usage="render <template.tex.j2> --data <file> [--out <file>]",
                args=({"name": "template", "required": True, "desc": ".tex.j2 template path"},),
                options=(OPT_JSON_DATA, OPT_OUT),
                examples=(
                    ("render report.tex.j2 --data week.json", "render report.tex from week.json data"),
                ),
                hints=("ro",),
            ),
            _leaf(
                "compile",
                "Compile .tex to PDF with tectonic",
                usage="compile <file.tex> [--out <dir>] [--search-path <dir>]...",
                args=({"name": "file", "required": True, "desc": ".tex source path"},),
                options=(
                    Opt("--out", "<dir>", "output directory (default: alongside the source)"),
                    Opt("--search-path", "<dir>", "extra package search dir (repeatable)"),
                ),
                examples=(
                    ("compile report.tex", "PDF next to the source"),
                ),
                hints=("idem",),
            ),
            _leaf(
                "fill",
                "Fill a docx/pptx/xlsx template with data (dispatch by extension)",
                usage="fill <template> --data <file> [--out <file>] [--yes]",
                args=({"name": "template", "required": True, "desc": ".docx/.pptx/.xlsx template path"},),
                options=(OPT_JSON_DATA, OPT_OUT, OPT_YES),
                examples=(
                    ("fill report.docx --data week.json --yes", "docxtpl fill, writes report-out"),
                ),
                hints=("dryrun",),
            ),
            _leaf(
                "read",
                "Extract / search / structurally query a document via reader",
                usage="read <file> [--mode extract|search|query] [--term <t>] [--expr <mq>]",
                args=({"name": "file", "required": True, "desc": "document path (pdf/office family)"},),
                options=(
                    Opt(
                        "--mode",
                        "<m>",
                        "reader mode",
                        enum=("extract", "search", "query"),
                        default="extract",
                    ),
                    Opt("--term", "<t>", "search term (mode=search)"),
                    Opt("--expr", "<e>", "mq expression (mode=query)"),
                ),
                examples=(
                    ("read report.pdf --mode search --term 结论", "exit 0 on hit, 1 on miss"),
                ),
                hints=("ro",),
            ),
            _leaf(
                "inspect",
                "Inspect an office document via officecli (get/query/view html)",
                usage="inspect <file> [--what get|query|view] [--path <p>] [--selector <s>]",
                args=({"name": "file", "required": True, "desc": ".docx/.xlsx/.pptx path"},),
                options=(
                    Opt("--what", "<w>", "inspection face", enum=("get", "query", "view"), default="view"),
                    Opt("--path", "<p>", "element path for get (e.g. /body/p[1])"),
                    Opt("--selector", "<s>", "css-like selector for query"),
                ),
                examples=(
                    ("inspect deck.pptx --what view", "rendered html snapshot"),
                ),
                hints=("ro",),
            ),
            _leaf(
                "doctor",
                "Self-check engines (officecli/reader/tectonic) and libraries",
                usage="doctor",
                options=(),
                examples=(
                    ("office-harness doctor", "versions, discovery, cache state"),
                ),
                hints=("ro", "idem"),
            ),
        ]
    )
    return c


COMMANDS: dict[str, Command] = _registry()

_HINT_TAG = {"ro": "ro", "idem": "idem", "destr": "destr", "dryrun": "dryrun"}


def version() -> str:
    """Distribution version from importlib.metadata, __version__ as fallback."""
    try:
        return importlib.metadata.version("office-harness")
    except importlib.metadata.PackageNotFoundError:
        return __version__


def _hint_tags(c: Command) -> str:
    return " ".join(_HINT_TAG[h] for h in c.hints if h in _HINT_TAG)


def render_bare() -> str:
    """Two-line compact face for argument-less invocation (exit 0, no error)."""
    return (
        f"{CLI_NAME}: document pipeline harness (tex/docx/pptx/xlsx over officecli/reader/tectonic).\n"
        f"命令清单: {CLI_NAME} --llms;详情: {CLI_NAME} --help"
    )


def render_help(command: str | None = None) -> str:
    """Human help face; leaf section order per dev-cli AF:64-74."""
    head = f"{CLI_NAME}@{version()} — document pipeline CLI harness"
    if command is None:
        lines = [head, "", "Usage:", f"  {CLI_NAME} <command> [options]", "", "Commands:"]
        w = max(len(n) for n in COMMANDS)
        for n, c in COMMANDS.items():
            tag = f" [{_hint_tags(c)}]" if c.hints else ""
            lines.append(f"  {n.ljust(w)}  {c.summary}{tag}")
        lines += ["", "Global Options:"]
        lines += _global_opts_lines()
        lines += ["", "Examples:"]
        lines += [f"  {ex}  # {d}" for ex, d in _global_examples()]
        return "\n".join(lines)
    c = COMMANDS.get(command)
    if c is None:
        raise KeyError(command)
    lines = [head, "", "Usage:", f"  {CLI_NAME} {c.usage}"]
    if c.args:
        lines += ["", "Arguments:"]
        for a in c.args:
            req = "required" if a.get("required") else "optional"
            lines.append(f"  <{a['name']}>  {a.get('desc', '')} ({req})")
    if c.options:
        lines += ["", "Options:"]
        for o in c.options:
            val = f" {o.val}" if o.val else ""
            enum = f" ({'|'.join(o.enum)})" if o.enum else ""
            dflt = f" (default: {o.default})" if o.default else ""
            lines.append(f"  {o.flag}{val}{enum}{dflt}  {o.desc}")
    if c.examples:
        lines += ["", "Examples:"]
        lines += [f"  {CLI_NAME} {ex}  # {d}" for ex, d in c.examples]
    lines += ["", "Global Options:"]
    lines += _global_opts_lines()
    lines += ["", "Environment Variables:"]
    lines += _env_lines()
    return "\n".join(lines)


def _global_opts_lines() -> list[str]:
    return [
        "  --filter-output <keys>   key-path filter, envelope-rooted (a.b,items[0,2])",
        "  --format <toon|json|yaml|md>  output family (toon default; json = machine envelope)",
        "  --full-output            full envelope incl. meta {command, duration_ms, cta}",
        "  --help, -h               show help (this face)",
        "  --llms                   agent-facing compact manual",
        "  --json                   output as JSON (AI-friendly)",
        "  --schema                 this command's JSON Schema",
    ]


def _env_lines() -> list[str]:
    return [f"  {k}  {v}" for k, v in _ENV_VARS.items()]


def _global_examples() -> tuple[tuple[str, str], ...]:
    c = COMMANDS.get("doctor")
    if c and c.examples:
        return c.examples
    return (("", ""),)


def render_llms() -> str:
    """Agent-facing compact manual, <=120 lines, projected from COMMANDS."""
    lines = [
        f"# {CLI_NAME}",
        "",
        f"> {CLI_NAME}: document pipeline harness — jinja 模板 x docxtpl/python-pptx/openpyxl,"
        f" 编排 officecli/reader/tectonic。版本 {version()}。手册由命令树渲染,勿手改。",
        "",
        "## 读序",
        "",
        "先 `--schema <command>` 看参数与输出契约;本手册看全景;细节 `--help <command>`。",
        "",
        "## 命令",
        "",
    ]
    for c in COMMANDS.values():
        tag = f" [{_hint_tags(c)}]" if c.hints else ""
        lines.append(f"### {c.name}{tag}")
        lines.append(c.summary)
        if c.usage:
            lines.append(f"  用法: {CLI_NAME} {c.usage}")
        for o in c.options:
            val = f" {o.val}" if o.val else ""
            lines.append(f"  {o.flag}{val} — {o.desc}")
        lines.append("")
    lines += [
        "## 退出码",
        "",
        "| code | meaning |",
        "|---|---|",
        "| 0 | success |",
        "| 1 | business miss (no hit / not found) |",
        "| 2 | usage or system error |",
        "",
        "## 输出契约",
        "",
        "- stdout JSON envelope {ok, data | error, meta?};meta carries {command, duration_ms, cta}",
        "- stderr single-line JSON {code, message, retryable?, cta?}; stdout stays pure",
        "- typed CTA rides both success (meta.cta) and failure (stderr cta)",
        "- writes dry-run until --yes; success exit does not imply executed",
        "- cut on purpose: --format yaml|md, --mcp, token pagination, --llms-full",
        "",
        "## 示例",
        "",
    ]
    shown = 0
    for c in COMMANDS.values():
        for ex, _desc in c.examples:
            if shown >= 5:
                break
            lines.append("```bash")
            lines.append(f"{CLI_NAME} {ex}")
            lines.append("```")
            shown += 1
    return "\n".join(lines)


def render_llms_json() -> dict[str, Any]:
    """Machine form of the manual with a manifest version string."""
    return {
        "manifest": f"{CLI_NAME}@{version()}",
        "commands": [
            {
                "name": c.name,
                "summary": c.summary,
                "usage": c.usage,
                "hints": list(c.hints),
                "options": [o.spec() for o in c.options],
            }
            for c in COMMANDS.values()
        ],
        "exit_codes": {"0": "success", "1": "business miss", "2": "usage or system error"},
    }


def render_schema(command: str | None = None) -> dict[str, Any]:
    """Three-face JSON Schema (args/options/output contract) for one command."""
    if command is None:
        return {
            "name": CLI_NAME,
            "version": version(),
            "commands": [
                {"name": c.name, "kind": c.kind, "summary": c.summary} for c in COMMANDS.values()
            ],
        }
    c = COMMANDS.get(command)
    if c is None:
        raise KeyError(command)
    return {
        "name": CLI_NAME,
        "version": version(),
        "command": command,
        "arguments": [
            {"name": a["name"], "required": bool(a.get("required")), "description": a.get("desc", "")}
            for a in c.args
        ],
        "options": [o.spec() for o in c.options],
        "output": {
            "envelope": "{ok, data | error, meta?}",
            "exit_codes": {"0": "success", "1": "business miss", "2": "usage or system error"},
        },
    }


def format_cta(description: str, commands: list[dict[str, Any]]) -> dict[str, Any]:
    """Typed CTA block shared by meta.cta and the human face."""
    folded: list[dict[str, Any]] = []
    for item in commands:
        if isinstance(item, str):
            folded.append({"command": f"{CLI_NAME} {item}"})
            continue
        parts = [CLI_NAME, str(item.get("command", ""))]
        args = item.get("args", {})
        if isinstance(args, dict):
            for k, v in args.items():
                parts.append(str(k) if v is True else f"{k}={v}")
        opts = item.get("options", {})
        if isinstance(opts, dict):
            for k, v in opts.items():
                parts.append(f"--{k}" if v is True else f"--{k} {v}")
        entry: dict[str, Any] = {"command": " ".join(p for p in parts if p)}
        if item.get("description"):
            entry["description"] = item["description"]
        folded.append(entry)
    return {"description": description, "commands": folded}


def render_cta(cta: dict[str, Any]) -> str:
    """Human render from the same CTA block (dev-cli: same-source two faces)."""
    out = [cta.get("description", "Suggested commands:")]
    for c in cta.get("commands", []):
        line = f"  {c['command']}"
        if c.get("description"):
            line += f" - {c['description']}"
        out.append(line)
    return "\n".join(out)
