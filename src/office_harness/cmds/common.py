"""Command-layer shared pieces: option parsing, typed errors, pydantic glue.

Command modules stay thin (IO orchestration and gates only); everything here is
pure and unit-testable. Exit semantics: MissError -> 1, OpError -> 2.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError


class MissError(Exception):
    """Business miss (no hit / not found): exit 1, never a crash."""

    def __init__(self, code: str, message: str, cta: dict[str, Any] | None = None):
        """Carry a typed code plus an optional CTA block."""
        super().__init__(message)
        self.code = code
        self.cta = cta


class OpError(Exception):
    """Engine or system failure: exit 2, retryable only for timeout family."""

    def __init__(
        self, code: str, message: str, retryable: bool = False, cta: dict[str, Any] | None = None
    ):
        """Carry a typed code, retryability and an optional CTA block."""
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.cta = cta


def parse_opts(tokens: list[str], flags: dict[str, str | None]) -> tuple[dict[str, Any], list[str]]:
    """Split tokens into (options, positionals).

    ``flags`` maps allowed option names to their value placeholder (None =
    boolean). Unknown options raise ValueError (usage, exit 2). Non-flag
    tokens pass through as positionals in order. Repeating a value option
    collects into a list (used by --search-path).
    """
    out: dict[str, Any] = {}
    positional: list[str] = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if not t.startswith("--"):
            positional.append(t)
            i += 1
            continue
        key, _, inline = t.partition("=")
        if key not in flags:
            raise ValueError(f"unknown option: {key}")
        wants_value = flags[key] is not None
        if wants_value:
            if inline:
                val: Any = inline
            else:
                if i + 1 >= len(tokens):
                    raise ValueError(f"{key} requires a value")
                i += 1
                val = tokens[i]
            if key in out:
                if not isinstance(out[key], list):
                    out[key] = [out[key]]
                out[key].append(val)
            else:
                out[key] = val
        else:
            if inline:
                raise ValueError(f"{key} is a boolean flag, no value expected")
            out[key] = True
        i += 1
    return out, positional


def pydantic_msg(e: ValidationError) -> str:
    """Compress a pydantic error list to one line for the stderr channel."""
    parts = []
    for err in e.errors():
        loc = ".".join(str(x) for x in err["loc"])
        parts.append(f"{loc}: {err['msg']}")
    return "; ".join(parts)
