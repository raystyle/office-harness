"""run.py: thin dispatcher — faces first, then per-command dispatch.

Command bodies live in cmds/*; this file only routes. Windows hardening: stdout
and stderr are reconfigured to UTF-8 before any import side effects so cp936
consoles never UnicodeEncodeError on Chinese output.
"""

from __future__ import annotations

import sys


def _force_utf8() -> None:
    """Reconfigure stdio to UTF-8 before imports; cp936 consoles stay safe."""
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name)
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass


_force_utf8()


from office_harness import cli, envelope
from office_harness.cmds import common as cmdcommon
from office_harness.cmds import compile as cmdcompile
from office_harness.cmds import doctor as cmddoctor
from office_harness.cmds import fill as cmdfill
from office_harness.cmds import inspect as cmdinspect
from office_harness.cmds import read as cmdread
from office_harness.cmds import recalc as cmdrecalc
from office_harness.cmds import render as cmdrender
from office_harness.envelope import EXIT_MISS, EXIT_OK, EXIT_USAGE, UsageError


def _face_or_dispatch(argv: list[str]) -> int:
    g, rest = envelope._split_global_flags(argv)
    if g.format_conflict:
        raise UsageError("--json and --format json are mutually exclusive; pick one")
    if g.filter_spec is not None and not g.json_mode:
        # filter implies machine mode
        g.json_mode = True

    # --llms / --schema / --help faces (command-scoped when a token names one)
    scope = rest[0] if rest and rest[0] in cli.COMMANDS else None
    if _flag(argv, "--llms"):
        if _flag(argv, "--json") or g.json_mode:
            envelope.print_json(cli.render_llms_json())
        else:
            sys.stdout.write(cli.render_llms() + "\n")
        return EXIT_OK
    if _flag(argv, "--schema"):
        try:
            envelope.print_json(cli.render_schema(scope))
        except KeyError:
            raise UsageError(f"unknown command for --schema: {scope}") from None
        return EXIT_OK
    if _flag(argv, "--help") or _flag(argv, "-h"):
        sys.stdout.write(cli.render_help(scope) + "\n")
        return EXIT_OK

    # bare invocation: navigation event, not an error
    if not rest:
        sys.stdout.write(cli.render_bare() + "\n")
        return EXIT_OK

    if rest and rest[0] == "--version":
        sys.stdout.write(cli.version() + "\n")
        return EXIT_OK

    g.command = rest[0]
    handler = _DISPATCH.get(rest[0])
    if handler is None:
        raise UsageError(f"unknown command: {rest[0]}")
    return handler(g, rest[1:])


def _flag(argv: list[str], flag: str) -> bool:
    return flag in argv


_DISPATCH = {
    "render": cmdrender.run,
    "compile": cmdcompile.run,
    "fill": cmdfill.run,
    "read": cmdread.run,
    "recalc": cmdrecalc.run,
    "inspect": cmdinspect.run,
    "doctor": cmddoctor.run,
}


def main(argv: list[str] | None = None) -> int:
    """CLI entry: faces first, then dispatch; returns the process exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        return _face_or_dispatch(args)
    except UsageError as e:
        return envelope.emit_error(envelope.StderrError(code="usage", message=str(e)), EXIT_USAGE)
    except ValueError as e:  # parse_opts / doctor arg refusals map to usage
        return envelope.emit_error(envelope.StderrError(code="usage", message=str(e)), EXIT_USAGE)
    except cmdcommon.MissError as e:
        return envelope.emit_error(
            envelope.StderrError(code=e.code, message=str(e), cta=e.cta), EXIT_MISS
        )
    except cmdcommon.OpError as e:
        return envelope.emit_error(
            envelope.StderrError(code=e.code, message=str(e), retryable=e.retryable, cta=e.cta),
            EXIT_USAGE,
        )


if __name__ == "__main__":
    raise SystemExit(main())
