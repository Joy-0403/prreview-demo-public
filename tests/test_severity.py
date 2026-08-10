from digest import severity


def test_the_ladder_is_ordered_low_to_high():
    assert severity.LADDER[0] == "info"
    assert severity.LADDER[-1] == "critical"


def test_nobody_affected_is_not_critical():
    """A high-weight category with no users affected is still not the top rung;
    both inputs have to agree."""
    assert severity.severity(5, 0) != "critical"


def test_a_cosmetic_issue_affecting_everyone_is_not_critical():
    assert severity.severity(1, 50_000) != "critical"


def test_an_outage_affecting_a_product_area_is_critical():
    assert severity.severity(5, 20_000) == "critical"


def test_at_least_is_inclusive():
    assert severity.at_least("high", "high")
    assert severity.at_least("critical", "high")
    assert not severity.at_least("medium", "high")


def test_an_unknown_name_never_clears_a_floor():
    assert not severity.at_least("catastrophic", "high")
