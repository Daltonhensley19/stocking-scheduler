"""JSON persistence. Everything lives under a single data folder:

    data/
      team.json                 roster, tasks, settings
      schedules/YYYY-MM-DD.json one file per day
      templates/<name>.json     reusable day layouts
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import date
from pathlib import Path

from .models import Team, Day
from .defaults import default_team, example_day

APP_NAME = "StockingScheduler"
# Shipped next to the .exe by the Windows installer. An installed copy keeps its
# data in the user's own folder rather than the program folder, so upgrades and
# uninstalls never touch schedules; a copy unzipped by hand stays portable.
INSTALLED_MARKER = "installed-by-setup.txt"


def is_frozen() -> bool:
    """True when running from a PyInstaller build."""
    return bool(getattr(sys, "frozen", False))


def _writable(folder: Path) -> bool:
    try:
        folder.mkdir(parents=True, exist_ok=True)
        probe = folder / ".write-test"
        probe.write_text("ok")
        probe.unlink()
        return True
    except OSError:
        return False


def user_data_dir() -> Path:
    """Per-user application data folder for this OS."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
        return Path(base) / APP_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / APP_NAME


def data_dir() -> Path:
    """Where schedules are stored.

    1. STOCKING_SCHEDULER_DATA environment variable, if set.
    2. Installed with the Windows installer, or on macOS (the .app bundle should
       not be written into): the per-user app-data folder.
    3. Packaged app unzipped by hand (Windows/Linux): a `data` folder next to the
       executable, so people can see and back it up (and share it from a network
       drive) — falling back to the per-user folder when that spot is read-only.
    4. Running from source: `data/` next to pyproject.toml.
    """
    env = os.environ.get("STOCKING_SCHEDULER_DATA")
    if env:
        return Path(env).expanduser()
    if is_frozen():
        exe_dir = Path(sys.executable).resolve().parent
        if sys.platform != "darwin" and not (exe_dir / INSTALLED_MARKER).exists():
            beside = exe_dir / "data"
            if _writable(beside):
                return beside
        return user_data_dir() / "data"
    return Path(__file__).resolve().parent.parent / "data"


class Storage:
    def __init__(self, root: Path | None = None):
        self.root = root or data_dir()
        self.schedules = self.root / "schedules"
        self.templates = self.root / "templates"
        for p in (self.root, self.schedules, self.templates):
            p.mkdir(parents=True, exist_ok=True)

    # --- helpers ------------------------------------------------------------
    @staticmethod
    def _write(path: Path, obj: dict) -> None:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(obj, indent=2), encoding="utf-8")
        tmp.replace(path)

    @staticmethod
    def _read(path: Path) -> dict | None:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    # --- team ---------------------------------------------------------------
    @property
    def team_path(self) -> Path:
        return self.root / "team.json"

    def load_team(self) -> Team:
        d = self._read(self.team_path)
        if d is None:
            team = default_team()
            self.save_team(team)
            self._first_run(team)
            return team
        return Team.from_dict(d)

    def _first_run(self, team: Team) -> None:
        """Seed an example so the first launch shows a real-looking schedule."""
        example = example_day(team)
        self.save_template("Example day", example)
        if not self.has_day(example.date):
            self.save_day(example)

    def save_team(self, team: Team) -> None:
        self._write(self.team_path, team.to_dict())

    # --- days ---------------------------------------------------------------
    def day_path(self, d: date) -> Path:
        return self.schedules / f"{d.isoformat()}.json"

    def has_day(self, d: date) -> bool:
        return self.day_path(d).exists()

    def load_day(self, d: date) -> Day:
        data = self._read(self.day_path(d))
        if data is None:
            return Day(date=d)
        return Day.from_dict(data)

    def save_day(self, day: Day) -> None:
        self._write(self.day_path(day.date), day.to_dict())

    def rename_task(self, old: str, new: str) -> None:
        """Rename a task in every saved day and template."""
        for path in [*self.schedules.glob("*.json"), *self.templates.glob("*.json")]:
            data = self._read(path)
            if data is None:
                continue
            try:
                day = Day.from_dict(data)
            except (KeyError, TypeError, ValueError):
                continue  # not a schedule file we understand; leave it alone
            if day.rename_task(old, new):
                self._write(path, day.to_dict())

    def saved_dates(self) -> list[date]:
        out = []
        for p in self.schedules.glob("*.json"):
            try:
                out.append(date.fromisoformat(p.stem))
            except ValueError:
                pass
        return sorted(out, reverse=True)

    # --- templates ----------------------------------------------------------
    @staticmethod
    def _safe_name(name: str) -> str:
        return re.sub(r"[^A-Za-z0-9 _-]+", "", name).strip() or "template"

    def template_names(self) -> list[str]:
        return sorted(p.stem for p in self.templates.glob("*.json"))

    def save_template(self, name: str, day: Day) -> None:
        self._write(self.templates / f"{self._safe_name(name)}.json", day.to_dict())

    def load_template(self, name: str) -> Day | None:
        d = self._read(self.templates / f"{self._safe_name(name)}.json")
        return Day.from_dict(d) if d else None

    def delete_template(self, name: str) -> None:
        p = self.templates / f"{self._safe_name(name)}.json"
        if p.exists():
            p.unlink()
