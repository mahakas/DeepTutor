"""Launcher help must not fall back to English framework chrome."""

import pytest
from typer.testing import CliRunner

from deeptutor_cli.main import app
from deeptutor_cli.setup_config import _api_key, _validate_endpoint


@pytest.mark.parametrize(
    "command",
    [[], ["start"], ["stop"], ["serve"], ["init"], ["doctor"], ["module"], ["module", "list"]],
)
def test_help_uses_persian_usage_and_help_description(command):
    result = CliRunner().invoke(app, [*command, "--help"])
    assert result.exit_code == 0, result.output
    assert "روش استفاده:" in result.output
    assert "نمایش راهنما و خروج." in result.output
    assert "Usage:" not in result.output
    assert "Show this message and exit" not in result.output
    assert "[OPTIONS]" not in result.output


def test_setup_api_key_error_is_persian_without_disclosing_environment(monkeypatch):
    monkeypatch.delenv("DARSYAR_MISSING_TEST_KEY", raising=False)
    with pytest.raises(ValueError, match="خالی است یا تنظیم نشده") as error:
        _api_key("DARSYAR_MISSING_TEST_KEY", required=True, section="llm")
    assert "DARSYAR_MISSING_TEST_KEY" not in str(error.value)


def test_setup_endpoint_error_is_persian_and_does_not_echo_credentials():
    with pytest.raises(ValueError, match="نباید اطلاعات ورود داشته باشد") as error:
        _validate_endpoint("https://private:secret@example.test", "llm")
    assert "private" not in str(error.value)
    assert "secret" not in str(error.value)
