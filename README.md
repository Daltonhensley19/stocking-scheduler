# Stocking 1 — Daily Pick & Run Scheduler

A desktop app for planning one day of freight for a small stocking team
(picker + stockers). It's the "Daily Freight Pick & Run Schedule" spreadsheet
idea, but you build the day by clicking instead of typing into cells.

## Run it

```sh
uv run stocking-scheduler        # or: uv run python -m scheduler
```

`uv` creates the virtual environment and installs PySide6 + openpyxl the first
time. Everything is saved automatically to the `data/` folder next to this
file (set `STOCKING_SCHEDULER_DATA=/some/folder` to put it elsewhere).

## How the screen is laid out

```
┌ ◀ date ▶ Today │ Assign Task… │ Undo Redo │ Day ▾ │ Print / Export ▾ │ Settings │ Help ┐
├──────────────────┬──────────────────────────────────────────────────────────────────────┤
│ ROSTER           │  Stocking 1 — Daily Freight Pick & Run Schedule                      │
│ ☑ Picker         │  Time │ Picker │ Stocker 1 │ Stocker 2 │ …                           │
│ ☑ Stocker 1      │  7:00 │ Topstock  Topstock   Topstock                                │
│ ☐ Stocker 6 (opt)│  9:00 │ Break     Break      Break                                   │
│                  │  9:15 │ Pick Frozen  Run Frozen  Help Pick…                          │
│ TASKS            │   …                                                                  │
│ ▪ Topstock       │                                                                      │
│ ▪ Run Frozen     │                                                                      │
│ ▪ Help Pick GM   │  Notes: ________________________________________________             │
└──────────────────┴──────────────────────────────────────────────────────────────────────┘
```

## Daily workflow

1. **Who's in** — tick the people working today in the Roster. Each ticked person
   becomes a column. "Core team" ticks everyone who isn't marked optional.
   Double-click a person (or a column header) to set today's duty
   ("Helps Pick GM"), topstock aisles, or a custom shift.
2. **Assign work** — drag over cells in the grid and click a task in the palette
   (or right-click the cells). Touching cells with the same task merge into one
   block. Delete clears cells. Double-click a block to add a note (case counts,
   "Joe helps") or set exact times like 9:20–10:00.
   **Assign Task…** (Ctrl+T) gives one task to several people at once — e.g.
   everyone on Topstock 7:00–9:00.

   Faster editing:
   * **Resize** — drag a block's top or bottom edge (the cursor changes over it).
   * **Move** — select cells, then drag the selection to another time or person.
     Hold Ctrl as you let go to copy instead. Esc cancels a drag.
   * **Copy / cut / paste** — Ctrl+C, Ctrl+X, Ctrl+V. Pasting one person's cells
     while several people are selected gives it to each of them.
   * **Repeat** — Ctrl+D copies the selected block to straight after itself;
     press again to keep going.
   * **Quick keys** — the tasks you use most sit at the top of the palette on
     keys 1–5. A newly used task replaces the one used least recently, so the
     other keys don't move. Right-click one to remove it.
   * **Search** — start typing a task name with the grid focused (or use the
     box above the palette), then press Enter to fill the selection.
3. **Check** — tick **Required** next to any task that must be given to
   someone every day, then press **Check Sheet** (F7) in the toolbar. It lists
   problems such as a Required task nobody working today is assigned.
4. **Reuse** — `Day ▾ → Copy from previous day` or save a good day as a template
   and apply it tomorrow. An "Example day" template is included.
5. **Share** — `Print / Export ▾` prints the board, prints one page per person,
   saves a PDF or PNG (handy for group chats), or exports an Excel workbook with
   the board plus one tab per associate — the same shape as the reference sheet.

Undo/Redo (Ctrl+Z / Ctrl+Shift+Z) covers every change to the day.

## Customizing

* **Tasks** — `New task…` in the palette; double-click a task to rename or
  recolor; right-click to delete. Tasks are grouped into General, Run Freight,
  Help Pick and Picking.
* **Settings** — sheet title, day start/end, grid granularity (10/15/20/30/60
  minutes) and the footer note that prints under the schedule.
* **Roster** — Add/Edit/Remove and ▲▼ to change column order.
* **View** — **Fit Day** in the toolbar shrinks the rows so the whole day fits
  without scrolling (on by default, remembered per computer). Ctrl+mouse wheel
  or Ctrl + / Ctrl − zooms the rows instead; Ctrl+0 resets.

## Files

```
data/
  team.json                 roster, task list, settings
  schedules/2026-09-11.json one file per day
  templates/Example day.json
```

Plain JSON — safe to back up or copy to another machine.

## Handing it to people who don't have Python

### Installers (easiest for Windows and Mac users)

Push this folder to GitHub and push a tag such as `v1.0` —
`.github/workflows/build.yml` builds everything and attaches it to a GitHub
Release (or run the workflow from the Actions tab and grab the files under
"Artifacts"). The tag becomes the version number.

| Download | For | What the person does |
|---|---|---|
| `StockingScheduler-Setup-1.0-windows.exe` | Windows 10/11 | Run it → Next → Install → Finish. No admin password needed. |
| `StockingScheduler-Setup-1.0-macos-arm64.pkg` | Macs with Apple Silicon (M1 and newer) | Open it → Continue → Install (asks for the Mac password). |
| `StockingScheduler-Setup-1.0-macos-intel.pkg` | Older Intel Macs | Same as above. |

* **Windows** — an Inno Setup wizard. It installs for the current user by
  default (no admin rights — handy on locked-down PCs); people who are admins
  can pick "all users". It adds a Start-menu entry, an optional desktop icon, a
  "Launch now" box on the last page and an entry in *Settings → Apps* to
  uninstall. Running a newer setup upgrades in place.
* **macOS** — a standard `.pkg`, so it opens the familiar Installer wizard and
  puts *Stocking Scheduler* in Applications. To uninstall, drag it to the Trash.

**Where installed copies keep schedules:** the user's own folder —
`%LOCALAPPDATA%\StockingScheduler\data` on Windows,
`~/Library/Application Support/StockingScheduler/data` on a Mac (the exact path
is in the app's Help window). Upgrading or uninstalling never deletes it. If
someone switches from the zip download to the installer, copy their old `data`
folder (next to the old program) to that location.

**The installers aren't code-signed**, so the first open shows a warning:
* Windows SmartScreen: *More info → Run anyway* (once, for the setup file).
* Mac: double-clicking the `.pkg` says it "can't be opened". Right-click it →
  *Open* → *Open*; on macOS 15 (Sequoia) and newer, instead go to
  *System Settings → Privacy & Security* and click *Open Anyway*. The installed
  app itself then opens normally.

Removing these warnings needs a paid code-signing certificate (Windows) and an
Apple Developer account for notarization (Mac).

To build an installer yourself, run this on that OS (Windows also needs
[Inno Setup 6](https://jrsoftware.org/isdl.php): `winget install JRSoftware.InnoSetup`):

```sh
uv run --group build python build.py --installer
```

### Portable downloads (no install)

```sh
uv run --group build python build.py            # single file — easiest to hand out
uv run --group build python build.py --onedir   # folder build — starts faster
```

That produces `dist/StockingScheduler` (`.exe` on Windows, `Stocking Scheduler.app`
on a Mac) and a zip/tar in `release/` with `RUNNING.txt` alongside it. The
script launches the result once headlessly to make sure it starts. The GitHub
workflow builds these too, plus the Linux `tar.gz`.

A portable copy keeps its `data` folder **next to the executable** (or in the
user's app-data folder if that location is read-only), so schedules are easy
to find and back up. Put it on a shared drive and everyone who opens it from
there sees the same schedules — the installers can't do that, since each
installed copy keeps its own data.

**PyInstaller builds only for the OS it runs on**, so build Windows files on a
Windows PC (install [uv](https://docs.astral.sh/uv/) first, then
`uv sync --group build` in this folder) or let GitHub Actions do it.

Notes for recipients (also in `RUNNING.txt`):
- The single-file build takes a few seconds to open the first time — it unpacks itself.
- Windows SmartScreen will warn once because the exe isn't code-signed:
  *More info → Run anyway*. On a Mac: right-click → Open the first time.

## Code layout

```
scheduler/
  models.py     dataclasses + JSON (Team, Day, Segment…), no Qt
  storage.py    load/save under data/
  defaults.py   starter roster, tasks and the example day
  checks.py     Check Sheet rules (no Qt) — add new rules to RULES
  export.py     HTML (print/PDF/PNG) and Excel export
  ui/grid.py    the schedule grid (custom-painted merged blocks)
  ui/panels.py  roster + task palette
  ui/dialogs.py assign / block / associate / task / settings dialogs
  ui/main_window.py
  app.py        entry point (`--smoke-test` opens and closes the window, used by build.py)
launcher.py             PyInstaller entry script
StockingScheduler.spec  PyInstaller recipe
build.py                one-command build + package
make_icon.py            regenerates assets/icon.*
installer/windows/      Inno Setup script for the Windows setup wizard
installer/macos/        .pkg wizard layout and its welcome / finish pages
```
