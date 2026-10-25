"""Starter data used the first time the app runs."""

from datetime import date

from .models import (
    Associate,
    Day,
    Task,
    Team,
    Settings,
    ROLE_PICKER,
    ROLE_STOCKER,
    CAT_GENERAL,
    CAT_RUN,
    CAT_HELP,
    CAT_PICK,
)


def default_tasks() -> list[Task]:
    general = [
        ("Topstock", "#cfe0f2"),
        ("Break", "#f9d3b5"),
        ("Lunch", "#f6b98a"),
        ("Topstock / Cleanup", "#d7e9d0"),
        ("Zone", "#e3e3e3"),
        ("Backroom", "#dcdcdc"),
    ]
    run = [
        "Run Frozen",
        "Run GM",
        "Run Dairy #1",
        "Run Grocery #1",
        "Run HBA",
        "Run Pets",
        "Run Paper",
        "Run Chem",
        "Run Juice",
        "Run Snacks",
        "Run Candy",
        "Run Dairy #2",
        "Run Grocery #2",
    ]
    help_pick = [
        "Help Pick Frozen",
        "Help Pick GM",
        "Help Pick Dairy #1",
        "Help Pick Grocery",
        "Help Pick HBA",
        "Help Pick Pets / Paper / Chem",
        "Help Pick Juice / Candy / Snacks",
    ]
    pick = [
        "Pick Frozen",
        "Pick GM",
        "Pick Dairy #1",
        "Pick Grocery #1",
        "Pick HBA",
        "Pick Pets / Paper / Chem",
        "Pick Juice / Candy / Snacks",
        "Pick Dairy #2",
        "Pick Grocery #2",
    ]
    tasks = [Task(n, CAT_GENERAL, c) for n, c in general]
    tasks += [Task(n, CAT_RUN) for n in run]
    tasks += [Task(n, CAT_HELP) for n in help_pick]
    tasks += [Task(n, CAT_PICK) for n in pick]
    return tasks


def default_team() -> Team:
    """A sample roster so the app isn't empty on first launch.
    Names are placeholders — edit them in the Roster panel."""
    roster = [
        Associate("Picker", ROLE_PICKER, False, "", "A16/A17"),
        Associate("Stocker 1", ROLE_STOCKER, False, "", "A18/A19"),
        Associate("Stocker 2", ROLE_STOCKER, False, "", "A20/A21"),
        Associate("Stocker 3", ROLE_STOCKER, False, "", "A22/A23"),
        Associate("Stocker 4", ROLE_STOCKER, False, "Helps Pick GM", "G1/G2/G3/G4"),
        Associate("Stocker 5", ROLE_STOCKER, False, "Helps Pick Grocery", "HBA"),
        Associate("Stocker 6", ROLE_STOCKER, True, "Helps Pick PPC / JCS", ""),
        Associate("Stocker 7", ROLE_STOCKER, True, "Helps Pick Both", ""),
    ]
    return Team(associates=roster, tasks=default_tasks(), settings=Settings())


def example_day(team: Team) -> Day:
    """A filled-in day in the style of the reference sheet: the picker works
    through the departments while everyone else topstocks, runs what was just
    picked, and one stocker at a time helps pick. Saved as a template on first
    run so there is something to look at and copy from."""

    def t(h: int, m: int = 0) -> int:
        return h * 60 + m

    day = Day(date=date.today())
    for a in team.associates:
        day.set_working(a, True)
    pickers = [a for a in team.associates if a.role == ROLE_PICKER]
    stockers = [a for a in team.associates if a.role != ROLE_PICKER]

    for p in pickers:
        for start, end, task, note in (
            (t(7), t(8, 45), "Topstock", ""),
            (t(8, 45), t(9), "Break", ""),
            (t(9), t(9, 20), "Pick Frozen", "TL helps · ~70 cases"),
            (t(9, 20), t(10), "Pick GM", "~100 cases"),
            (t(10), t(10, 40), "Pick Dairy #1", "~120 cases"),
            (t(10, 40), t(11, 20), "Pick Grocery #1", "~105 cases"),
            (t(11, 20), t(12, 30), "Lunch", ""),
            (t(12, 30), t(13), "Pick HBA", "~155 cases"),
            (t(13), t(13, 40), "Pick Pets / Paper / Chem", "~125 cases"),
            (t(13, 40), t(14, 20), "Pick Juice / Candy / Snacks", "~110 cases"),
            (t(14, 20), t(14, 40), "Pick Dairy #2", "20–40 cases"),
            (t(14, 40), t(15), "Pick Grocery #2", "20–40 cases"),
            (t(15), t(16), "Topstock / Cleanup", ""),
        ):
            day.set_range(p.id, start, end, task, note)

    for s in stockers:
        for start, end, task in (
            (t(7), t(9), "Topstock"),
            (t(9), t(9, 15), "Break"),
            (t(9, 15), t(9, 45), "Run Frozen"),
            (t(10), t(10, 30), "Run GM"),
            (t(10, 40), t(11, 20), "Run Dairy #1"),
            (t(11, 20), t(12), "Run Grocery #1"),
            (t(12), t(13), "Lunch"),
            (t(13), t(13, 40), "Run HBA"),
            (t(13, 40), t(14, 20), "Run Pets"),
            (t(14, 20), t(14, 50), "Run Juice"),
            (t(14, 50), t(16), "Topstock / Cleanup"),
        ):
            day.set_range(s.id, start, end, task)

    # one helper per pick window, rotating through the stockers
    helps = (
        (t(9, 20), t(10), "Help Pick GM"),
        (t(10, 40), t(11, 20), "Help Pick Grocery"),
        (t(12, 30), t(13), "Help Pick HBA"),
        (t(13), t(13, 40), "Help Pick Pets / Paper / Chem"),
        (t(13, 40), t(14, 20), "Help Pick Juice / Candy / Snacks"),
    )
    for i, (start, end, task) in enumerate(helps):
        if not stockers:
            break
        helper = stockers[(i + 3) % len(stockers)]
        day.set_range(helper.id, start, end, task)
        if task == "Help Pick HBA":  # that helper lunches earlier so they're free
            day.set_range(helper.id, t(11, 30), t(12, 30), "Lunch")
            day.set_range(helper.id, t(11, 20), t(11, 30), "Run Grocery #1")
    day.notes = "Example day — edit anything, or Day ▾ → Clear all to start fresh."
    return day
