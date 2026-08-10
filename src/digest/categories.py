"""The controlled vocabulary, loaded once.

`config/categories.json` is the single source. The Dockerfile copies it into
the image at build time, so an image built before a vocabulary change serves
the old list until it is rebuilt.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

CONFIG = Path(__file__).resolve().parents[2] / "config" / "categories.json"


class UnknownCategory(ValueError):
    pass


@lru_cache(maxsize=1)
def _table() -> dict[str, dict]:
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    return {c["key"]: c for c in data["categories"]}


def weight_of(key: str) -> int:
    try:
        return int(_table()[key]["weight"])
    except KeyError:
        raise UnknownCategory(
            f"{key!r} is not in {CONFIG.name}. Add it there rather than "
            "special-casing it here."
        ) from None


def label_of(key: str) -> str:
    return _table()[key]["label"]


def known() -> list[str]:
    return sorted(_table())
