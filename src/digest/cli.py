"""Read incidents, rank them, print the digest.

    python -m digest.cli incidents.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from . import categories, render, severity, summarize


def _offline(prompt: str) -> str:
    """Stand-in for a model call, so the demo runs with no credentials."""
    for line in prompt.splitlines():
        if line.startswith("Title: "):
            return line[len("Title: "):]
    return "(no title)"


def enrich(raw: dict, *, call=_offline) -> dict:
    weight = categories.weight_of(raw["category"])
    affected = int(raw.get("affected_users", 0))
    return {
        "category": raw["category"],
        "affected_users": affected,
        "severity": severity.severity(weight, affected),
        "summary": summarize.summarise(raw["title"], raw.get("body", ""), call=call),
    }


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    raw = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    print(render.digest([enrich(r) for r in raw["incidents"]]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
