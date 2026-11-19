"""A corrupt catalog must never be replaced with an empty one.

``ModelCatalogService.load`` treats a missing catalog as a fresh install and
seeds it with defaults, which is right. It used to treat an *unparseable*
catalog the same way, because both look like "{}" to the reader — so a single
truncated write (a crash, a full disk, an interrupted editor save) destroyed
every stored API key on the next read, silently and irreversibly.

The catalog now raises ``CatalogUnreadable`` instead. These tests pin both
halves of that: the corrupt file survives untouched, and the ordinary paths
(absent file, healthy file) still behave as they did.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from deeptutor.services.config.model_catalog import (
    CatalogUnreadable,
    ModelCatalogService,
)

SECRET = "sk-do-not-lose-this-value"

HEALTHY = {
    "version": 1,
    "connections": [],
    "services": {
        "llm": {
            "active_profile_id": "p1",
            "active_model_id": "m1",
            "profiles": [{"id": "p1", "api_key": SECRET, "models": []}],
        }
    },
}


def _catalog(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "model_catalog.json"
    path.write_text(text, encoding="utf-8")
    return path


def test_truncated_catalog_is_not_overwritten(tmp_path: Path) -> None:
    path = _catalog(tmp_path, json.dumps(HEALTHY))
    path.write_text('{"version": 1, "connections": [', encoding="utf-8")
    corrupt = path.read_bytes()

    with pytest.raises(CatalogUnreadable):
        ModelCatalogService(path).load()

    assert path.read_bytes() == corrupt, (
        "the unreadable catalog was rewritten; any API key inside it is gone"
    )


def test_the_error_tells_the_operator_what_to_do(tmp_path: Path) -> None:
    path = _catalog(tmp_path, "{not json")

    with pytest.raises(CatalogUnreadable) as caught:
        ModelCatalogService(path).load()

    message = str(caught.value)
    assert str(path) in message
    assert "left untouched" in message
    # Recovery has to be discoverable from the message alone, because the
    # failure surfaces at startup where there is no other context.
    assert "Repair the file" in message and "move it aside" in message


def test_a_non_object_catalog_is_not_treated_as_empty(tmp_path: Path) -> None:
    path = _catalog(tmp_path, "[1, 2, 3]")

    with pytest.raises(CatalogUnreadable):
        ModelCatalogService(path).load()

    assert path.read_text(encoding="utf-8") == "[1, 2, 3]"


def test_an_absent_catalog_is_still_seeded(tmp_path: Path) -> None:
    path = tmp_path / "model_catalog.json"

    catalog = ModelCatalogService(path).load()

    assert path.exists(), "a fresh install must still get a catalog file"
    assert len(catalog["services"]) >= 1


def test_an_empty_file_is_still_seeded(tmp_path: Path) -> None:
    # Zero bytes is a write that never started, not a corrupt payload, so it
    # keeps the old graceful path rather than raising at startup.
    path = _catalog(tmp_path, "")

    ModelCatalogService(path).load()

    assert path.stat().st_size > 0


def test_a_healthy_catalog_keeps_its_secret(tmp_path: Path) -> None:
    path = _catalog(tmp_path, json.dumps(HEALTHY))

    catalog = ModelCatalogService(path).load()

    assert "sk-do-not-lose-this-value" in path.read_text(encoding="utf-8")
    assert catalog["services"]["llm"]["active_profile_id"] == "p1"
