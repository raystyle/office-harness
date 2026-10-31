r"""Kami engine client: native Windows weasyprint rendering over vendored assets.

Design notes (per AGENTS.md \"engine calls only via engine/ clients\"):

- No external binary to discover: the render kernel is the python dependency
  weasyprint (pango stack). On Windows the pango native libraries come from
  the GTK runtime that ships with QEMU (``C:\Program Files\qemu``); bootstrap
  order: env ``KAMI_GTK_BIN`` override, then the QEMU default. DLLs are
  injected via ``os.add_dll_directory``.
- ``fonts.conf`` is rendered from ``assets/kami/fonts.conf`` (pointing at the
  Windows fonts dir) so fontconfig never complains about a missing default
  config.
- The vendored kami validation/deliver scripts under ``assets/kami/scripts``
  are reused as libraries (sys.path injection), never spawned as subprocesses.
  The entry here does the three things the harness needs: render, page
  images, structural checks; the full deliver gate stays in cmd land.
"""

from __future__ import annotations

import atexit
import os
import sys
from importlib import import_module
from pathlib import Path
from typing import Any

KAMI_ROOT = Path(__file__).resolve().parents[3] / "assets" / "kami"
GTK_BIN_ENV = "KAMI_GTK_BIN"
_DEFAULT_GTK_CANDIDATES = [
    r"C:\Program Files\qemu",
    r"C:\GTK3-Runtime\bin",
]

_EXIT_GUARD_INSTALLED = False


def _install_exit_noise_guard() -> None:
    """Mute C-level finalizer stderr noise (fontconfig) at process exit.

    The QEMU-bundled fontconfig re-reads its compiled-in default config during
    C atexit (after Python handlers, before CRT exit) and prints 3 error lines
    regardless of FONTCONFIG_FILE. Redirecting fd 2 to devnull from a Python
    atexit handler stays in effect for the remaining C finalizers, keeping the
    stderr line-protocol pure; nothing legitimate writes there after this point.
    """
    global _EXIT_GUARD_INSTALLED
    if _EXIT_GUARD_INSTALLED:
        return
    _EXIT_GUARD_INSTALLED = True

    def _mute() -> None:
        try:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, 2)
            os.close(devnull)
        except OSError:
            pass

    atexit.register(_mute)


def gtk_bootstrap() -> Path | None:
    """Inject the GTK DLL directory (idempotent); return the hit or None."""
    env_bin = os.environ.get(GTK_BIN_ENV)
    candidates = [Path(env_bin)] if env_bin else [Path(p) for p in _DEFAULT_GTK_CANDIDATES]
    add_dll_directory = getattr(os, "add_dll_directory", None)
    for cand in candidates:
        if (cand / "libgobject-2.0-0.dll").is_file():
            if add_dll_directory is not None:
                add_dll_directory(str(cand))
            os.environ["PATH"] = str(cand) + os.pathsep + os.environ.get("PATH", "")
            return cand
    return None


def fontconfig_bootstrap() -> None:
    """Render the self-supplied fonts.conf and point fontconfig at it."""
    conf_tpl = KAMI_ROOT / "fonts.conf"
    if not conf_tpl.is_file():
        return
    windir = os.environ.get("WINDIR", r"C:\Windows")
    cache_dir = Path(os.environ.get("TEMP", ".")) / "fc-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    rendered = cache_dir / "fonts.conf"
    rendered.write_text(
        conf_tpl.read_text(encoding="utf-8")
        .replace("@@WINDIR_FONTS@@", windir + r"\Fonts")
        .replace("@@FC_CACHE_DIR@@", str(cache_dir)),
        encoding="utf-8",
    )
    # FONTCONFIG_FILE 指认配置文件本体;FONTCONFIG_PATH 兜住 pango/ft2 在
    # C 层另行初始化的 fontconfig 实例(它们先查 PATH 再查 FILE)。
    os.environ["FONTCONFIG_FILE"] = str(rendered)
    os.environ["FONTCONFIG_PATH"] = str(cache_dir.parent)


def weasyprint():
    """Import weasyprint lazily (after the GTK/fontconfig bootstrap)."""
    gtk_bootstrap()
    fontconfig_bootstrap()
    _install_exit_noise_guard()
    return import_module("weasyprint")


def import_kami_module(name: str) -> Any:
    """Load a vendored kami script module by name (build/checks/content/...)."""
    scripts = KAMI_ROOT / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    return import_module(name)


def render_pdf(html_path: Path, pdf_path: Path) -> int:
    """Render HTML to PDF and return the page count; raises on failure."""
    mod = weasyprint()
    doc = mod.HTML(filename=str(html_path)).render()
    doc.write_pdf(str(pdf_path))
    return len(doc.pages)


def page_images(pdf_path: Path, out_dir: Path, dpi: int = 150) -> list[Path]:
    """Export each PDF page as a PNG (visual pass); return the paths in order."""
    pymupdf = import_module("pymupdf")
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    with pymupdf.open(str(pdf_path)) as doc:
        for i, page in enumerate(doc, start=1):
            pix = page.get_pixmap(dpi=dpi)
            p = out_dir / f"page-{i:02d}.png"
            pix.save(str(p))
            paths.append(p)
    return paths
