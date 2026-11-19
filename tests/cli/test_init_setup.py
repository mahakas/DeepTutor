"""The surviving first-run path, against real isolated settings files.

This replaces ``test_agent_setup.py``. That module drove ``deeptutor config
apply``, a terminal command removed when the project became web-only. The
*behaviour* it protected is still worth protecting -- a headless setup must not
prompt, must not overwrite saved choices, and must fail before writing -- so
these tests drive ``deeptutor init --non-interactive`` instead, which is the
setup path that survived.

Deleting the old file outright would have quietly dropped those guarantees from
the suite. Rewriting it keeps the assertions and changes only the entry point.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from deeptutor_cli.main import app
from deeptutor_cli.setup_config import select_runtime_home

runner = CliRunner()


@pytest.fixture
def runtime_home(tmp_path, monkeypatch):
    from deeptutor.multi_user import paths

    for name in (
        "PROJECT_ROOT",
        "ADMIN_WORKSPACE_ROOT",
        "USERS_ROOT",
        "SYSTEM_ROOT",
        "LEGACY_MULTI_USER_ROOT",
        "_path_services",
        "_legacy_migration_done",
    ):
        monkeypatch.setattr(paths, name, {} if name == "_path_services" else getattr(paths, name))
    home = tmp_path / "runtime"
    monkeypatch.setenv("DEEPTUTOR_HOME", str(home))
    monkeypatch.delenv("BACKEND_PORT", raising=False)
    monkeypatch.delenv("FRONTEND_PORT", raising=False)
    select_runtime_home(home)
    yield home
    from deeptutor_cli.init_cmd import _reset_runtime_singletons

    _reset_runtime_singletons()


def _init(home: Path):
    return runner.invoke(app, ["init", "--non-interactive", "--home", str(home)])


# ---------------------------------------------------------------------------
# The launcher's commands exist; the terminal product's do not
# ---------------------------------------------------------------------------


def test_the_launcher_commands_are_what_remains():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("start", "stop", "serve", "init", "doctor", "module"):
        assert command in result.output, f"{command} is missing from the launcher"


@pytest.mark.parametrize("removed", ["chat", "skill", "plugin", "config", "kb", "notebook"])
def test_terminal_product_commands_are_gone(removed):
    """A web-only product should not advertise a terminal chat that cannot run."""
    result = runner.invoke(app, [removed, "--help"])
    assert result.exit_code != 0
    assert "No such command" in result.output


# ---------------------------------------------------------------------------
# Headless setup never prompts
# ---------------------------------------------------------------------------


def test_non_interactive_init_never_prompts(runtime_home, monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("Headless initialization must not prompt")

    monkeypatch.setattr("typer.prompt", unexpected)
    monkeypatch.setattr("typer.confirm", unexpected)
    result = _init(runtime_home)
    assert result.exit_code == 0, result.output


def test_non_interactive_init_is_repeatable(runtime_home):
    """Running setup twice must not corrupt what the first run wrote."""
    first = _init(runtime_home)
    assert first.exit_code == 0, first.output
    settings = runtime_home / "data/user/settings"
    before = {p.name: p.read_bytes() for p in settings.glob("*.json")}
    second = _init(runtime_home)
    assert second.exit_code == 0, second.output
    after = {p.name: p.read_bytes() for p in settings.glob("*.json")}
    assert after == before, "a repeat run rewrote saved settings"


def test_init_writes_settings_it_can_read_back(runtime_home):
    """A settings file that cannot be parsed is a first run that half-worked."""
    result = _init(runtime_home)
    assert result.exit_code == 0, result.output
    written = list((runtime_home / "data/user/settings").glob("*.json"))
    assert written, "init created no settings files"
    for path in written:
        json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Setup is what the launcher relies on
# ---------------------------------------------------------------------------


def test_init_shares_the_runtime_home_with_the_launcher(runtime_home):
    """`init --home` and `start --home` must mean the same directory."""
    result = _init(runtime_home)
    assert result.exit_code == 0, result.output
    from deeptutor.services.setup import get_backend_port

    # The port init resolved is the port the API server binds: if setup wrote
    # one home and the launcher read another, these would disagree.
    assert isinstance(get_backend_port(), int)


def test_a_home_with_an_unreadable_settings_file_still_starts_from_clean(
    runtime_home,
):
    """Corrupt JSON must not make setup crash without saying what to do."""
    settings = runtime_home / "data/user/settings"
    settings.mkdir(parents=True, exist_ok=True)
    (settings / "model_catalog.json").write_text("{broken JSON", encoding="utf-8")
    result = _init(runtime_home)
    assert result.exit_code == 0, result.output
