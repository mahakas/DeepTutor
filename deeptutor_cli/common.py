"""Shared CLI console, and the input helpers setup still needs.

What used to be here
--------------------
923 lines of turn rendering: streamed chat rounds, tool-call and tool-result
frames, SIGINT interception, notebook tables, session tables. All of it served
``deeptutor chat`` and ``deeptutor run``, which are terminal product surfaces
and are gone.

What remains is what the launcher genuinely needs: one configured Rich console
(109 call sites across ``init``, ``doctor`` and ``module``) and the two input
primitives the setup wizard uses. Keeping the rest would have meant shipping
a renderer nothing can call.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys
from typing import Iterator, TextIO
import unicodedata

from rich.console import Console

console = Console()


def _utf8_aware_terminal_input(stream: TextIO) -> Iterator[None]:
    """Read stdin as UTF-8 even on a Windows console with a legacy code page.

    Without this, an answer typed in Persian arrives as mojibake before the
    wizard ever sees it -- and then gets written into a settings file.
    """
    encoding = getattr(stream, "encoding", None) or ""
    previous = encoding
    try:
        if hasattr(stream, "reconfigure") and encoding.lower().replace("-", "") != "utf8":
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):  # pragma: no cover - exotic streams
        pass
    try:
        yield
    finally:
        if previous and hasattr(stream, "reconfigure"):  # pragma: no cover
            try:
                stream.reconfigure(encoding=previous)  # type: ignore[attr-defined]
            except (AttributeError, ValueError):
                pass


def read_console_input(prompt: str) -> str:
    """Ask the operator a question, with UTF-8 safe input."""
    with _utf8_aware_terminal_input(sys.stdin):
        return input(prompt)


def print_path_result(path: str | Path) -> None:
    """Report a filesystem result without Rich trying to markup the path.

    Paths can contain ``[`` and a Windows path contains ``\\``; both are markup
    to Rich and would either swallow text or abort the render.
    """
    console.print(str(path), markup=False, highlight=False)


def _one_line(value: object) -> str:
    """Collapse whitespace and drop control characters for a terminal."""
    text = " ".join(str(value).split())
    return "".join(ch for ch in text if unicodedata.category(ch)[0] != "C")


def maybe_run(coro):  # noqa: ANN001
    """Run a coroutine and release the application container's leases.

    This is not a convenience wrapper. ``close_application_container`` is what
    releases turns, subprocesses and module leases on the owning loop; without
    it a CLI exit leaves work running and a lease held. An earlier rewrite of
    this file replaced it with an unrelated context manager and dropped that
    guarantee -- the runtime-cleanup tests caught it, which is what they are
    for.
    """

    async def run_and_close():
        from deeptutor.app.container import close_application_container

        try:
            return await coro
        finally:
            await close_application_container()

    try:
        return asyncio.run(run_and_close())
    except KeyboardInterrupt:
        console.print("\n[dim]متوقف شد.[/]")
        return None


__all__ = [
    "console",
    "maybe_run",
    "print_path_result",
    "read_console_input",
]
