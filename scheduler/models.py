"""Data model for the daily pick & run schedule.

Everything here is plain Python (no Qt) so it can be saved/loaded as JSON
and reused by the export code.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import date

ROLE_PICKER = "Picker"
ROLE_STOCKER = "Stocker"
ROLES = (ROLE_PICKER, ROLE_STOCKER)

# Task categories, used to group the palette and pick default colors.
CAT_GENERAL = "General"
CAT_RUN = "Run Freight"
CAT_HELP = "Help Pick"
CAT_PICK = "Picking"
CATEGORIES = (CAT_GENERAL, CAT_RUN, CAT_HELP, CAT_PICK)

CATEGORY_COLORS = {
    CAT_GENERAL: "#d0dcea",
    CAT_RUN: "#cdebd6",
    CAT_HELP: "#fff0b3",
    CAT_PICK: "#e0d4f5",
}


def minutes_to_label(m: int, ampm: bool = False) -> str:
    """480 -> '8:00' (or '8:00 AM' when ampm=True)."""
    h, mm = divmod(m, 60)
    suffix = ""
    if ampm:
        suffix = " AM" if h < 12 else " PM"
    h12 = h % 12
    if h12 == 0:
        h12 = 12
    return f"{h12}:{mm:02d}{suffix}"


def label_to_minutes(text: str) -> int | None:
    """Parse '7:00', '7:00 AM', '13:30', '1:30 PM', '7' into minutes since midnight."""
    t = text.strip().upper().replace(".", "")
    if not t:
        return None
    pm = t.endswith("PM")
    am = t.endswith("AM")
    if pm or am:
        t = t[:-2].strip()
    if ":" in t:
        hs, ms = t.split(":", 1)
    else:
        hs, ms = t, "0"
    try:
        h, m = int(hs), int(ms)
    except ValueError:
        return None
    if pm and h < 12:
        h += 12
    if am and h == 12:
        h = 0
    if not (0 <= h < 24 and 0 <= m < 60):
        return None
    return h * 60 + m


@dataclass
class Task:
    name: str
    category: str = CAT_GENERAL
    color: str = ""  # hex, empty -> category default
    required: bool = False  # someone working must be assigned it at least once (see checks.py)

    def effective_color(self) -> str:
        return self.color or CATEGORY_COLORS.get(self.category, "#e6e6e6")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Task":
        return cls(
            name=d["name"],
            category=d.get("category", CAT_GENERAL),
            color=d.get("color", ""),
            required=bool(d.get("required", False)),
        )


@dataclass
class Associate:
    """A member of the team (persistent across days)."""

    name: str
    role: str = ROLE_STOCKER
    optional: bool = False  # e.g. "Stocker 6 (Optional)"
    duty: str = ""  # secondary duty, e.g. "Helps Pick GM"
    aisles: str = ""  # default topstock aisles, e.g. "A18/A19"
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Associate":
        return cls(
            name=d["name"],
            role=d.get("role", ROLE_STOCKER),
            optional=bool(d.get("optional", False)),
            duty=d.get("duty", ""),
            aisles=d.get("aisles", ""),
            id=d.get("id") or uuid.uuid4().hex[:8],
        )


@dataclass
class Segment:
    """One block of time on one associate's day: [start, end) in minutes."""

    start: int
    end: int
    task: str
    note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Segment":
        return cls(int(d["start"]), int(d["end"]), d["task"], d.get("note", ""))


@dataclass
class DayAssociate:
    """Per-day info for an associate who is working that day."""

    id: str
    duty: str = ""
    aisles: str = ""
    shift_start: int | None = None  # minutes; None = whole day
    shift_end: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "DayAssociate":
        return cls(
            id=d["id"],
            duty=d.get("duty", ""),
            aisles=d.get("aisles", ""),
            shift_start=d.get("shift_start"),
            shift_end=d.get("shift_end"),
        )


@dataclass
class Settings:
    title: str = "Stocking 1 — Daily Freight Pick & Run Schedule"
    day_start: int = 7 * 60
    day_end: int = 16 * 60
    slot_minutes: int = 15
    footer: str = (
        "GM = GM rolling bins, GM receiving, automotive, B2 room and the 15 room. "
        "Expectation is 95%+ pick rate and 45 cases ran per hour per person."
    )
    quick_tasks: list[str] = field(default_factory=list)  # palette's number-key tasks

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Settings":
        s = cls()
        for k in s.__dict__:
            if k in d:
                setattr(s, k, d[k])
        return s

    def slots(self) -> list[int]:
        """Start minute of every row in the grid."""
        return list(range(self.day_start, self.day_end, self.slot_minutes))


@dataclass
class Team:
    """Persistent data: roster, tasks and settings."""

    associates: list[Associate] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)
    settings: Settings = field(default_factory=Settings)

    def get(self, assoc_id: str) -> Associate | None:
        for a in self.associates:
            if a.id == assoc_id:
                return a
        return None

    def task(self, name: str) -> Task | None:
        for t in self.tasks:
            if t.name == name:
                return t
        return None

    def task_color(self, name: str) -> str:
        t = self.task(name)
        return t.effective_color() if t else "#e6e6e6"

    def to_dict(self) -> dict:
        return {
            "associates": [a.to_dict() for a in self.associates],
            "tasks": [t.to_dict() for t in self.tasks],
            "settings": self.settings.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Team":
        return cls(
            associates=[Associate.from_dict(x) for x in d.get("associates", [])],
            tasks=[Task.from_dict(x) for x in d.get("tasks", [])],
            settings=Settings.from_dict(d.get("settings", {})),
        )


@dataclass
class Day:
    """One day's schedule."""

    date: date
    working: list[DayAssociate] = field(default_factory=list)
    segments: dict[str, list[Segment]] = field(default_factory=dict)  # assoc id -> segments
    notes: str = ""

    # --- working associates -------------------------------------------------
    def is_working(self, assoc_id: str) -> bool:
        return any(w.id == assoc_id for w in self.working)

    def day_assoc(self, assoc_id: str) -> DayAssociate | None:
        for w in self.working:
            if w.id == assoc_id:
                return w
        return None

    def set_working(self, assoc: Associate, on: bool) -> None:
        if on and not self.is_working(assoc.id):
            self.working.append(DayAssociate(id=assoc.id, duty=assoc.duty, aisles=assoc.aisles))
        elif not on:
            self.working = [w for w in self.working if w.id != assoc.id]

    def order_working(self, ordered_ids: list[str]) -> None:
        """Keep the day's working list in roster order."""
        index = {aid: i for i, aid in enumerate(ordered_ids)}
        self.working.sort(key=lambda w: index.get(w.id, 10**6))

    # --- segments -----------------------------------------------------------
    def segs(self, assoc_id: str) -> list[Segment]:
        return self.segments.setdefault(assoc_id, [])

    def task_at(self, assoc_id: str, minute: int) -> Segment | None:
        for s in self.segments.get(assoc_id, []):
            if s.start <= minute < s.end:
                return s
        return None

    def set_range(self, assoc_id: str, start: int, end: int, task: str | None, note: str = "") -> None:
        """Assign `task` to [start, end) for one associate, replacing whatever was there.
        task=None clears the range."""
        if end <= start:
            return
        old = self.segments.get(assoc_id, [])
        new: list[Segment] = []
        for s in old:
            if s.end <= start or s.start >= end:
                new.append(s)  # untouched
                continue
            # overlap -> keep the parts outside [start, end)
            if s.start < start:
                new.append(Segment(s.start, start, s.task, s.note))
            if s.end > end:
                new.append(Segment(end, s.end, s.task, s.note))
        if task:
            new.append(Segment(start, end, task, note))
        new.sort(key=lambda s: s.start)
        self.segments[assoc_id] = self._merge(new)

    @staticmethod
    def _merge(segs: list[Segment]) -> list[Segment]:
        """Join touching segments with the same task+note."""
        out: list[Segment] = []
        for s in segs:
            if out and out[-1].end == s.start and out[-1].task == s.task and out[-1].note == s.note:
                out[-1].end = s.end
            else:
                out.append(Segment(s.start, s.end, s.task, s.note))
        return out

    def extract(self, assoc_id: str, start: int, end: int) -> list[Segment]:
        """Copies of what's assigned in [start, end), clipped to it and with
        times made relative to `start` — the shape `put` takes back."""
        out: list[Segment] = []
        for s in self.segments.get(assoc_id, []):
            a, b = max(s.start, start), min(s.end, end)
            if a < b:
                out.append(Segment(a - start, b - start, s.task, s.note))
        return out

    def put(self, assoc_id: str, at: int, length: int, segs: list[Segment]) -> None:
        """Replace [at, at + length) with `segs` (relative times, as from `extract`)."""
        self.set_range(assoc_id, at, at + length, None)
        for s in segs:
            self.set_range(assoc_id, at + s.start, at + min(s.end, length), s.task, s.note)

    def clear_all(self) -> None:
        self.segments = {}

    def rename_task(self, old: str, new: str) -> bool:
        """Rename every block using task `old`. Returns True if anything changed."""
        changed = False
        for segs in self.segments.values():
            for s in segs:
                if s.task == old:
                    s.task = new
                    changed = True
        return changed

    # --- serialization ------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "date": self.date.isoformat(),
            "working": [w.to_dict() for w in self.working],
            "segments": {k: [s.to_dict() for s in v] for k, v in self.segments.items() if v},
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Day":
        return cls(
            date=date.fromisoformat(d["date"]),
            working=[DayAssociate.from_dict(x) for x in d.get("working", [])],
            segments={k: [Segment.from_dict(s) for s in v] for k, v in d.get("segments", {}).items()},
            notes=d.get("notes", ""),
        )

    def copy_for(self, new_date: date) -> "Day":
        return Day.from_dict({**self.to_dict(), "date": new_date.isoformat()})


def working_associates(team: Team, day: Day) -> list[tuple[Associate, DayAssociate]]:
    """Associates working on `day`, in roster order (pickers first)."""
    out: list[tuple[Associate, DayAssociate]] = []
    for a in team.associates:
        w = day.day_assoc(a.id)
        if w is not None:
            out.append((a, w))
    out.sort(key=lambda p: 0 if p[0].role == ROLE_PICKER else 1)
    return out


@dataclass
class Run:
    """A vertical block of consecutive grid rows that share one segment."""

    row: int
    rows: int
    segment: Segment
    start: int  # minute of first slot
    end: int  # minute after last slot


def column_runs(day: Day, assoc_id: str, slots: list[int], slot_minutes: int) -> list[Run]:
    """Group the grid rows of one associate into runs of the same segment.
    Rows with nothing assigned are not returned."""
    segs = day.segments.get(assoc_id, [])

    def overlap(seg: Segment, start: int) -> int:
        return min(start + slot_minutes, seg.end) - max(start, seg.start)

    # A row shows the segment covering most of it (the later one on a tie), so
    # times that don't line up with the grid (e.g. 10:40 on a 15-minute grid)
    # still land on the nearest rows.
    owner: list[Segment | None] = []
    for start in slots:
        best, best_ov = None, 0
        for seg in segs:
            ov = overlap(seg, start)
            if ov > 0 and ov >= best_ov:
                best, best_ov = seg, ov
        owner.append(best)

    # A block shorter than a row (e.g. 9:00-9:05 on a 15-minute grid) can lose
    # every row it touches and vanish. Give it the row it overlaps most, as long
    # as that doesn't hide the row's current owner as well.
    rows_owned: dict[int, int] = {}
    for seg in owner:
        if seg is not None:
            rows_owned[id(seg)] = rows_owned.get(id(seg), 0) + 1
    for seg in segs:
        if rows_owned.get(id(seg)):
            continue
        best_row, best_ov = None, 0
        for i, start in enumerate(slots):
            ov = overlap(seg, start)
            cur = owner[i]
            if ov > best_ov and (cur is None or rows_owned[id(cur)] > 1):
                best_row, best_ov = i, ov
        if best_row is not None:
            cur = owner[best_row]
            if cur is not None:
                rows_owned[id(cur)] -= 1
            owner[best_row] = seg
            rows_owned[id(seg)] = 1

    runs: list[Run] = []
    current: Run | None = None
    for i, (start, seg) in enumerate(zip(slots, owner)):
        if seg is None:
            current = None
            continue
        if current is not None and current.segment is seg:
            current.rows += 1
            current.end = start + slot_minutes
        else:
            current = Run(i, 1, seg, start, start + slot_minutes)
            runs.append(current)
    return runs
