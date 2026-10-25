# Stocking 1 — Daily Pick & Run Scheduler

A desktop app for planning one day of freight for a small stocking team
(picker + stockers). It's the "Daily Freight Pick & Run Schedule" spreadsheet
idea, but you build the day by clicking instead of typing into cells — then
print it, save it as a PDF or picture for the group chat, or export it to Excel.

It's free, works without an internet connection, and saves your work
automatically.

## Download & install

**Pick the download for your computer:**

| Your computer | Download |
|---|---|
| 🪟 **Windows 10 or 11** | **[⬇ Download for Windows](https://github.com/Daltonhensley19/stocking-scheduler/releases/latest/download/StockingScheduler-Setup-windows.exe)** |
| 🍎 **Mac with an Apple chip** (M1, M2, M3, M4…) | **[⬇ Download for Apple-chip Mac](https://github.com/Daltonhensley19/stocking-scheduler/releases/latest/download/StockingScheduler-Setup-macos-arm64.pkg)** |
| 🍎 **Mac with an Intel chip** (older Macs) | **[⬇ Download for Intel Mac](https://github.com/Daltonhensley19/stocking-scheduler/releases/latest/download/StockingScheduler-Setup-macos-intel.pkg)** |

All versions are also on the **[Releases page](https://github.com/Daltonhensley19/stocking-scheduler/releases/latest)**.

> **Not sure which Mac you have?** Click the **Apple logo** in the top-left
> corner of the screen → **About This Mac**. If the line says **Chip: Apple M…**, get the
> Apple-chip download. If it says **Processor: … Intel …**, get the Intel one.

### Installing on Windows

1. Click **Download for Windows** above.
2. Your browser may say the file *"isn't commonly downloaded"*. That's because
   the app is new, not because something is wrong. In **Edge**: click the
   **⋯** next to the download → **Keep** → **Show more** → **Keep anyway**.
   In **Chrome**: click **Keep**.
3. Open the downloaded file (**StockingScheduler-Setup-windows.exe**).
4. A blue box may say **"Windows protected your PC."** Click **More info**, then
   **Run anyway**. (This only happens once, because the app isn't from a big
   company that pays Microsoft to vouch for it.)
5. The setup wizard opens. Click **Next** → **Install** → **Finish**.
   You **don't** need an administrator password.
6. Stocking Scheduler opens. Next time, find it in the **Start menu** (or on
   your desktop, if you ticked "Create a desktop shortcut").

### Installing on a Mac

1. Click the right Mac download above (see *"Not sure which Mac you have?"*).
2. Open your **Downloads** folder and double-click the **.pkg** file.
3. The Mac will probably say the file **"can't be opened"** or is from an
   **"unidentified developer."** That's because the app isn't registered with
   Apple, not because something is wrong. To open it anyway:
   * **macOS 15 (Sequoia) or newer:** click **Done**, open **System Settings**
     → **Privacy & Security**, scroll down, and click **Open Anyway** next to
     the message about StockingScheduler. Enter your Mac password if asked.
   * **Older macOS:** hold **Control** and click the .pkg file → choose
     **Open** → click **Open** again.
4. The installer opens. Click **Continue** → **Install**, and type your Mac
   password when asked (that's normal for anything added to Applications).
5. Click **Close** when it finishes. Open **Stocking Scheduler** from
   **Launchpad** or your **Applications** folder. It opens normally from now on.

### Updating to a new version

Download the newest version from the links above and install it the same way.
It replaces the old version, and **all your schedules are kept**.

### Uninstalling

* **Windows:** Start menu → **Settings** → **Apps** → find **Stocking
  Scheduler** → **Uninstall**.
* **Mac:** open **Applications** and drag **Stocking Scheduler** to the
  **Trash**.

Either way, your schedules are **not** deleted (see below), so reinstalling
brings everything back.

### Your schedules

Everything is saved automatically as you work — there's no Save button.
Your schedules live in your own user folder:

* **Windows:** `%LOCALAPPDATA%\StockingScheduler\data` — paste that into the
  File Explorer address bar to open it.
* **Mac:** `~/Library/Application Support/StockingScheduler/data` — in Finder,
  choose **Go → Go to Folder…** and paste it.

The exact location is also shown at the bottom of the app's **Help** window.
To **back up** or **move to another computer**, copy that whole `data` folder
to the same place on the other computer.

### Something not working?

* **The app won't open after installing (Mac):** open **System Settings →
  Privacy & Security** and look for an **Open Anyway** button for Stocking
  Scheduler.
* **Text looks tiny or the grid is cramped:** click **Fit Day** in the toolbar
  to switch it off, or hold **Ctrl** and scroll to zoom the rows.
* **Something else:** [open an issue](https://github.com/Daltonhensley19/stocking-scheduler/issues) describing what happened.

---

# Using the app

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

## What's in the data folder

```
data/
  team.json                 roster, task list, settings
  schedules/2026-09-11.json one file per day
  templates/Example day.json
```

Plain JSON — safe to back up or copy to another machine.

---

# For developers

## Run from source

```sh
uv run stocking-scheduler        # or: uv run python -m scheduler
```

`uv` creates the virtual environment and installs PySide6 + openpyxl the first
time. When run from source, everything is saved to the `data/` folder next to
this file (set `STOCKING_SCHEDULER_DATA=/some/folder` to put it elsewhere).

## Building the downloads

**Releases are built by GitHub Actions** (`.github/workflows/build.yml`). Push a
tag such as `v1.1` and it builds every download and publishes a Release; the
tag becomes the version number. (Run the workflow from the Actions tab instead
to get the files under "Artifacts" without publishing.)

| File | What it is |
|---|---|
| `StockingScheduler-Setup-windows.exe` | Windows setup wizard (Inno Setup) — per-user install, no admin needed |
| `StockingScheduler-Setup-macos-arm64.pkg` / `-macos-intel.pkg` | macOS Installer package → /Applications |
| `StockingScheduler-windows.zip`, `-macos-*.zip`, `-linux.tar.gz` | Portable copies, no install |

The installer file names have no version number on purpose, so the
`releases/latest/download/…` links above always fetch the newest one.

**Data location.** Installed copies keep schedules in the user's app-data
folder, so upgrades and uninstalls never touch them (the Windows installer drops
an `installed-by-setup.txt` marker next to the exe to signal this). A portable
copy keeps its `data` folder **next to the executable** instead — put it on a
shared drive and everyone who opens it from there sees the same schedules.

**Signing.** Nothing is code-signed, which is why users see the SmartScreen /
Gatekeeper warnings described above. Removing them needs a Windows
code-signing certificate and an Apple Developer account (for notarization).

**Building locally.** PyInstaller builds only for the OS it runs on. On that OS
(install [uv](https://docs.astral.sh/uv/), then `uv sync --group build`):

```sh
uv run --group build python build.py               # portable single file
uv run --group build python build.py --onedir      # portable folder (starts faster)
uv run --group build python build.py --installer   # setup wizard (Windows / macOS)
```

The Windows installer also needs [Inno Setup 6](https://jrsoftware.org/isdl.php)
(`winget install JRSoftware.InnoSetup`). Output goes to `release/`, and the
script launches the built app once headlessly to make sure it starts.

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
