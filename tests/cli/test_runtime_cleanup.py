"""CLI completion releases the runtime before closing its event loop."""

import asyncio

import pytest
from typer.testing import CliRunner

from deeptutor.app import container as containers
from deeptutor.modules.lifecycle import environment_lease
from deeptutor_cli.common import maybe_run
from deeptutor_cli.main import app


@pytest.mark.parametrize("outcome", ["success", "error", "cancel"])
def test_cli_releases_runtime_lease_on_every_exit(outcome):
    container = containers.get_application_container()

    async def command():
        await container.start()
        if outcome == "error":
            raise ValueError("command failed")
        if outcome == "cancel":
            raise asyncio.CancelledError
        return "done"

    if outcome == "success":
        assert maybe_run(command()) == "done"
    else:
        error = ValueError if outcome == "error" else asyncio.CancelledError
        with pytest.raises(error):
            maybe_run(command())
    assert not container._started
    assert container._module_lease is None
    assert containers._default_container is None
    with environment_lease(exclusive=True):
        pass


def test_a_failing_launcher_command_does_not_block_module_changes():
    """A command that fails must still release the environment lease.

    This used to drive `deeptutor run <bad-capability>`. That command is gone
    with the terminal product, but the invariant it protected is not: whatever
    a launcher command does, a failure must not leave the lease held, because
    the next module install would then block forever. `start` on a missing
    module is the surviving way to make a command fail before doing any work.
    """
    result = CliRunner().invoke(app, ["start", "--home", "/nonexistent/read-only/path"])
    assert result.exit_code != 0 or result.exception is not None
    with environment_lease(exclusive=True):
        pass


def test_cleanup_does_not_construct_an_unused_container(monkeypatch):
    monkeypatch.setattr(
        containers.ApplicationContainer,
        "build",
        lambda: pytest.fail("Cleanup constructed a runtime"),
    )

    async def command():
        return 42

    assert maybe_run(command()) == 42
