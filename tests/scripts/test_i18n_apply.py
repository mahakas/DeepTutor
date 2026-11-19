"""The translation merger must use displayed text, not rename-table keys."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "i18n" / "apply.py"


@pytest.fixture
def merger(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("i18n_apply", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    locales = tmp_path / "locales"
    for language in ("en", "fa"):
        (locales / language).mkdir(parents=True)
    monkeypatch.setattr(module, "LOCALES", locales)
    monkeypatch.setattr(module, "ROOT", tmp_path)

    def run(en, fa, batch, *flags):
        for language, data in (("en", en), ("fa", fa)):
            (locales / language / "app.json").write_text(
                json.dumps(data, ensure_ascii=False), encoding="utf-8"
            )
        fa_path = locales / "fa" / "app.json"
        before = fa_path.read_bytes()
        batch_path = tmp_path / "batch.json"
        batch_path.write_text(json.dumps(batch, ensure_ascii=False), encoding="utf-8")
        monkeypatch.setattr(sys, "argv", [str(SCRIPT), str(batch_path), *flags])
        status = module.main()
        return status, json.loads(fa_path.read_text(encoding="utf-8")), before, fa_path.read_bytes()

    return run


def test_placeholder_validation_uses_displayed_value(merger):
    status, result, _, _ = merger(
        {"Old title": "Version {{version}}"},
        {},
        {"Old title": "نسخهٔ {{version}}"},
    )
    assert status == 0
    assert result == {"Old title": "نسخهٔ {{version}}"}


def test_by_value_expands_all_keys_with_same_display(merger):
    status, result, _, _ = merger(
        {"No notebooks": "No collections", "No collections": "No collections"},
        {},
        {"No collections": "مجموعه‌ای وجود ندارد"},
        "--by-value",
    )
    assert status == 0
    assert result == dict.fromkeys(("No notebooks", "No collections"), "مجموعه‌ای وجود ندارد")


def test_by_value_preserves_existing_translation(merger):
    status, result, _, _ = merger(
        {"Old": "New", "New": "New"},
        {"Old": "ترجمهٔ بازبینی‌شده"},
        {"New": "تازه"},
        "--by-value",
    )
    assert status == 0
    assert result == {"Old": "ترجمهٔ بازبینی‌شده", "New": "تازه"}


def test_by_value_force_replaces_existing_translation(merger):
    status, result, _, _ = merger(
        {"Old": "New"}, {"Old": "قبلی"}, {"New": "تازه"}, "--by-value", "--force"
    )
    assert status == 0
    assert result == {"Old": "تازه"}


@pytest.mark.parametrize(
    ("batch", "flags"),
    [
        ({"Missing": "ناموجود"}, ()),
        ({"Missing": "ناموجود"}, ("--by-value",)),
        ({"New": ""}, ("--by-value",)),
        ({"New": 1}, ("--by-value",)),
        ({"Version {{version}}": "نسخه"}, ("--by-value",)),
        ({"New": "تازه {{extra}}"}, ("--by-value",)),
    ],
)
def test_invalid_batch_never_writes_partial_result(merger, batch, flags):
    status, result, before, after = merger(
        {"OK": "OK", "Old": "New", "Version": "Version {{version}}"},
        {"Existing": "موجود"},
        {"OK": "درست", **batch},
        *flags,
    )
    assert status == 1
    assert before == after
    assert result == {"Existing": "موجود"}


def test_dry_run_keeps_original_bytes(merger):
    status, result, before, after = merger(
        {"Old": "New"}, {}, {"New": "تازه"}, "--by-value", "--dry-run"
    )
    assert status == 0
    assert before == after
    assert result == {}


def test_literal_dotted_key_stays_flat(merger):
    status, result, _, _ = merger(
        {"settings.language": "Language"}, {}, {"Language": "زبان"}, "--by-value"
    )
    assert status == 0
    assert result == {"settings.language": "زبان"}
