"""How an incident's severity is decided.

One ladder, used by everything that ranks or filters incidents. The thresholds
live here rather than at each call site so that raising the bar for `critical`
is a single edit -- see `render.headline`, which reads the same ladder rather
than restating it.
"""

from __future__ import annotations

# Ordered low to high. The index is the comparison key; the names are what
# reaches a human.
LADDER: tuple[str, ...] = ("info", "low", "medium", "high", "critical")

# A category's weight plus the number of affected users decides the rung.
# Both inputs matter: a cosmetic issue affecting everyone is not critical, and
# an outage affecting one internal tool is not either.
_USER_BANDS: tuple[tuple[int, int], ...] = (
    (0, 0),        # nobody affected yet
    (10, 1),       # a handful
    (500, 2),      # a team
    (10_000, 3),   # a product area
)


def _user_score(affected: int) -> int:
    score = 0
    for threshold, points in _USER_BANDS:
        if affected >= threshold:
            score = points
    return score


def rank(weight: int, affected_users: int) -> int:
    """Index into LADDER. Clamped, so a new category weight cannot fall off."""
    raw = _user_score(affected_users) + (weight - 1) // 2
    return max(0, min(raw, len(LADDER) - 1))


def severity(weight: int, affected_users: int) -> str:
    return LADDER[rank(weight, affected_users)]


def at_least(name: str, floor: str) -> bool:
    """True when `name` is `floor` or worse. Unknown names sort lowest."""
    try:
        return LADDER.index(name) >= LADDER.index(floor)
    except ValueError:
        return False


def is_urgent(name: str) -> bool:
    """Whether this rung wakes somebody up."""
    return name in ("high", "critical")
