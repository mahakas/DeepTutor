"""What is translated, what is not, and in what order to fix it.

The Persian bundle is keyed by the English sentence itself
(``keySeparator: false``), so "translate" is a flat mapping and "how far along
are we" is a set difference. This reports that difference by size bucket,
because the buckets are not equally useful: 3,170 of the missing strings are
under 20 characters and make up 20% of the volume, while 80 strings over 160
characters make up 8%. Translating by volume and translating by impact are
different jobs, and the report should show both.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LOCALES = ROOT / "web" / "locales"


def flatten(node, prefix=""):
    out = {}
    for key, value in node.items():
        full = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            out.update(flatten(value, full))
        else:
            out[full] = value
    return out


def load(lang, name):
    path = LOCALES / lang / f"{name}.json"
    if not path.exists():
        return {}
    return flatten(json.loads(path.read_text(encoding="utf-8")))


def report(name="app", *, show=0):
    en = load("en", name)
    fa = load("fa", name)
    todo = {k: str(v) for k, v in en.items() if k not in fa}
    total_chars = sum(len(str(v)) for v in en.values()) or 1
    done_chars = sum(len(str(v)) for k, v in en.items() if k in fa)

    print(f"{name}.json")
    print(f"  keys        {len(en):,}")
    print(f"  translated  {len(en) - len(todo):,}  ({100 * (len(en) - len(todo)) / max(len(en), 1):.1f}% of keys)")
    print(f"  volume      {done_chars:,} / {total_chars:,} chars ({100 * done_chars / total_chars:.1f}%)")
    print(f"  remaining   {len(todo):,} keys, {sum(len(v) for v in todo.values()):,} chars")

    buckets = [(0, 20), (20, 40), (40, 80), (80, 160), (160, 10**9)]
    print(f"\n  {'size':>12s}  {'keys':>6s}  {'chars':>9s}")
    for lo, hi in buckets:
        sel = [v for v in todo.values() if lo < len(v) <= hi]
        label = f"{lo+1}-{hi}" if hi < 10**9 else f">{lo}"
        print(f"  {label:>12s}  {len(sel):6d}  {sum(len(v) for v in sel):9,d}")

    if show:
        print(f"\n  next {show} shortest:")
        for key, value in sorted(todo.items(), key=lambda kv: len(kv[1]))[:show]:
            print(f"    {value!r}")
    return len(todo)


if __name__ == "__main__":
    count = report("app", show=int(sys.argv[1]) if len(sys.argv) > 1 else 0)
    report("common")
    sys.exit(0)
