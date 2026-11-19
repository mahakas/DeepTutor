"""The UI language list has to match the locales the frontend actually ships.

Regression guard for a real defect: ``web/i18n/languages.ts`` listed ``fa`` and
``_normalize_language`` handled it, but the ``UiLanguage`` Literal omitted it, so
``PUT /api/settings/ui {"language": "fa"}`` was rejected by request validation
while the picker still offered Persian. The two lists drifted because nothing
tied them together.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import get_args

import pytest

from deeptutor.services.settings.interface_settings import UiLanguage

REPO_ROOT = Path(__file__).resolve().parents[3]
LANGUAGES_TS = REPO_ROOT / "web" / "i18n" / "languages.ts"
LOCALES = REPO_ROOT / "web" / "locales"


def _frontend_languages() -> set[str]:
    """Codes from APP_LANGUAGES in languages.ts, without a TS toolchain."""
    source = LANGUAGES_TS.read_text(encoding="utf-8")
    block = re.search(r"APP_LANGUAGES[^=]*=\s*\[(.*?)\]", source, re.S)
    assert block, "APP_LANGUAGES not found in languages.ts"
    codes = re.findall(r'code:\s*"([a-z]{2})"', block.group(1))
    assert codes, "no language codes parsed out of APP_LANGUAGES"
    return set(codes)


@pytest.mark.parametrize("code", sorted(_frontend_languages()))
def test_every_frontend_language_is_accepted_by_the_backend(code: str) -> None:
    assert code in get_args(UiLanguage), (
        f"{code!r} is offered by the frontend picker but rejected by UiLanguage; "
        "selecting it would fail request validation"
    )


def test_backend_accepts_nothing_the_frontend_cannot_render() -> None:
    orphaned = set(get_args(UiLanguage)) - _frontend_languages()
    assert not orphaned, f"UiLanguage allows languages with no frontend entry: {orphaned}"


@pytest.mark.parametrize("code", sorted(_frontend_languages()))
def test_every_frontend_language_has_a_loadable_locale_file(code: str) -> None:
    path = LOCALES / code / "app.json"
    assert path.is_file(), f"missing bundle for {code}: {path}"
    keys = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(keys, dict) and keys, f"{path} is empty"
