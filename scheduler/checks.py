"""Sheet checks: rules a finished day's schedule should follow. No Qt, so the
rules can be tested and reused on their own.

Add a rule by writing a function `(team, day) -> list[str]` and listing it in
RULES; each string is one problem, worded for the person building the sheet.
"""

from __future__ import annotations

from .models import Team, Day


def required_tasks_assigned(team: Team, day: Day) -> list[str]:
    """Every task marked Required is given to at least one person working today."""
    working = {w.id for w in day.working}
    used = {s.task for aid, segs in day.segments.items() if aid in working for s in segs}
    return [
        f"Nobody is assigned “{t.name}” (marked Required)."
        for t in team.tasks
        if t.required and t.name not in used
    ]


RULES = [required_tasks_assigned]


def find_violations(team: Team, day: Day) -> list[str]:
    return [problem for rule in RULES for problem in rule(team, day)]
