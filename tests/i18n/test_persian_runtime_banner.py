"""Persian CLI labels must stay complete and safe to format."""

from __future__ import annotations

from io import StringIO
import re
from string import Formatter

import pytest
from rich.console import Console

from deeptutor.runtime.banner import LABELS, _pick_language, labels_for, render_banner


@pytest.mark.parametrize("language", ["fa", "fa-IR", "fa_IR", "persian", "فارسی"])
def test_persian_runtime_aliases(language):
    assert _pick_language(language) == "fa"
    assert labels_for(language) is LABELS["fa"]


def test_persian_runtime_labels_are_complete_and_formattable():
    assert LABELS["fa"].keys() == LABELS["en"].keys()
    for key, source in LABELS["en"].items():
        target = LABELS["fa"][key]
        assert re.search(r"[\u0600-\u06ff]", target), key
        fields = lambda text: sorted(  # noqa: E731
            name for _, name, _, _ in Formatter().parse(text) if name is not None
        )
        assert fields(source) == fields(target), key
        target.format(**dict.fromkeys(fields(source), "نمونه"))


def test_persian_banner_has_persian_brand_and_setup_mode():
    out = StringIO()
    console = Console(file=out, width=100, force_terminal=False)
    console.print(render_banner("fa", mode_key="init.mode"))
    rendered = out.getvalue()
    assert "درسیار" in rendered
    assert "راه‌اندازی فضای کاری" in rendered
    assert "DeepTutor" not in rendered


def test_saved_persian_language_reaches_runtime(monkeypatch):
    from deeptutor.runtime.banner import resolve_language
    from deeptutor.services.settings import interface_settings

    monkeypatch.setattr(interface_settings, "get_ui_language", lambda default: "fa-IR")
    assert resolve_language() == "fa"


def test_runtime_language_defaults_to_persian_when_settings_fail(monkeypatch):
    from deeptutor.runtime.banner import resolve_language
    from deeptutor.services.settings import interface_settings

    def unavailable(default):
        raise OSError("settings unavailable")

    monkeypatch.setattr(interface_settings, "get_ui_language", unavailable)
    assert resolve_language() == "fa"
