"""Turning ranked incidents into the text people actually read."""

from __future__ import annotations

from . import categories, severity

# What gets a siren in the headline. Read from the ladder rather than spelled
# out, so raising the bar for `critical` does not need an edit here too.
ALERT_FLOOR = "high"


def headline(incidents: list[dict]) -> str:
    urgent = [i for i in incidents if severity.at_least(i["severity"], ALERT_FLOOR)]
    if not urgent:
        return f"{len(incidents)} incident(s), nothing above {ALERT_FLOOR}."
    return f"{len(urgent)} of {len(incidents)} incident(s) at {ALERT_FLOOR} or worse."


def line(incident: dict) -> str:
    label = categories.label_of(incident["category"])
    mark = "!" if severity.is_urgent(incident["severity"]) else " "
    return (
        f"{mark}[{incident['severity'].upper():>8}] {label} - {incident['summary']} "
        f"({incident['affected_users']} affected, {incident['region']})"
    )


def digest(incidents: list[dict]) -> str:
    ordered = sorted(
        incidents,
        key=lambda i: (severity.LADDER.index(i["severity"]), i["affected_users"]),
        reverse=True,
    )
    return "\n".join([headline(ordered), "", *(line(i) for i in ordered)])
