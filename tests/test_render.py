from digest import render


def _inc(sev: str, cat: str = "outage", users: int = 100) -> dict:
    return {"severity": sev, "category": cat, "affected_users": users,
            "summary": "the thing broke"}


def test_the_headline_says_nothing_urgent_when_nothing_is():
    out = render.headline([_inc("low"), _inc("medium")])
    assert "nothing above" in out


def test_the_headline_counts_only_what_clears_the_floor():
    out = render.headline([_inc("critical"), _inc("low"), _inc("high")])
    assert out.startswith("2 of 3")


def test_the_digest_puts_the_worst_first():
    body = render.digest([_inc("low"), _inc("critical"), _inc("medium")])
    lines = [ln for ln in body.splitlines() if ln.startswith("[")]
    assert "CRITICAL" in lines[0]


def test_a_line_uses_the_label_from_the_vocabulary():
    assert "Degraded service" in render.line(_inc("high", cat="degradation"))
