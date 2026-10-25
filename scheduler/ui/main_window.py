"""Main window: toolbar, roster + palette on the left, the schedule grid on the right."""

from __future__ import annotations

import copy
from datetime import date, datetime, timedelta
from html import escape

from PySide6.QtCore import Qt, QDate, QSettings, QTimer, QSize, QMarginsF
from PySide6.QtGui import QAction, QKeySequence, QPainter, QImage, QColor, QPageLayout, QTextDocument
from PySide6.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PySide6.QtWidgets import (
    QDateEdit,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..models import Team, Day, Associate, Segment, CATEGORIES, minutes_to_label
from ..storage import Storage
from .. import export as ex
from ..checks import find_violations
from .grid import ScheduleGrid
from .panels import RosterPanel, TaskPalette, QUICK_KEYS
from .dialogs import (
    AssignDialog,
    BlockDialog,
    AssociateDialog,
    DayAssociateDialog,
    TaskDialog,
    SettingsDialog,
    pick_from_list,
    ask_text,
)


def qdate(d: date) -> QDate:
    return QDate(d.year, d.month, d.day)


def pydate(q: QDate) -> date:
    return date(q.year(), q.month(), q.day())


class MainWindow(QMainWindow):
    def __init__(self, storage: Storage):
        super().__init__()
        self.storage = storage
        self.team: Team = storage.load_team()
        self.day: Day = self._load_day(date.today())
        self._touched = False
        self._undo: list[dict] = []
        self._redo: list[dict] = []
        # Copied cells: [(column offset, minutes offset, length, segments)], relative
        # to the top-left of what was copied.
        self._clipboard: list[tuple[int, int, int, list[Segment]]] = []
        # Quick-key tasks, least recently used first (this session); a new task
        # replaces the least recent one so the other keys stay put.
        self._quick_use: list[str] = list(reversed(self.team.settings.quick_tasks))

        self.setWindowTitle("Stocking 1 — Daily Pick & Run Scheduler")
        self.resize(1380, 860)

        self._build_toolbar()
        self._build_body()
        self._build_statusbar()

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(500)
        self._save_timer.timeout.connect(self.save_now)

        self._clock = QTimer(self)
        self._clock.setInterval(30_000)
        self._clock.timeout.connect(self._tick)
        self._clock.start()

        self._bind_all()
        self._tick()

    # ------------------------------------------------------------------ build
    def _build_toolbar(self) -> None:
        tb = QToolBar("Main")
        tb.setMovable(False)
        tb.setIconSize(QSize(18, 18))
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.addToolBar(tb)

        self.prev_act = QAction("◀", self, triggered=lambda: self.shift_day(-1))
        self.prev_act.setToolTip("Previous day")
        self.next_act = QAction("▶", self, triggered=lambda: self.shift_day(+1))
        self.next_act.setToolTip("Next day")
        self.date_edit = QDateEdit(qdate(self.day.date))
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("ddd  MMM d, yyyy")
        self.date_edit.dateChanged.connect(lambda q: self.go_to(pydate(q)))
        today_act = QAction("Today", self, triggered=lambda: self.go_to(date.today()))

        tb.addAction(self.prev_act)
        tb.addWidget(self.date_edit)
        tb.addAction(self.next_act)
        tb.addAction(today_act)
        tb.addSeparator()

        assign_act = QAction("Assign Task…", self, triggered=self.open_assign_dialog)
        assign_act.setShortcut(QKeySequence("Ctrl+T"))
        assign_act.setToolTip("Give a task to one or more people over a time range (Ctrl+T)")
        tb.addAction(assign_act)

        self.undo_act = QAction("Undo", self, triggered=self.undo)
        self.undo_act.setShortcut(QKeySequence.StandardKey.Undo)
        self.redo_act = QAction("Redo", self, triggered=self.redo)
        self.redo_act.setShortcut(QKeySequence.StandardKey.Redo)
        tb.addAction(self.undo_act)
        tb.addAction(self.redo_act)
        tb.addSeparator()

        # Day menu: copy / templates / clear
        day_menu = QMenu("Day", self)
        day_menu.addAction("Copy from previous day", self.copy_previous_day)
        day_menu.addAction("Copy from another date…", self.copy_from_date)
        day_menu.addSeparator()
        day_menu.addAction("Apply template…", self.apply_template)
        day_menu.addAction("Save today as template…", self.save_template)
        day_menu.addAction("Delete template…", self.delete_template)
        day_menu.addSeparator()
        day_menu.addAction("Clear all assignments", self.clear_all)
        tb.addWidget(self._menu_button("Day ▾", day_menu))

        share_menu = QMenu("Share", self)
        share_menu.addAction("Print schedule board…", lambda: self.print_html(ex.board_html(self.team, self.day), landscape=True))
        share_menu.addAction("Print one page per person…", lambda: self.print_html(ex.all_people_html(self.team, self.day)))
        share_menu.addSeparator()
        share_menu.addAction("Save board as PDF…", lambda: self.save_pdf(ex.board_html(self.team, self.day), "schedule", True))
        share_menu.addAction("Save per-person pages as PDF…", lambda: self.save_pdf(ex.all_people_html(self.team, self.day), "per-person", False))
        share_menu.addAction("Save board as image (PNG)…", self.save_png)
        share_menu.addAction("Export to Excel (.xlsx)…", self.export_excel)
        tb.addWidget(self._menu_button("Print / Export ▾", share_menu))
        tb.addSeparator()

        check_act = QAction("Check Sheet", self, triggered=self.check_sheet)
        check_act.setShortcut(QKeySequence("F7"))
        check_act.setToolTip("Look for problems in today's schedule, e.g. a Required task nobody is assigned (F7)")
        tb.addAction(check_act)
        self.addAction(check_act)
        self.fit_act = QAction("Fit Day", self, checkable=True)
        self.fit_act.setToolTip("Shrink the rows so the whole day fits without scrolling.\n"
                                "Ctrl+mouse wheel (or Ctrl + / Ctrl −) zooms instead; Ctrl+0 resets.")
        tb.addAction(self.fit_act)
        tb.addSeparator()

        settings_act = QAction("Settings…", self, triggered=self.open_settings)
        tb.addAction(settings_act)
        help_act = QAction("Help", self, triggered=self.show_help)
        tb.addAction(help_act)

        self.addAction(self.undo_act)
        self.addAction(self.redo_act)
        self.addAction(assign_act)

    def _menu_button(self, text: str, menu: QMenu) -> QToolButton:
        b = QToolButton()
        b.setText(text)
        b.setMenu(menu)
        b.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        return b

    def _build_body(self) -> None:
        self.roster = RosterPanel()
        self.palette_panel = TaskPalette()
        left = QSplitter(Qt.Orientation.Vertical)
        left.addWidget(self.roster)
        left.addWidget(self.palette_panel)
        left.setSizes([230, 570])  # one-line roster rows need less room; give it to the palette

        # One line: sheet title, then the date and head count in lighter type
        self.banner = QLabel()
        self.banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.banner.setTextFormat(Qt.TextFormat.RichText)
        self.banner.setStyleSheet("QLabel { background: #0b2a4a; color: white; font-size: 13pt; padding: 5px; }")

        self.grid = ScheduleGrid()
        self.notes = QLineEdit()
        self.notes.setPlaceholderText("Notes for today (printed under the schedule)…")
        self.notes.textEdited.connect(self._notes_edited)
        notes_row = QHBoxLayout()
        notes_row.addWidget(QLabel("Notes:"))
        notes_row.addWidget(self.notes, 1)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)
        rl.addWidget(self.banner)
        rl.addWidget(self.grid, 1)
        rl.addSpacing(6)
        rl.addLayout(notes_row)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(left)
        split.addWidget(right)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([330, 1050])

        wrap = QWidget()
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(6, 6, 6, 6)
        wl.addWidget(split)
        self.setCentralWidget(wrap)

        # wiring
        self.roster.working_toggled.connect(self.set_working)
        self.roster.add_requested.connect(self.add_associate)
        self.roster.edit_requested.connect(self.edit_associate)
        self.roster.remove_requested.connect(self.remove_associate)
        self.roster.move_requested.connect(self.move_associate)
        self.roster.day_details_requested.connect(self.edit_day_details)
        self.palette_panel.task_clicked.connect(self._palette_task)
        self.palette_panel.forget_quick.connect(self.forget_quick_task)
        self.palette_panel.required_toggled.connect(self.set_task_required)
        self.palette_panel.search_done.connect(self.grid.setFocus)
        self.palette_panel.new_task.connect(self.new_task)
        self.palette_panel.edit_task.connect(self.edit_task)
        self.palette_panel.delete_task.connect(self.delete_task)
        self.palette_panel.clear_clicked.connect(self.clear_selection)
        self.grid.clear_requested.connect(self.clear_selection)
        self.grid.cell_activated.connect(self.edit_block)
        self.grid.header_edit.connect(self.edit_day_details)
        self.grid.context_requested.connect(self.grid_context_menu)
        self.grid.selection_summary.connect(self._selection_status)
        self.grid.block_resized.connect(self.resize_block)
        self.grid.cells_moved.connect(self.move_cells)
        self.grid.copy_requested.connect(self.copy_cells)
        self.grid.cut_requested.connect(self.cut_cells)
        self.grid.paste_requested.connect(self.paste_cells)
        self.grid.repeat_requested.connect(self.repeat_cells)
        self.grid.quick_task.connect(self.apply_quick_task)
        self.grid.type_search.connect(self.palette_panel.start_search)

    def _build_statusbar(self) -> None:
        sb = QStatusBar()
        self.setStatusBar(sb)
        self.sel_label = QLabel("")
        self.save_label = QLabel("")
        sb.addWidget(self.sel_label, 1)
        sb.addPermanentWidget(self.save_label)

        # View preferences belong to this computer, not the shared data folder
        self.prefs = QSettings("StockingScheduler", "StockingScheduler")
        self.grid.set_fit_day(self.prefs.value("view/fit_day", True, type=bool))
        self.fit_act.setChecked(self.grid.fit_day)
        self.fit_act.toggled.connect(self.grid.set_fit_day)
        self.grid.fit_changed.connect(self._fit_changed)

    def _fit_changed(self, on: bool) -> None:
        self.fit_act.setChecked(on)  # Ctrl+wheel zoom switches Fit Day off
        self.prefs.setValue("view/fit_day", on)

    # ------------------------------------------------------------- data flow
    def _load_day(self, d: date) -> Day:
        if self.storage.has_day(d):
            return self.storage.load_day(d)
        day = Day(date=d)
        for a in self.team.associates:  # new day: assume the core team is in
            if not a.optional:
                day.set_working(a, True)
        return day

    def _bind_all(self) -> None:
        """Push the current team/day into every widget."""
        self.day.order_working([a.id for a in self.team.associates])
        self.roster.set_data(self.team, self.day)
        self.palette_panel.set_team(self.team)
        self.grid.set_data(self.team, self.day)
        self.notes.setText(self.day.notes)
        n = len(self.day.working)
        when = self.day.date.strftime("%A, %B %d, %Y").replace(" 0", " ")
        self.banner.setText(
            f"<b>{escape(self.team.settings.title)}</b>"
            f"<span style='color:#c9d6e3; font-size:11pt;'>&nbsp;&nbsp;&nbsp;·&nbsp;&nbsp;&nbsp;{when}"
            f"&nbsp;&nbsp;·&nbsp;&nbsp;{n} working</span>"
        )
        self.date_edit.blockSignals(True)
        self.date_edit.setDate(qdate(self.day.date))
        self.date_edit.blockSignals(False)
        self._update_undo_actions()

    def _tick(self) -> None:
        now = datetime.now()
        self.grid.now_minute = now.hour * 60 + now.minute if self.day.date == date.today() else None
        self.grid.viewport().update()

    def _selection_status(self, text: str) -> None:
        self.sel_label.setText(
            text or "Tip: drag over cells, then click a task (or press 1–5, or type its name). "
            "Drag a block's edge to resize it; drag selected cells to move them."
        )

    # --- saving ---------------------------------------------------------------
    def mark_dirty(self) -> None:
        self._touched = True
        self.save_label.setText("Saving…")
        self._save_timer.start()

    def save_now(self) -> None:
        # Only write a day file once the user has actually changed something
        # (or one already exists) — otherwise flipping through dates would
        # create empty files for every date passed over.
        if self._touched or self.storage.has_day(self.day.date):
            self.storage.save_day(self.day)
        self.storage.save_team(self.team)
        self.save_label.setText(f"Saved {datetime.now().strftime('%I:%M %p').lstrip('0')}")

    def closeEvent(self, event) -> None:
        self._save_timer.stop()
        self.save_now()
        super().closeEvent(event)

    # --- undo -------------------------------------------------------------------
    def snapshot(self) -> None:
        self._undo.append(self.day.to_dict())
        if len(self._undo) > 200:
            self._undo.pop(0)
        self._redo.clear()
        self._update_undo_actions()

    def undo(self) -> None:
        if not self._undo:
            return
        self._redo.append(self.day.to_dict())
        self.day = Day.from_dict(self._undo.pop())
        self._after_day_mutation(rebuild=True)

    def redo(self) -> None:
        if not self._redo:
            return
        self._undo.append(self.day.to_dict())
        self.day = Day.from_dict(self._redo.pop())
        self._after_day_mutation(rebuild=True)

    def _update_undo_actions(self) -> None:
        self.undo_act.setEnabled(bool(self._undo))
        self.redo_act.setEnabled(bool(self._redo))

    def _after_day_mutation(self, rebuild: bool = False) -> None:
        if rebuild:
            self._bind_all()
        else:
            self.grid.refresh()
        self._update_undo_actions()
        self.mark_dirty()

    # --------------------------------------------------------------- navigation
    def go_to(self, d: date) -> None:
        if d == self.day.date:
            return
        self._save_timer.stop()
        self.save_now()
        self.day = self._load_day(d)
        self._touched = False
        self._undo.clear()
        self._redo.clear()
        self._bind_all()
        self._tick()

    def shift_day(self, delta: int) -> None:
        self.go_to(self.day.date + timedelta(days=delta))

    # ---------------------------------------------------------------- roster
    def set_working(self, assoc_id: str, on: bool) -> None:
        a = self.team.get(assoc_id)
        if a is None or self.day.is_working(assoc_id) == on:
            return
        self.snapshot()
        self.day.set_working(a, on)
        self._after_day_mutation(rebuild=True)

    def add_associate(self) -> None:
        dlg = AssociateDialog(parent=self)
        if dlg.exec():
            a = Associate("")
            dlg.apply_to(a)
            self.team.associates.append(a)
            self.day.set_working(a, True)
            self._after_day_mutation(rebuild=True)

    def edit_associate(self, assoc_id: str) -> None:
        a = self.team.get(assoc_id)
        if a is None:
            return
        dlg = AssociateDialog(a, parent=self)
        if dlg.exec():
            dlg.apply_to(a)
            self._after_day_mutation(rebuild=True)

    def remove_associate(self, assoc_id: str) -> None:
        a = self.team.get(assoc_id)
        if a is None:
            return
        if QMessageBox.question(self, "Remove", f"Remove {a.name} from the team?") != QMessageBox.StandardButton.Yes:
            return
        self.team.associates = [x for x in self.team.associates if x.id != assoc_id]
        self.day.set_working(a, False)
        self._after_day_mutation(rebuild=True)

    def move_associate(self, assoc_id: str, delta: int) -> None:
        ids = [a.id for a in self.team.associates]
        if assoc_id not in ids:
            return
        i = ids.index(assoc_id)
        j = i + delta
        if not (0 <= j < len(ids)):
            return
        self.team.associates[i], self.team.associates[j] = self.team.associates[j], self.team.associates[i]
        self._after_day_mutation(rebuild=True)

    def edit_day_details(self, assoc_id: str) -> None:
        a, w = self.team.get(assoc_id), self.day.day_assoc(assoc_id)
        if a is None or w is None:
            return
        dlg = DayAssociateDialog(self.team, a, w, parent=self)
        if dlg.exec():
            self.snapshot()
            dlg.apply_to(w, a)
            self._after_day_mutation(rebuild=True)

    # ----------------------------------------------------------------- tasks
    def team_changed(self) -> None:
        """Called after the task list changed (e.g. from inside a dialog)."""
        self.palette_panel.rebuild()
        self.grid.refresh()
        self.mark_dirty()

    def new_task(self) -> None:
        dlg = TaskDialog(self.team, parent=self)
        if dlg.exec():
            self.team.tasks.append(dlg.result_task())
            self.team_changed()

    def edit_task(self, name: str) -> None:
        t = self.team.task(name)
        if t is None:
            return
        dlg = TaskDialog(self.team, t, parent=self)
        if dlg.exec():
            new = dlg.result_task()
            if new.name != t.name:
                # Tasks are matched by name, so rename it everywhere — every
                # saved day, template and undo step — or old blocks turn gray.
                self.day.rename_task(t.name, new.name)
                self.storage.rename_task(t.name, new.name)
                for stack in (self._undo, self._redo):
                    for i, snap in enumerate(stack):
                        d = Day.from_dict(snap)
                        if d.rename_task(t.name, new.name):
                            stack[i] = d.to_dict()
                quick = self.team.settings.quick_tasks
                quick[:] = [new.name if q == t.name else q for q in quick]
                self._quick_use = [new.name if q == t.name else q for q in self._quick_use]
            t.name, t.category, t.color = new.name, new.category, new.color
            self.team_changed()

    def set_task_required(self, name: str, on: bool) -> None:
        t = self.team.task(name)
        if t is not None and t.required != on:
            t.required = on
            self.mark_dirty()

    def check_sheet(self) -> None:
        problems = find_violations(self.team, self.day)
        if not problems:
            QMessageBox.information(self, "Check Sheet", "No problems found. \u2714")
            return
        n = len(problems)
        QMessageBox.warning(
            self,
            "Check Sheet",
            f"{n} problem{'s' if n != 1 else ''} found:\n\n" + "\n".join(f"\u2022 {p}" for p in problems),
        )

    def delete_task(self, name: str) -> None:
        if QMessageBox.question(self, "Delete task", f"Delete the task type '{name}'?\n"
                                "Blocks already using it stay on the schedule (in gray).") != QMessageBox.StandardButton.Yes:
            return
        self.team.tasks = [t for t in self.team.tasks if t.name != name]
        self.team_changed()

    # ------------------------------------------------------------ assignment
    def assign(self, ids: list[str], start: int, end: int, task: str, note: str = "") -> None:
        self.snapshot()
        for aid in ids:
            self.day.set_range(aid, start, end, task, note)
        self._note_used(task)
        self._after_day_mutation()

    def apply_task_to_selection(self, task: str) -> None:
        ranges = self.grid.selected_ranges()
        if not ranges:
            self.open_assign_dialog(task=task)
            return
        self.snapshot()
        for aid, a, b in ranges:
            self.day.set_range(aid, a, b, task)
        self._note_used(task)
        self._after_day_mutation()

    def _palette_task(self, task: str) -> None:
        self.apply_task_to_selection(task)
        self.grid.setFocus()  # so the number keys / Delete work straight away

    # --- quick keys ----------------------------------------------------------------
    def apply_quick_task(self, index: int) -> None:
        quick = self.palette_panel.quick_tasks()
        if index < len(quick):
            self.apply_task_to_selection(quick[index])

    def _note_used(self, task: str) -> None:
        """Put `task` on a number key (if it isn't already) without moving the others."""
        if self.team.task(task) is None:
            return
        quick = self.team.settings.quick_tasks
        quick[:] = [q for q in quick if self.team.task(q)][:QUICK_KEYS]
        self._quick_use = [q for q in self._quick_use if q in quick and q != task]
        if task not in quick:
            if len(quick) < QUICK_KEYS:
                quick.append(task)
            else:
                oldest = self._quick_use.pop(0) if self._quick_use else quick[-1]
                quick[quick.index(oldest)] = task
            self.palette_panel.rebuild()
        self._quick_use.append(task)

    def forget_quick_task(self, task: str) -> None:
        quick = self.team.settings.quick_tasks
        quick[:] = [q for q in quick if q != task]
        self._quick_use = [q for q in self._quick_use if q != task]
        self.palette_panel.rebuild()
        self.mark_dirty()

    # --- drag, copy / paste ---------------------------------------------------------
    def resize_block(self, aid: str, old_start: int, old_end: int, start: int, end: int) -> None:
        seg = next((x for x in self.day.segs(aid) if x.start == old_start and x.end == old_end), None)
        if seg is None:
            return
        self.snapshot()
        task, note = seg.task, seg.note
        self.day.set_range(aid, old_start, old_end, None)
        self.day.set_range(aid, start, end, task, note)
        self._after_day_mutation()

    def move_cells(self, moves: list, shift: int, copy: bool) -> None:
        """moves = [(from id, to id, start, end)]: move (or copy) what's in each
        range to the other person, `shift` minutes later. Empty cells move too."""
        self.snapshot()
        pieces = [(dst, a + shift, b - a, self.day.extract(src, a, b)) for src, dst, a, b in moves]
        if not copy:
            for src, _, a, b in moves:
                self.day.set_range(src, a, b, None)
        for dst, at, length, segs in pieces:
            self.day.put(dst, at, length, segs)
        self._after_day_mutation()

    def copy_cells(self) -> bool:
        blocks = self.grid.selected_blocks()
        if not blocks:
            self.statusBar().showMessage("Select some cells to copy first.", 3000)
            return False
        col0 = min(c for c, _, _ in blocks)
        t0 = self.grid.row_time(min(r0 for _, r0, _ in blocks))
        self._clipboard = []
        for c, r0, r1 in blocks:
            a, b = self.grid.row_time(r0), self.grid.row_time(r1 + 1)
            aid = self.grid.assoc_at(c).id
            self._clipboard.append((c - col0, a - t0, b - a, self.day.extract(aid, a, b)))
        self.statusBar().showMessage("Copied — select where it should go and press Ctrl+V.", 4000)
        return True

    def cut_cells(self) -> None:
        if self.copy_cells():
            self.clear_selection()

    def paste_cells(self) -> None:
        if not self._clipboard:
            self.statusBar().showMessage("Nothing copied yet — select cells and press Ctrl+C.", 3000)
            return
        blocks = self.grid.selected_blocks()
        if blocks:
            row0 = min(r0 for _, r0, _ in blocks)
            cols = sorted({c for c, _, _ in blocks})
        else:
            cur = self.grid.currentIndex()
            if not cur.isValid():
                return
            row0, cols = cur.row(), [cur.column()]
        # One copied column pasted onto several selected people goes to each of
        # them; otherwise it lands with its top-left at the first selected cell.
        if len({dc for dc, _, _, _ in self._clipboard}) > 1:
            cols = cols[:1]
        s = self.team.settings
        anchor = self.grid.row_time(row0)
        self.snapshot()
        pasted = []
        for col in cols:
            for dc, dt, length, segs in self._clipboard:
                assoc = self.grid.assoc_at(col + dc)
                at = anchor + dt
                length = min(length, s.day_end - at)
                if assoc is None or length <= 0:
                    continue
                self.day.put(assoc.id, at, length, segs)
                r = (at - s.day_start) // s.slot_minutes
                pasted.append((col + dc, r, r + -(-length // s.slot_minutes) - 1))
        self._after_day_mutation()
        self.grid.select_blocks(pasted)

    def repeat_cells(self) -> None:
        """Ctrl+D: copy each selected block to straight after itself and select the copy,
        so pressing it again keeps repeating."""
        blocks = self.grid.selected_blocks()
        if not blocks:
            return
        s = self.team.settings
        self.snapshot()
        repeated = []
        for c, r0, r1 in blocks:
            a, b = self.grid.row_time(r0), self.grid.row_time(r1 + 1)
            length = min(b - a, s.day_end - b)
            if length <= 0:
                continue
            aid = self.grid.assoc_at(c).id
            self.day.put(aid, b, length, self.day.extract(aid, a, b))
            repeated.append((c, r1 + 1, r1 + (r1 - r0) + 1))
        self._after_day_mutation()
        self.grid.select_blocks(repeated)

    def clear_selection(self) -> None:
        ranges = self.grid.selected_ranges()
        if not ranges:
            return
        self.snapshot()
        for aid, a, b in ranges:
            self.day.set_range(aid, a, b, None)
        self._after_day_mutation()

    def clear_all(self) -> None:
        if QMessageBox.question(self, "Clear", "Remove every assignment for this day?") != QMessageBox.StandardButton.Yes:
            return
        self.snapshot()
        self.day.clear_all()
        self._after_day_mutation()

    def open_assign_dialog(self, task: str | None = None) -> None:
        if not self.day.working:
            QMessageBox.information(self, "Nobody working", "Check at least one person in the roster first.")
            return
        ranges = self.grid.selected_ranges()
        start = end = None
        people = None
        if ranges:
            start = min(r[1] for r in ranges)
            end = max(r[2] for r in ranges)
            people = sorted({r[0] for r in ranges})
        dlg = AssignDialog(self.team, self.day, parent=self, task=task, start=start, end=end, people=people)
        dlg.exec()

    def edit_block(self, row: int, col: int) -> None:
        a = self.grid.assoc_at(col)
        if a is None:
            return
        s = self.team.settings
        slot = self.grid.slots[row]
        run = self.grid.run_at(row, col)
        seg = run.segment if run else None
        dlg = BlockDialog(self.team, a, seg, slot, slot + s.slot_minutes, parent=self)
        if not dlg.exec():
            return
        self.snapshot()
        if seg is not None:
            self.day.set_range(a.id, seg.start, seg.end, None)
        if not dlg.cleared:
            task, note, start, end = dlg.values()
            self.day.set_range(a.id, start, end, task, note)
            self._note_used(task)
        self._after_day_mutation()

    def grid_context_menu(self, pos, row: int, col: int) -> None:
        self.build_grid_menu(row, col).exec(pos)

    def build_grid_menu(self, row: int, col: int) -> QMenu:
        from .dialogs import color_icon

        menu = QMenu(self)
        run = self.grid.run_at(row, col)
        menu.addAction("Edit block… (task / note / time)", lambda: self.edit_block(row, col))
        menu.addAction("Clear selected cells", self.clear_selection)
        menu.addAction("Assign to several people…", self.open_assign_dialog)
        menu.addSeparator()
        for text, slot, key in (
            ("Copy", self.copy_cells, QKeySequence.StandardKey.Copy),
            ("Cut", self.cut_cells, QKeySequence.StandardKey.Cut),
            ("Paste", self.paste_cells, QKeySequence.StandardKey.Paste),
            ("Repeat below", self.repeat_cells, QKeySequence("Ctrl+D")),
        ):
            act = menu.addAction(text, slot)
            act.setShortcut(key)
            if slot == self.paste_cells:
                act.setEnabled(bool(self._clipboard))
        menu.addSeparator()
        for cat in CATEGORIES:
            tasks = [t for t in self.team.tasks if t.category == cat]
            if not tasks:
                continue
            sub = menu.addMenu(cat)
            for t in tasks:
                act = sub.addAction(color_icon(t.effective_color()), t.name)
                act.triggered.connect(lambda _=False, n=t.name: self.apply_task_to_selection(n))
        if run is not None:
            menu.addSeparator()
            r = run
            menu.addAction(
                f"Select whole block ({minutes_to_label(r.segment.start)}–{minutes_to_label(r.segment.end)})",
                lambda: self._select_segment(col, r),
            )
        return menu

    def _select_segment(self, col: int, run) -> None:
        seg = run.segment
        rows = [i for i, m in enumerate(self.grid.slots) if seg.start <= m < seg.end]
        if rows:
            self.grid.select_range(col, rows[0], rows[-1])

    def _notes_edited(self, text: str) -> None:
        self.day.notes = text
        self.mark_dirty()

    # -------------------------------------------------------- copy / templates
    def _apply_day_layout(self, src: Day, label: str) -> None:
        """Copy working list + assignments from another Day onto today."""
        self.snapshot()
        known = {a.id for a in self.team.associates}
        self.day.working = [copy.deepcopy(w) for w in src.working if w.id in known]
        self.day.segments = {k: copy.deepcopy(v) for k, v in src.segments.items() if k in known}
        if not self.day.notes:
            self.day.notes = src.notes
        self._after_day_mutation(rebuild=True)
        self.statusBar().showMessage(f"Copied {label}.", 4000)

    def copy_previous_day(self) -> None:
        prev = [d for d in self.storage.saved_dates() if d < self.day.date]
        if not prev:
            QMessageBox.information(self, "Copy", "There is no earlier saved day to copy from.")
            return
        src = self.storage.load_day(prev[0])
        self._apply_day_layout(src, prev[0].strftime("%a %b %d"))

    def copy_from_date(self) -> None:
        dates = [d for d in self.storage.saved_dates() if d != self.day.date]
        labels = [d.strftime("%a %b %d, %Y") for d in dates]
        choice = pick_from_list(self, "Copy from", "Copy the schedule from:", labels)
        if choice:
            src = self.storage.load_day(dates[labels.index(choice)])
            self._apply_day_layout(src, choice)

    def save_template(self) -> None:
        name = ask_text(self, "Save template", "Template name:", "Standard day")
        if name:
            self.storage.save_template(name, self.day)
            self.statusBar().showMessage(f"Saved template '{name}'.", 4000)

    def apply_template(self) -> None:
        name = pick_from_list(self, "Apply template", "Template:", self.storage.template_names())
        if name:
            src = self.storage.load_template(name)
            if src:
                self._apply_day_layout(src, f"template '{name}'")

    def delete_template(self) -> None:
        name = pick_from_list(self, "Delete template", "Template:", self.storage.template_names())
        if name and QMessageBox.question(self, "Delete", f"Delete template '{name}'?") == QMessageBox.StandardButton.Yes:
            self.storage.delete_template(name)

    # --------------------------------------------------------------- settings
    def open_settings(self) -> None:
        dlg = SettingsDialog(self.team, parent=self)
        if dlg.exec():
            dlg.apply_to(self.team)
            self._bind_all()
            self.mark_dirty()

    def show_help(self) -> None:
        QMessageBox.information(
            self,
            "How to use",
            "<b>1. Who's working:</b> check names in the Roster. Each checked person gets a column.<br>"
            "Double-click a person (or a column header) to set today's duty, topstock aisles or shift.<br><br>"
            "<b>2. Assign work:</b> drag over cells in the grid, then click a task on the left "
            "(or right-click the cells). Consecutive cells with the same task merge into one block.<br>"
            "Use <b>Assign Task…</b> (Ctrl+T) to give the same task to several people at once.<br>"
            "Double-click a block to change its note (e.g. case counts) or exact times. "
            "Delete key clears selected cells.<br><br>"
            "<b>Faster editing:</b> drag a block's top or bottom edge to resize it. Drag cells that are "
            "already selected to move them (hold Ctrl as you let go to copy). "
            "Ctrl+C / Ctrl+X / Ctrl+V copy, cut and paste — paste one person's cells onto several "
            "selected people to give it to all of them. Ctrl+D repeats a block straight after itself.<br>"
            "Number keys 1–5 apply the quick-key tasks at the top of the palette; "
            "start typing a task name in the grid to search, then press Enter.<br><br>"
            "<b>Check:</b> tick <b>Required</b> beside a task that must be given to someone every day, "
            "then press <b>Check Sheet</b> (F7) to list any problems.<br><br>"
            "<b>3. Reuse:</b> Day ▾ → copy a previous day or save/apply a template.<br><br>"
            "<b>4. Share:</b> Print / Export ▾ → print, PDF, PNG image, or Excel with one tab per person.<br><br>"
            "<b>View:</b> <b>Fit Day</b> fits the whole day in the window; Ctrl+mouse wheel "
            "(or Ctrl + / Ctrl −) zooms the rows, Ctrl+0 resets.<br><br>"
            f"Everything saves automatically to the data folder:<br><code>{escape(str(self.storage.root))}</code>",
        )

    # ---------------------------------------------------------------- output
    def _document(self, html: str) -> QTextDocument:
        doc = QTextDocument()
        doc.setHtml(html)
        return doc

    def _printer(self, landscape: bool) -> QPrinter:
        p = QPrinter(QPrinter.PrinterMode.HighResolution)
        p.setPageOrientation(QPageLayout.Orientation.Landscape if landscape else QPageLayout.Orientation.Portrait)
        p.setPageMargins(QMarginsF(10, 10, 10, 10), QPageLayout.Unit.Millimeter)
        return p

    def print_html(self, html: str, landscape: bool = False) -> None:
        printer = self._printer(landscape)
        doc = self._document(html)
        dlg = QPrintPreviewDialog(printer, self)
        dlg.setWindowTitle("Print preview")
        dlg.paintRequested.connect(lambda pr: doc.print_(pr))
        dlg.resize(1100, 800)
        dlg.exec()

    def _suggest(self, suffix: str, ext: str) -> str:
        return f"{self.day.date.isoformat()}-{suffix}.{ext}"

    def save_pdf(self, html: str, suffix: str, landscape: bool) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF", self._suggest(suffix, "pdf"), "PDF (*.pdf)")
        if not path:
            return
        printer = self._printer(landscape)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(path)
        self._document(html).print_(printer)
        self.statusBar().showMessage(f"Saved {path}", 5000)

    def save_png(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save image", self._suggest("schedule", "png"), "PNG image (*.png)")
        if not path:
            return
        doc = self._document(ex.board_html(self.team, self.day))
        width = 1500
        doc.setTextWidth(width)
        size = doc.size().toSize()
        scale = 2
        img = QImage(size.width() * scale, size.height() * scale, QImage.Format.Format_ARGB32)
        img.fill(QColor("white"))
        painter = QPainter(img)
        painter.scale(scale, scale)
        doc.drawContents(painter)
        painter.end()
        img.save(path)
        self.statusBar().showMessage(f"Saved {path}", 5000)

    def export_excel(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export to Excel", self._suggest("schedule", "xlsx"), "Excel (*.xlsx)")
        if not path:
            return
        try:
            ex.export_xlsx(path, self.team, self.day)
        except Exception as e:  # noqa: BLE001 - show any failure to the user
            QMessageBox.critical(self, "Export failed", str(e))
            return
        self.statusBar().showMessage(f"Saved {path}", 5000)
