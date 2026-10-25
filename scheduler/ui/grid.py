"""The schedule grid: rows are time slots, columns are the people working today.

Blocks of consecutive rows with the same assignment are drawn as one merged
block (colored, outlined, text centered) even though every cell stays
individually selectable — so you can drag over any range and paint a task.

Dragging a block's top or bottom edge resizes it; dragging cells that are
already selected moves them (hold Ctrl when letting go to copy instead).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QRect, QSize, Signal, QPoint, QItemSelection, QItemSelectionModel
from PySide6.QtGui import QColor, QFont, QFontMetrics, QKeySequence, QPainter, QPen, QBrush
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QHeaderView,
    QStyle,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
)

from ..models import Team, Day, Associate, DayAssociate, Run, column_runs, working_associates, minutes_to_label, ROLE_PICKER

HEADER_BG = QColor("#0b2a4a")
HEADER_BG_PICKER = QColor("#1f4e79")
HEADER_FG = QColor("#ffffff")
HEADER_SUB = QColor("#c9d6e3")
EMPTY_BG = QColor("#ffffff")
OFF_SHIFT_BG = QColor("#ececec")
GRID_LINE = QColor("#dfe3e8")
HOUR_LINE = QColor("#b9c2cc")
TEXT = QColor("#1b1b1b")
SELECT_OVERLAY = QColor(25, 95, 210, 55)  # drag-preview fill
SELECT_HATCH = QColor(20, 60, 170, 150)  # selected cells: diagonal stripes, so a
SELECT_BORDER = QColor("#1543a8")        # selection never looks like a blue task
MIN_ROW_HEIGHT = 14  # "Fit day" won't squeeze rows below this; it scrolls instead
NOW_LINE = QColor("#e02020")
EDGE_GRAB = 4  # px either side of a block's top/bottom edge that grabs it for resizing


class PeopleHeader(QHeaderView):
    """Multi-line column header: name / role / duty / aisles."""

    edit_requested = Signal(int)  # logical column index

    def __init__(self, grid: "ScheduleGrid"):
        super().__init__(Qt.Orientation.Horizontal, grid)
        self.grid = grid
        self.setSectionsClickable(True)
        self.setHighlightSections(False)
        self.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStretchLastSection(False)
        self.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.sectionDoubleClicked.connect(self.edit_requested)

    def sizeHint(self) -> QSize:
        return QSize(super().sizeHint().width(), 74)

    def paintSection(self, painter: QPainter, rect: QRect, index: int) -> None:
        painter.save()
        try:
            a, w = self.grid.people[index]
        except IndexError:
            painter.fillRect(rect, HEADER_BG)
            painter.restore()
            return
        painter.fillRect(rect, HEADER_BG_PICKER if a.role == ROLE_PICKER else HEADER_BG)
        painter.setPen(QPen(QColor("#4a6684"), 1))
        painter.drawLine(rect.topRight(), rect.bottomRight())

        lines: list[tuple[str, QFont, QColor]] = []
        bold = QFont(self.font())
        bold.setBold(True)
        bold.setPointSizeF(self.font().pointSizeF() + 1)
        small = QFont(self.font())
        small.setPointSizeF(max(7.0, self.font().pointSizeF() - 1))
        lines.append((a.name, bold, HEADER_FG))
        role = a.role + (" · optional" if a.optional else "")
        lines.append((role, small, HEADER_SUB))
        if w.duty:
            lines.append((w.duty, small, QColor("#ffe08a")))
        extra = []
        if w.aisles:
            extra.append(f"Topstock {w.aisles}")
        if w.shift_start is not None and w.shift_end is not None:
            extra.append(f"{minutes_to_label(w.shift_start)}–{minutes_to_label(w.shift_end)}")
        if extra:
            lines.append((" · ".join(extra), small, HEADER_SUB))

        total = sum(QFontMetrics(f).height() for _, f, _ in lines)
        y = rect.top() + max(2, (rect.height() - total) // 2)
        for text, font, color in lines:
            fm = QFontMetrics(font)
            painter.setFont(font)
            painter.setPen(color)
            elided = fm.elidedText(text, Qt.TextElideMode.ElideRight, rect.width() - 8)
            painter.drawText(QRect(rect.left() + 4, y, rect.width() - 8, fm.height()), Qt.AlignmentFlag.AlignCenter, elided)
            y += fm.height()
        painter.restore()


class BlockDelegate(QStyledItemDelegate):
    def __init__(self, grid: "ScheduleGrid"):
        super().__init__(grid)
        self.grid = grid

    def paint(self, painter: QPainter, option, index) -> None:
        grid = self.grid
        row, col = index.row(), index.column()
        rect: QRect = option.rect
        team, day = grid.team, grid.day
        if team is None or day is None:
            return
        s = team.settings
        slot_start = grid.slots[row]
        run = grid.run_at(row, col)

        painter.save()
        painter.setClipRect(rect)

        if run is None:
            on_shift = grid.on_shift(col, slot_start)
            painter.fillRect(rect, EMPTY_BG if on_shift else OFF_SHIFT_BG)
            is_hour = (slot_start + s.slot_minutes) % 60 == 0
            painter.setPen(QPen(HOUR_LINE if is_hour else GRID_LINE, 1))
            painter.drawLine(rect.bottomLeft(), rect.bottomRight())
            painter.setPen(QPen(GRID_LINE, 1))
            painter.drawLine(rect.topRight(), rect.bottomRight())
        else:
            color = QColor(team.task_color(run.segment.task))
            painter.fillRect(rect, color)
            top_y = grid.rowViewportPosition(run.row)
            last = run.row + run.rows - 1
            bottom_y = grid.rowViewportPosition(last) + grid.rowHeight(last)
            run_rect = QRect(rect.left(), top_y, rect.width(), bottom_y - top_y)
            painter.setPen(QPen(color.darker(150), 1))
            painter.drawRect(run_rect.adjusted(0, 0, -1, -1))
            self._draw_block_text(painter, run_rect, run)

        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(rect, QColor(25, 95, 210, 30))
            painter.fillRect(rect, QBrush(SELECT_HATCH, Qt.BrushStyle.BDiagPattern))
            sel = grid.selectionModel()
            m = grid.model()
            top = row == 0 or not sel.isSelected(m.index(row - 1, col))
            bottom = row == grid.rowCount() - 1 or not sel.isSelected(m.index(row + 1, col))
            left = col == 0 or not sel.isSelected(m.index(row, col - 1))
            right = col == grid.columnCount() - 1 or not sel.isSelected(m.index(row, col + 1))
            edge = 2  # outline drawn just inside the cell, so neighbours can't paint over it
            if top:
                painter.fillRect(QRect(rect.left(), rect.top(), rect.width(), edge), SELECT_BORDER)
            if bottom:
                painter.fillRect(QRect(rect.left(), rect.bottom() - edge + 1, rect.width(), edge), SELECT_BORDER)
            if left:
                painter.fillRect(QRect(rect.left(), rect.top(), edge, rect.height()), SELECT_BORDER)
            if right:
                painter.fillRect(QRect(rect.right() - edge + 1, rect.top(), edge, rect.height()), SELECT_BORDER)

        now = grid.now_minute
        if now is not None and slot_start <= now < slot_start + s.slot_minutes:
            y = rect.top() + int(rect.height() * (now - slot_start) / s.slot_minutes)
            painter.setPen(QPen(NOW_LINE, 2))
            painter.drawLine(rect.left(), y, rect.right(), y)
        painter.restore()

    def _draw_block_text(self, painter: QPainter, run_rect: QRect, run: Run) -> None:
        seg = run.segment
        base = self.grid.font()
        bold = QFont(base)
        bold.setBold(True)
        small = QFont(base)
        small.setPointSizeF(max(7.0, base.pointSizeF() - 1.5))
        fm_b, fm_s = QFontMetrics(bold), QFontMetrics(small)
        width = run_rect.width() - 8
        avail = run_rect.height() - 2
        if avail < fm_b.height():  # short rows (zoomed out / Fit day): shrink to fit
            bold.setPointSizeF(max(6.5, bold.pointSizeF() * avail / fm_b.height()))
            fm_b = QFontMetrics(bold)

        lines: list[tuple[str, QFont, QFontMetrics]] = [(seg.task, bold, fm_b)]
        if seg.note and avail >= fm_b.height() + fm_s.height():
            lines.append((seg.note, small, fm_s))
        rng = f"{minutes_to_label(seg.start)}–{minutes_to_label(seg.end)}"
        if avail >= sum(fm.height() for _, _, fm in lines) + fm_s.height():
            lines.append((rng, small, fm_s))

        total = sum(fm.height() for _, _, fm in lines)
        y = run_rect.top() + max(1, (run_rect.height() - total) // 2)
        painter.setPen(TEXT)
        for text, font, fm in lines:
            painter.setFont(font)
            elided = fm.elidedText(text, Qt.TextElideMode.ElideRight, width)
            painter.drawText(QRect(run_rect.left() + 4, y, width, fm.height()), Qt.AlignmentFlag.AlignCenter, elided)
            y += fm.height()


class ScheduleGrid(QTableWidget):
    selection_summary = Signal(str)
    cell_activated = Signal(int, int)  # row, col (double click)
    header_edit = Signal(str)  # associate id
    context_requested = Signal(QPoint, int, int)  # global pos, row, col
    clear_requested = Signal()  # Delete / Backspace pressed
    block_resized = Signal(str, int, int, int, int)  # assoc id, old start, old end, new start, new end
    cells_moved = Signal(list, int, bool)  # [(from id, to id, start, end)], minutes shifted, copy
    copy_requested = Signal()
    cut_requested = Signal()
    paste_requested = Signal()
    repeat_requested = Signal()  # Ctrl+D
    quick_task = Signal(int)  # number key pressed (0-based)
    type_search = Signal(str)  # a letter typed while the grid has focus
    fit_changed = Signal(bool)  # "Fit day" turned on/off (Ctrl+wheel zoom turns it off)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.team: Team | None = None
        self.day: Day | None = None
        self.people: list[tuple[Associate, DayAssociate]] = []
        self.slots: list[int] = []
        self._runs: list[dict[int, Run]] = []
        self.now_minute: int | None = None
        # Mouse gestures in progress (None when idle)
        self._resize: dict | None = None  # dragging a block edge
        self._press: tuple[QPoint, object] | None = None  # pressed on a selected cell
        self._drag: tuple[int, int] | None = None  # (rows, cols) the selection is being moved by
        self._move_blocks: list[tuple[int, int, int]] = []
        # Row height: stretch the whole day to the window, or the normal height × zoom
        self.fit_day = False
        self.zoom = 1.0

        self._header = PeopleHeader(self)
        self.setHorizontalHeader(self._header)
        self._header.edit_requested.connect(self._on_header_edit)
        self.setItemDelegate(BlockDelegate(self))
        self.setShowGrid(False)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setCornerButtonEnabled(False)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context)
        self.viewport().setMouseTracking(True)  # to show the resize cursor over block edges
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.verticalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.verticalHeader().setMinimumWidth(58)
        self.verticalHeader().setMinimumSectionSize(MIN_ROW_HEIGHT)
        self.setStyleSheet(
            "QTableWidget { background: white; border: 1px solid #b9c2cc; }"
            "QHeaderView::section:vertical { background: #e9eef4; border: 0; border-bottom: 1px solid #dfe3e8;"
            " border-right: 1px solid #b9c2cc; padding-right: 6px; color: #1b1b1b; }"
        )
        self.selectionModel().selectionChanged.connect(lambda *_: self._emit_summary())

    # --- data -------------------------------------------------------------
    def set_data(self, team: Team, day: Day) -> None:
        self.team, self.day = team, day
        self.rebuild()

    def rebuild(self) -> None:
        """Rebuild rows/columns from the model (call after roster or settings change)."""
        if self.team is None or self.day is None:
            return
        keep = self._selected_cells()
        s = self.team.settings
        self.slots = s.slots()
        self.people = working_associates(self.team, self.day)
        self.setUpdatesEnabled(False)
        self.clearSelection()
        self.setRowCount(len(self.slots))
        self.setColumnCount(len(self.people))
        for r, m in enumerate(self.slots):
            item = QTableWidgetItem(minutes_to_label(m))
            f = QFont(self.font())
            f.setBold(m % 60 == 0)
            if m % 60 != 0:
                item.setForeground(QBrush(QColor("#5b6773")))
            item.setFont(f)
            self.setVerticalHeaderItem(r, item)
        self._apply_row_height()
        for c, (a, w) in enumerate(self.people):
            self.setHorizontalHeaderItem(c, QTableWidgetItem(a.name))
        self.refresh()
        for r, c in keep:
            if r < self.rowCount() and c < self.columnCount():
                self.selectionModel().select(self.model().index(r, c), self.selectionModel().SelectionFlag.Select)
        self.setUpdatesEnabled(True)
        self._emit_summary()

    # --- row height: fit day / zoom -------------------------------------------
    def _row_height(self) -> int:
        if self.fit_day and self.rowCount():
            return max(MIN_ROW_HEIGHT, self.viewport().height() // self.rowCount())
        return max(MIN_ROW_HEIGHT, min(90, round(self._row_height_at_zoom_1() * self.zoom)))

    def _apply_row_height(self) -> None:
        h = self._row_height()
        # the time labels shrink along with short rows so they aren't clipped
        size = self.font().pointSizeF() * min(1.0, h / 20)
        for r in range(self.rowCount()):
            if self.rowHeight(r) != h:
                self.setRowHeight(r, h)
            item = self.verticalHeaderItem(r)
            if item is not None and abs(item.font().pointSizeF() - size) > 0.05:
                f = item.font()
                f.setPointSizeF(max(6.5, size))
                item.setFont(f)

    def set_fit_day(self, on: bool) -> None:
        if on != self.fit_day:
            self.fit_day = on
            self._apply_row_height()
            self.fit_changed.emit(on)

    def set_zoom(self, zoom: float) -> None:
        """Normal row height × zoom (also turns Fit day off)."""
        self.zoom = max(0.5, min(3.0, zoom))
        self.set_fit_day(False)
        self._apply_row_height()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.fit_day:
            self._apply_row_height()

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # zoom from whatever size the rows are now, so leaving Fit day doesn't jump
            current = self._row_height() / max(1, self._row_height_at_zoom_1())
            step = 1.1 if event.angleDelta().y() > 0 else 1 / 1.1
            self.set_zoom(current * step)
            event.accept()
            return
        super().wheelEvent(event)

    def _row_height_at_zoom_1(self) -> int:
        """Normal row height for the grid granularity (taller rows for longer slots)."""
        return max(18, min(44, int(self.team.settings.slot_minutes * 1.5))) if self.team else 22

    def refresh(self) -> None:
        """Recompute the merged blocks and repaint (call after assignments change)."""
        if self.team is None or self.day is None:
            return
        s = self.team.settings
        self._runs = []
        for a, _ in self.people:
            runs = column_runs(self.day, a.id, self.slots, s.slot_minutes)
            lookup: dict[int, Run] = {}
            for r in runs:
                for k in range(r.rows):
                    lookup[r.row + k] = r
            self._runs.append(lookup)
        self.viewport().update()
        self._header.viewport().update()
        self._emit_summary()

    def run_at(self, row: int, col: int) -> Run | None:
        if col >= len(self._runs):
            return None
        return self._runs[col].get(row)

    def on_shift(self, col: int, minute: int) -> bool:
        try:
            w = self.people[col][1]
        except IndexError:
            return True
        if w.shift_start is None or w.shift_end is None:
            return True
        return w.shift_start <= minute < w.shift_end

    def assoc_at(self, col: int) -> Associate | None:
        return self.people[col][0] if 0 <= col < len(self.people) else None

    # --- selection ----------------------------------------------------------
    def _selected_cells(self) -> list[tuple[int, int]]:
        return [(i.row(), i.column()) for i in self.selectedIndexes()]

    def selected_blocks(self) -> list[tuple[int, int, int]]:
        """[(column, first row, last row)] for every contiguous selected run of cells."""
        by_col: dict[int, list[int]] = {}
        for r, c in self._selected_cells():
            by_col.setdefault(c, []).append(r)
        out: list[tuple[int, int, int]] = []
        for c, rows in sorted(by_col.items()):
            rows.sort()
            start = prev = rows[0]
            for r in rows[1:]:
                if r == prev + 1:
                    prev = r
                    continue
                out.append((c, start, prev))
                start = prev = r
            out.append((c, start, prev))
        return out

    def row_time(self, row: int) -> int:
        """Minute at which grid row `row` starts (row == rowCount gives the end of the last row)."""
        s = self.team.settings
        return s.day_start + row * s.slot_minutes

    def selected_ranges(self) -> list[tuple[str, int, int]]:
        """[(associate id, start minute, end minute)] for every contiguous selected block."""
        if self.team is None:
            return []
        out: list[tuple[str, int, int]] = []
        for c, r0, r1 in self.selected_blocks():
            a = self.assoc_at(c)
            if a is not None:
                out.append((a.id, self.row_time(r0), self.row_time(r1 + 1)))
        return out

    def select_blocks(self, blocks: list[tuple[int, int, int]]) -> None:
        """Select [(column, first row, last row)], clipped to the grid."""
        self.clearSelection()
        m = self.model()
        sel = QItemSelection()
        first = None
        for c, r0, r1 in blocks:
            r0, r1 = max(0, r0), min(self.rowCount() - 1, r1)
            if 0 <= c < self.columnCount() and r0 <= r1:
                sel.select(m.index(r0, c), m.index(r1, c))
                if first is None:
                    first = m.index(r0, c)
        if first is not None:
            self.selectionModel().setCurrentIndex(first, QItemSelectionModel.SelectionFlag.NoUpdate)
        self.selectionModel().select(sel, QItemSelectionModel.SelectionFlag.Select)

    def select_range(self, col: int, row0: int, row1: int) -> None:
        self.select_blocks([(col, row0, row1)])

    def _emit_summary(self) -> None:
        ranges = self.selected_ranges()
        if not ranges:
            self.selection_summary.emit("")
            return
        if len(ranges) == 1:
            aid, a, b = ranges[0]
            assoc = self.team.get(aid) if self.team else None
            name = assoc.name if assoc else "?"
            self.selection_summary.emit(f"Selected: {name}  {minutes_to_label(a, True)} – {minutes_to_label(b, True)}")
        else:
            people = {aid for aid, _, _ in ranges}
            self.selection_summary.emit(f"Selected: {len(ranges)} blocks across {len(people)} people")

    # --- events -------------------------------------------------------------
    def _on_context(self, pos: QPoint) -> None:
        idx = self.indexAt(pos)
        if not idx.isValid():
            return
        if not self.selectionModel().isSelected(idx):
            self.clearSelection()
            self.selectionModel().select(idx, self.selectionModel().SelectionFlag.Select)
        self.context_requested.emit(self.viewport().mapToGlobal(pos), idx.row(), idx.column())

    def _on_header_edit(self, col: int) -> None:
        a = self.assoc_at(col)
        if a:
            self.header_edit.emit(a.id)

    def keyPressEvent(self, event) -> None:
        key, text = event.key(), event.text()
        mods = event.modifiers() & ~Qt.KeyboardModifier.KeypadModifier
        Mod = Qt.KeyboardModifier
        if key == Qt.Key.Key_Escape and (self._press or self._resize):
            self._cancel_gesture()
        elif key == Qt.Key.Key_Control and self._drag:
            self._move_feedback(copy=True)
        elif key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.clear_requested.emit()
        elif event.matches(QKeySequence.StandardKey.Copy):
            self.copy_requested.emit()
        elif event.matches(QKeySequence.StandardKey.Cut):
            self.cut_requested.emit()
        elif event.matches(QKeySequence.StandardKey.Paste):
            self.paste_requested.emit()
        elif key == Qt.Key.Key_D and mods == Mod.ControlModifier:
            self.repeat_requested.emit()
        elif mods & Mod.ControlModifier and key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal, Qt.Key.Key_Minus, Qt.Key.Key_0):
            if key == Qt.Key.Key_0:
                self.set_zoom(1.0)
            else:
                current = self._row_height() / max(1, self._row_height_at_zoom_1())
                self.set_zoom(current * (1.1 if key != Qt.Key.Key_Minus else 1 / 1.1))
        elif text and not mods & (Mod.ControlModifier | Mod.AltModifier | Mod.MetaModifier) and text in "123456789":
            self.quick_task.emit(int(text) - 1)
        elif text and not mods & (Mod.ControlModifier | Mod.AltModifier | Mod.MetaModifier) and text.isalpha():
            self.type_search.emit(text)
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Control and self._drag:
            self._move_feedback(copy=False)
        super().keyReleaseEvent(event)

    # --- mouse: resize block edges / move the selection ----------------------
    def _edge_at(self, pos: QPoint) -> tuple[int, Run, str] | None:
        """(column, run, "top"/"bottom") if `pos` is on the top or bottom edge of a block."""
        idx = self.indexAt(pos)
        if not idx.isValid():
            return None
        row, col = idx.row(), idx.column()
        cell_top = self.rowViewportPosition(row)
        cell_bottom = cell_top + self.rowHeight(row)
        run = self.run_at(row, col)
        if cell_bottom - pos.y() <= EDGE_GRAB:
            if run and run.row + run.rows - 1 == row:
                return col, run, "bottom"
            below = self.run_at(row + 1, col)
            if below and below.row == row + 1:
                return col, below, "top"
        if pos.y() - cell_top <= EDGE_GRAB:
            if run and run.row == row:
                return col, run, "top"
            above = self.run_at(row - 1, col) if row > 0 else None
            if above and above.row + above.rows - 1 == row - 1:
                return col, above, "bottom"
        return None

    def _row_at(self, y: int) -> int:
        r = self.rowAt(y)
        if r < 0:
            r = 0 if y < self.rowViewportPosition(0) else self.rowCount() - 1
        return r

    def _col_at(self, x: int) -> int:
        c = self.columnAt(x)
        if c < 0:
            c = 0 if x < self.columnViewportPosition(0) else self.columnCount() - 1
        return c

    def _boundary_at(self, y: int) -> int:
        """Index of the row boundary nearest to viewport y (0 .. rowCount)."""
        r = self._row_at(y)
        return r + 1 if y - self.rowViewportPosition(r) > self.rowHeight(r) / 2 else r

    def _block_rect(self, col: int, r0: int, r1: int) -> QRect:
        top = self.rowViewportPosition(r0)
        bottom = self.rowViewportPosition(r1) + self.rowHeight(r1)
        return QRect(self.columnViewportPosition(col), top, self.columnWidth(col), bottom - top)

    def _autoscroll(self, pos: QPoint) -> None:
        bar, h = self.verticalScrollBar(), self.viewport().height()
        if pos.y() < 16:
            bar.setValue(bar.value() - 12)
        elif pos.y() > h - 16:
            bar.setValue(bar.value() + 12)

    def _plain_click(self, idx) -> None:
        self.selectionModel().setCurrentIndex(idx, QItemSelectionModel.SelectionFlag.ClearAndSelect)

    def _cancel_gesture(self) -> None:
        self._resize = self._press = self._drag = None
        self.viewport().unsetCursor()
        self.viewport().update()
        self._emit_summary()

    def mousePressEvent(self, event) -> None:
        pos = event.position().toPoint()
        if event.button() == Qt.MouseButton.LeftButton and self.team is not None:
            edge = self._edge_at(pos)
            if edge:
                col, run, side = edge
                self._resize = {"col": col, "run": run, "side": side, "origin": pos,
                                "idx": self.indexAt(pos), "new": None}
                return
            idx = self.indexAt(pos)
            if (idx.isValid() and event.modifiers() == Qt.KeyboardModifier.NoModifier
                    and self.selectionModel().isSelected(idx)):
                self._press = (pos, idx)
                self._drag = None
                self._move_blocks = self.selected_blocks()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        pos = event.position().toPoint()
        far = lambda origin: (pos - origin).manhattanLength() >= QApplication.startDragDistance()
        if self._resize:
            if self._resize["new"] is not None or far(self._resize["origin"]):
                self._update_resize(pos)
            return
        if self._press:
            if self._drag is not None or far(self._press[0]):
                self._update_move(pos, bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier))
            return
        if not event.buttons():
            if self._edge_at(pos):
                self.viewport().setCursor(Qt.CursorShape.SizeVerCursor)
            else:
                self.viewport().unsetCursor()
        super().mouseMoveEvent(event)

    def _update_resize(self, pos: QPoint) -> None:
        r = self._resize
        run, seg = r["run"], r["run"].segment
        last = run.row + run.rows - 1
        k = self._boundary_at(pos.y())
        if r["side"] == "bottom":
            k = max(k, run.row + 1)
            r["new"], r["rows"] = (seg.start, self.row_time(k)), (run.row, k - 1)
        else:
            k = min(k, last)
            r["new"], r["rows"] = (self.row_time(k), seg.end), (k, last)
        a, b = r["new"]
        self.selection_summary.emit(f"Resize {seg.task}: {minutes_to_label(a, True)} – {minutes_to_label(b, True)}")
        self._autoscroll(pos)
        self.viewport().update()

    def _update_move(self, pos: QPoint, copy: bool) -> None:
        idx = self._press[1]
        blocks = self._move_blocks
        dr = self._row_at(pos.y()) - idx.row()
        dc = self._col_at(pos.x()) - idx.column()
        # keep everything being moved inside the grid
        dr = max(-min(b[1] for b in blocks), min(dr, self.rowCount() - 1 - max(b[2] for b in blocks)))
        dc = max(-min(b[0] for b in blocks), min(dc, self.columnCount() - 1 - max(b[0] for b in blocks)))
        self._drag = (dr, dc)
        self._move_feedback(copy)
        self._autoscroll(pos)
        self.viewport().update()

    def _move_feedback(self, copy: bool) -> None:
        dr, dc = self._drag
        self.viewport().setCursor(Qt.CursorShape.DragCopyCursor if copy else Qt.CursorShape.ClosedHandCursor)
        verb = "Copy" if copy else "Move"
        if len(self._move_blocks) == 1:
            c, r0, r1 = self._move_blocks[0]
            a = self.assoc_at(c + dc)
            where = f"to {a.name if a else '?'} {minutes_to_label(self.row_time(r0 + dr), True)}" \
                    f" – {minutes_to_label(self.row_time(r1 + dr + 1), True)}"
        else:
            where = f"{len(self._move_blocks)} blocks"
        hint = "" if copy else "   (hold Ctrl when you let go to copy instead)"
        self.selection_summary.emit(f"{verb} {where}{hint}")

    def mouseReleaseEvent(self, event) -> None:
        if self._resize:
            r, self._resize = self._resize, None
            seg = r["run"].segment
            if r["new"] is None:
                self._plain_click(r["idx"])
            elif r["new"] != (seg.start, seg.end):
                aid = self.people[r["col"]][0].id
                self.block_resized.emit(aid, seg.start, seg.end, *r["new"])
                self.select_blocks([(r["col"], *r["rows"])])
            self._cancel_gesture()
            return
        if self._press:
            idx, drag, blocks = self._press[1], self._drag, self._move_blocks
            self._press = self._drag = None
            if drag is None:
                self._plain_click(idx)
            elif drag != (0, 0):
                dr, dc = drag
                copy = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
                moves = [
                    (self.people[c][0].id, self.people[c + dc][0].id, self.row_time(r0), self.row_time(r1 + 1))
                    for c, r0, r1 in blocks
                ]
                self.cells_moved.emit(moves, dr * self.team.settings.slot_minutes, copy)
                self.select_blocks([(c + dc, r0 + dr, r1 + dr) for c, r0, r1 in blocks])
            self._cancel_gesture()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        self._resize = self._press = self._drag = None
        idx = self.indexAt(event.position().toPoint())
        if idx.isValid() and event.button() == Qt.MouseButton.LeftButton:
            self.cell_activated.emit(idx.row(), idx.column())
            return
        super().mouseDoubleClickEvent(event)

    def leaveEvent(self, event) -> None:
        if not (self._resize or self._press):
            self.viewport().unsetCursor()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self._resize and self._resize["new"] is not None or self._drag and self._drag != (0, 0):
            p = QPainter(self.viewport())
            if self._resize:
                color = QColor(self.team.task_color(self._resize["run"].segment.task))
                color.setAlpha(170)
                rects = [(self._block_rect(self._resize["col"], *self._resize["rows"]), color)]
            else:
                dr, dc = self._drag
                rects = [(self._block_rect(c + dc, r0 + dr, r1 + dr), SELECT_OVERLAY) for c, r0, r1 in self._move_blocks]
            for rect, fill in rects:
                p.fillRect(rect, fill)
                p.setPen(QPen(SELECT_BORDER, 2, Qt.PenStyle.DashLine))
                p.drawRect(rect.adjusted(1, 1, -1, -1))
            p.end()
        if self.columnCount() == 0:
            p = QPainter(self.viewport())
            p.setPen(QColor("#6b7784"))
            f = QFont(self.font())
            f.setPointSizeF(f.pointSizeF() + 2)
            p.setFont(f)
            p.drawText(
                self.viewport().rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Nobody is checked in yet.\nTick the people working today in the Roster on the left.",
            )
            p.end()
