"""Merge a translation batch into the Persian bundle, safely.

The translation is data, not a hand-edited JSON blob, for three reasons: a batch
can be reviewed on its own, a merge cannot silently clobber a key that landed in
the meantime, and progress is measurable between batches instead of at the end.

Rules the merge enforces, each because breaking it produces a bug that does not
look like a translation bug:

* Every key must exist in the English bundle. A key that does not is a typo or
  a stale string, and writing it produces a bundle entry nothing will ever read.
* A translation must not be empty. An empty value with ``returnEmptyString:
  false`` silently falls back to English, so "translated" would be a lie the
  status report believes.
* ``{{placeholders}}`` must match the source exactly. A dropped placeholder
  renders a sentence with a hole in it; an invented one raises at runtime.
* Keys already translated are never overwritten unless ``--force`` is given.
  Two batches racing on the same key is how a good translation disappears.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCALES = ROOT / "web" / "locales"
PLACEHOLDER = __import__("re").compile(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}")


def flatten(node, prefix=""):
    out = {}
    for key, value in node.items():
        full = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            out.update(flatten(value, full))
        else:
            out[full] = value
    return out


def unflatten(mapping):
    """Return the bundle as the flat mapping the app actually reads.

    Deliberately flat. Both `en/app.json` and `fa/app.json` store keys like
    ``"language.english"`` as *literal* top-level keys and contain no nested
    objects at all -- 2,412 of the English keys contain a dot. The app reads
    them that way because ``keySeparator`` is disabled, so ``"language.english"``
    is one key and not a path.

    An earlier version of this function rebuilt nesting, which would have turned
    2,412 working keys into unreachable ones while leaving the file looking
    organised. The name is kept so the intent -- "produce the on-disk shape" --
    stays visible next to the reason it does not nest.
    """
    return dict(mapping)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("batch", help="JSON file: {\"English source\": \"Persian\"}")
    ap.add_argument("--bundle", default="app")
    ap.add_argument("--force", action="store_true", help="overwrite existing translations")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--by-value",
        action="store_true",
        help=(
            "Match batch entries against the English bundle's *displayed* text "
            "instead of its keys. Needed for entries whose value differs from "
            "their key: the English bundle uses those to rename a brand term "
            "(key 'No notebooks yet' displays 'No favorites collections yet'), "
            "so the sentence a reader sees, and the sentence a translator "
            "translates, is the value."
        ),
    )
    args = ap.parse_args()

    en = flatten(json.loads((LOCALES / "en" / f"{args.bundle}.json").read_text(encoding="utf-8")))
    fa_path = LOCALES / "fa" / f"{args.bundle}.json"
    fa = flatten(json.loads(fa_path.read_text(encoding="utf-8")))

    batch = json.loads(Path(args.batch).read_text(encoding="utf-8"))
    if not isinstance(batch, dict) or not batch:
        raise SystemExit("batch must be a non-empty JSON object")

    errors: list[str] = []
    added = skipped = 0

    if args.by_value:
        # One display sentence can back several keys; all of them get the
        # translation, and each is validated on its own.
        by_display = {}
        for key, value in en.items():
            by_display.setdefault(str(value), []).append(key)
        expanded = {}
        for source, target in batch.items():
            hits = by_display.get(source)
            if not hits:
                errors.append(f"unknown display text (not in en bundle): {source!r}")
                continue
            for key in hits:
                expanded[key] = target
        batch = expanded

    for source, target in batch.items():
        if source not in en:
            errors.append(f"unknown key (not in en bundle): {source!r}")
            continue
        if not isinstance(target, str) or not target.strip():
            errors.append(f"empty translation: {source!r}")
            continue
        # Placeholders are checked against the text the reader actually sees.
        # For a "renamed" entry -- one whose value differs from its key, which
        # is how the English bundle renames a brand term -- the value is the
        # source sentence, and the key is only a lookup token.
        visible = str(en[source])
        want = set(PLACEHOLDER.findall(visible))
        got = set(PLACEHOLDER.findall(target))
        if want != got:
            errors.append(
                f"placeholder mismatch in {source!r}: expected {sorted(want)}, got {sorted(got)}"
            )
            continue
        if source in fa and not args.force:
            skipped += 1
            continue
        fa[source] = target
        added += 1

    if errors:
        print(f"{len(errors)} problem(s), nothing written:")
        for err in errors[:25]:
            print(f"  - {err}")
        if len(errors) > 25:
            print(f"  ... and {len(errors) - 25} more")
        return 1

    print(f"added {added}, skipped {skipped} (already translated)")
    if args.dry_run:
        return 0

    fa_path.write_text(
        json.dumps(unflatten(fa), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {fa_path.relative_to(ROOT)}  ({len(fa):,} keys)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
