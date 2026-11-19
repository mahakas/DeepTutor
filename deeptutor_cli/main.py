"""The DeepTutor entry point: start, stop and inspect the web app.

Why this file still exists in a web-only product
------------------------------------------------
The web app is a Next.js frontend over a FastAPI backend, and something has to
bring both up in the right order, on the right ports, with the right runtime
home. That something is ``deeptutor start``. Removing the CLI entirely would
leave the web app with no way to launch, which is not what "web only" means.

What was removed
----------------
Every terminal *product* surface: ``chat``, ``skill``, ``plugin``, ``config``,
``session``, ``provider``, ``workspace``, and the module commands (``book``,
``kb``, ``memory``, ``notebook``, ``partner``). Those were a second way to use
DeepTutor that happened to live in a terminal; this project is the browser one.

What stayed, and why each one is load-bearing for the web app
-------------------------------------------------------------
``start`` / ``stop`` / ``serve``
    The launcher. ``deeptutor start`` is what the README, the Dockerfile and
    ``runtime/launcher.py`` all invoke.
``init`` / ``init_wizard`` / ``setup_config``
    First-run setup: runtime home, provider, model. The web settings page can
    change these later, but the very first launch has no server to ask.
``doctor``
    Diagnosis for a stack that did not start. Its value is highest exactly when
    the web app cannot run and cannot explain why.
``module``
    Install and remove optional modules. A deployment concern, not a chat one.
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
import sys

import typer

from deeptutor.logging import configure_logging
from deeptutor.modules.catalog import manifests, module_enabled
from deeptutor.runtime.mode import RunMode, set_mode

from .common import console
from .doctor import register as register_doctor
from .init_cmd import register as register_init
from .module import register as register_module

set_mode(RunMode.CLI)
configure_logging(console_stream=sys.stderr)

app = typer.Typer(
    name="deeptutor",
    help="DeepTutor – launch and operate the web app.",
    no_args_is_help=True,
    add_completion=False,
)

# Module-registered commands are intentionally not mounted. The modules
# themselves still exist and still serve their HTTP routes; what went away is
# their terminal entry point. ``manifests`` is still imported because ``init``
# and ``doctor`` read it to report what is installed.
for owner, module in manifests().items():
    if not module_enabled(owner):
        continue
    for command in module["commands"]:
        # A manifest that still declares a command now points at a module that
        # does not exist. Fail loudly at import time rather than silently
        # offering a command that raises when clicked.
        if command["register"].startswith("deeptutor_cli."):
            module_path, _, _ = command["register"].partition(":")
            try:
                import_module(module_path)
            except ImportError as exc:  # pragma: no cover - packaging error
                raise SystemExit(
                    f"module '{owner}' declares a terminal command "
                    f"({command['name']}) but {module_path} is not installed. "
                    "This product is web-only; remove the command from the manifest."
                ) from exc

register_doctor(app)
register_init(app)
module_app = typer.Typer(help="Install, remove and inspect optional modules.")
app.add_typer(module_app, name="module")
register_module(module_app)


@app.command()
def start(
    home: Path | None = typer.Option(None, "--home", help="Runtime workspace root."),
    dev: bool = typer.Option(
        False,
        "--dev",
        help="Use the Next.js development server for frontend work.",
    ),
    detach: bool = typer.Option(
        False,
        "--detach",
        help="Run outside the current console; stop later with `deeptutor stop`.",
    ),
    open_browser: bool = typer.Option(
        True,
        "--open-browser/--no-browser",
        help="Open the frontend automatically after startup.",
    ),
) -> None:
    """Launch backend + frontend together. Source installs default to production."""
    from deeptutor.modules.catalog import require_module

    require_module("server")
    require_module("web")
    from deeptutor.runtime.launcher import start as start_web

    start_web(home=home, dev=dev, detach=detach, open_browser=open_browser)


@app.command()
def stop(
    home: Path | None = typer.Option(None, "--home", help="Runtime workspace root."),
) -> None:
    """Stop a DeepTutor launcher started with ``--detach``."""
    from deeptutor.runtime.launcher import stop as stop_web

    if not stop_web(home=home):
        raise typer.Exit(code=1)


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Bind address."),
    port: int | None = typer.Option(None, help="Port number."),
    reload: bool = typer.Option(False, help="Enable auto-reload for development."),
) -> None:
    """Start only the DeepTutor API server (no frontend)."""
    import asyncio

    from deeptutor.modules.catalog import require_module

    require_module("server")
    set_mode(RunMode.SERVER)
    if port is None:
        from deeptutor.services.setup import get_backend_port

        port = get_backend_port()

    # Windows: uvicorn defaults to SelectorEventLoop which does not support
    # asyncio.create_subprocess_exec.  Switch to ProactorEventLoop so that
    # child-process APIs (used by Math Animator renderer, etc.) work correctly.
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    try:
        import uvicorn
    except ImportError:
        console.print(
            "[bold red]Error:[/] API server dependencies not installed.\n"
            "Run: deeptutor module install server"
        )
        raise typer.Exit(code=1)

    from deeptutor.services.config import (
        HTTP_KEEP_ALIVE_TIMEOUT,
        get_ws_max_size,
        load_system_settings,
    )

    backend_workers = max(1, int(load_system_settings().get("backend_workers") or 1))
    if reload and backend_workers > 1:
        console.print("[bold red]Error:[/] --reload cannot be used when backend_workers > 1.")
        raise typer.Exit(code=2)

    # ws_max_size tracks the configured chat-attachment total so base64
    # uploads fit in one WS frame (uvicorn defaults to 16MB).
    #
    # These three flags are not optional tuning. Without timeout_keep_alive the
    # proxy's 5s idle reap and uvicorn's 5s default race on the same socket and
    # the loser gets ECONNRESET, surfaced to the user as "Failed to load
    # sessions". A rewrite of this file once dropped all three; the launch-point
    # test caught it, which is exactly why that test exists.
    uvicorn.run(
        "deeptutor.api.main:app",
        host=host,
        port=port,
        reload=reload,
        workers=backend_workers,
        reload_excludes=["web/*", "data/*"] if reload else None,
        # Keep request.client tied to the actual peer; XFF is client-controlled
        # unless the deployment explicitly provides a trusted proxy.
        proxy_headers=False,
        ws_max_size=get_ws_max_size(),
        timeout_keep_alive=HTTP_KEEP_ALIVE_TIMEOUT,
        timeout_graceful_shutdown=1,
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
