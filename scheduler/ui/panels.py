"""Left-hand panels: the roster (who is working today) and the task palette."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QSize, QEvent
from PySide6.QtGui import QFont, QColor, QBrush
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QAbstractItemView,
)

from ..models import Team, Day, CATEGORIES, ROLE_PICKER
from .dialogs import color_icon

QUICK_KEYS = 5  # tasks reachable with the number keys 1..5
KIND = Qt.ItemDataRole.UserRole + 1  # palette row kind: "head", "quick" or "task"


def section_label(text: str) -> QLabel:
    lab = QLabel(text)
    lab.setStyleSheet(
        "QLabel { background: #0b2a4a; color: white; font-weight: bold; padding: 4px 8px; }"
    )
    return lab


class RosterPanel(QWidget):
    """Checkbox list of the whole team. Checked = working today."""

    working_toggled = Signal(str, bool)  # assoc id, on
    add_requested = Signal()
    edit_requested = Signal(str)
    remove_requested = Signal(str)
    move_requested = Signal(str, int)  # id, delta (-1 up / +1 down)
    day_details_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.team: Team | None = None
        self.day: Day | None = None
        self._building = False

        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list.itemChanged.connect(self._item_changed)
        self.list.itemDoubleClicked.connect(self._double_clicked)
        self.list.setToolTip(
            "Check the people working today — each one gets a column in the grid.\n"
            "Double-click a person to edit today's duty / aisles / shift."
        )

        btns = QHBoxLayout()
        btns.setSpacing(4)
        self.add_btn = QPushButton("Add")
        self.edit_btn = QPushButton("Edit")
        self.remove_btn = QPushButton("Remove")
        self.up_btn = QToolButton()
        self.up_btn.setText("▲")
        self.down_btn = QToolButton()
        self.down_btn.setText("▼")
        for b in (self.add_btn, self.edit_btn, self.remove_btn):
            btns.addWidget(b)
        btns.addStretch(1)
        btns.addWidget(self.up_btn)
        btns.addWidget(self.down_btn)
        self.add_btn.clicked.connect(self.add_requested)
        self.edit_btn.clicked.connect(lambda: self._emit_for_current(self.edit_requested))
        self.remove_btn.clicked.connect(lambda: self._emit_for_current(self.remove_requested))
        self.up_btn.clicked.connect(lambda: self._move(-1))
        self.down_btn.clicked.connect(lambda: self._move(+1))

        quick = QHBoxLayout()
        self.all_btn = QPushButton("Everyone in")
        self.core_btn = QPushButton("Core team")
        self.none_btn = QPushButton("Nobody")
        for b in (self.all_btn, self.core_btn, self.none_btn):
            b.setToolTip("Quickly set who is working today")
            quick.addWidget(b)
        self.all_btn.clicked.connect(lambda: self._bulk(lambda a: True))
        self.core_btn.clicked.connect(lambda: self._bulk(lambda a: not a.optional))
        self.none_btn.clicked.connect(lambda: self._bulk(lambda a: False))

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lay.addWidget(section_label("ROSTER — check who is working today"))
        lay.addWidget(self.list, 1)
        lay.addLayout(quick)
        lay.addLayout(btns)

    def set_data(self, team: Team, day: Day) -> None:
        self.team, self.day = team, day
        self.rebuild()

    def rebuild(self) -> None:
        if self.team is None or self.day is None:
            return
        self._building = True
        current = self.current_id()
        self.list.clear()
        for a in self.team.associates:
            it = QListWidgetItem()
            it.setData(Qt.ItemDataRole.UserRole, a.id)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            on = self.day.is_working(a.id)
            it.setCheckState(Qt.CheckState.Checked if on else Qt.CheckState.Unchecked)
            w = self.day.day_assoc(a.id)
            duty = (w.duty if w else a.duty) or ""
            # One line per person; the role is left out when the name already says
            # it ("Stocker 1"), and the picker is marked by its icon anyway.
            bits = [a.name]
            if a.role.lower() not in a.name.lower():
                bits.append(a.role)
            if a.optional:
                bits.append("optional")
            if duty:
                bits.append(duty)
            it.setText(" · ".join(bits))
            it.setToolTip(" · ".join([a.name, a.role, *(["optional"] if a.optional else []), *([duty] if duty else [])]))
            f = QFont(self.font())
            f.setBold(on)
            it.setFont(f)
            if a.role == ROLE_PICKER:
                it.setIcon(color_icon("#1f4e79", 12))
            if not on:
                it.setForeground(QBrush(QColor("#7a7a7a")))
            self.list.addItem(it)
            if a.id == current:
                self.list.setCurrentItem(it)
        self._building = False

    def current_id(self) -> str | None:
        it = self.list.currentItem()
        return it.data(Qt.ItemDataRole.UserRole) if it else None

    def _emit_for_current(self, sig) -> None:
        aid = self.current_id()
        if aid:
            sig.emit(aid)

    def _move(self, delta: int) -> None:
        aid = self.current_id()
        if aid:
            self.move_requested.emit(aid, delta)

    def _item_changed(self, it: QListWidgetItem) -> None:
        if self._building:
            return
        self.working_toggled.emit(it.data(Qt.ItemDataRole.UserRole), it.checkState() == Qt.CheckState.Checked)

    def _double_clicked(self, it: QListWidgetItem) -> None:
        aid = it.data(Qt.ItemDataRole.UserRole)
        if self.day and self.day.is_working(aid):
            self.day_details_requested.emit(aid)
        else:
            self.edit_requested.emit(aid)

    def _bulk(self, pred) -> None:
        if self.team is None:
            return
        for a in self.team.associates:
            self.working_toggled.emit(a.id, bool(pred(a)))


class TaskPalette(QWidget):
    """Colored list of tasks. Clicking one paints it onto the selected cells."""

    task_clicked = Signal(str)
    new_task = Signal()
    edit_task = Signal(str)
    delete_task = Signal(str)
    clear_clicked = Signal()
    forget_quick = Signal(str)  # remove a task from the quick keys
    required_toggled = Signal(str, bool)  # task name, Required ticked
    search_done = Signal()  # Enter / Esc in the search box: hand focus back to the grid

    def __init__(self, parent=None):
        super().__init__(parent)
        self.team: Team | None = None
        self.search = QLineEdit()
        self.search.setPlaceholderText("Find a task…  (or just start typing in the grid)")
        self.search.setClearButtonEnabled(True)
        self.search.setToolTip("Type part of a task name, then press Enter to fill the selected cells")
        self.search.textChanged.connect(self._filter)
        self.search.returnPressed.connect(self._search_enter)
        self.search.installEventFilter(self)
        self.list = QListWidget()
        self.list.setIconSize(QSize(16, 16))
        self.list.itemClicked.connect(self._clicked)
        self.list.itemDoubleClicked.connect(self._double_clicked)
        self.list.setToolTip(
            "Select cells in the grid, then click a task here to fill them.\n"
            "Double-click a task to edit its name or color."
        )
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._context)

        btns = QHBoxLayout()
        btns.setSpacing(4)
        self.new_btn = QPushButton("New task…")
        self.clear_btn = QPushButton("Clear cells")
        self.clear_btn.setToolTip("Empty the selected cells (Delete key does the same)")
        btns.addWidget(self.new_btn)
        btns.addWidget(self.clear_btn)
        self.new_btn.clicked.connect(self.new_task)
        self.clear_btn.clicked.connect(self.clear_clicked)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lay.addWidget(section_label("TASKS — select cells, then click to fill"))
        lay.addWidget(self.search)
        lay.addWidget(self.list, 1)
        lay.addLayout(btns)

    def set_team(self, team: Team) -> None:
        self.team = team
        self.rebuild()

    def quick_tasks(self) -> list[str]:
        """Task names on the number keys, in key order (deleted tasks skipped)."""
        if self.team is None:
            return []
        return [n for n in self.team.settings.quick_tasks if self.team.task(n)][:QUICK_KEYS]

    def _head(self, text: str) -> None:
        head = QListWidgetItem(text)
        head.setFlags(Qt.ItemFlag.NoItemFlags)
        head.setData(KIND, "head")
        f = QFont(self.font())
        f.setBold(True)
        f.setPointSizeF(max(7.0, f.pointSizeF() - 1))
        head.setFont(f)
        head.setForeground(QBrush(QColor("#5b6773")))
        self.list.addItem(head)

    def _task_item(self, name: str, text: str, kind: str) -> None:
        color = self.team.task_color(name)
        it = QListWidgetItem(color_icon(color, 16), text)
        it.setData(Qt.ItemDataRole.UserRole, name)
        it.setData(KIND, kind)
        it.setBackground(QBrush(QColor(color).lighter(112)))
        self.list.addItem(it)
        if kind == "task":
            self._add_required_box(it, name)

    def _add_required_box(self, it: QListWidgetItem, name: str) -> None:
        """A "Required" checkbox at the right end of a task's row. Clicks beside
        the box fall through the holder to the row, which still applies the task."""
        box = QCheckBox("Required")
        box.setChecked(self.team.task(name).required)
        box.setToolTip("Required: Check Sheet flags it if nobody working today is assigned this task")
        f = QFont(self.font())
        f.setPointSizeF(max(7.0, f.pointSizeF() - 1.5))
        box.setFont(f)
        box.setStyleSheet("QCheckBox { color: #5b6773; } QCheckBox:checked { color: #8a1c1c; font-weight: bold; }")
        box.toggled.connect(lambda on, n=name: self.required_toggled.emit(n, on))
        holder = QWidget()
        row = QHBoxLayout(holder)
        row.setContentsMargins(0, 0, 4, 0)
        row.addStretch(1)
        row.addWidget(box)
        self.list.setItemWidget(it, holder)

    def rebuild(self) -> None:
        if self.team is None:
            return
        self.list.clear()
        quick = self.quick_tasks()
        if quick:
            self._head(f"QUICK KEYS — press 1–{len(quick)} in the grid")
            for i, name in enumerate(quick, start=1):
                self._task_item(name, f"{i}   {name}", "quick")
        for cat in CATEGORIES:
            tasks = [t for t in self.team.tasks if t.category == cat]
            if not tasks:
                continue
            self._head(cat.upper())
            for t in tasks:
                self._task_item(t.name, t.name, "task")
        self._filter(self.search.text())

    # --- search -----------------------------------------------------------------
    def _filter(self, text: str) -> None:
        """Show only tasks whose name contains `text`; hide the quick keys and
        any category left empty while searching."""
        needle = text.strip().lower()
        items = [self.list.item(i) for i in range(self.list.count())]
        for it in items:
            kind = it.data(KIND)
            if kind == "quick":
                it.setHidden(bool(needle))
            elif kind == "task":
                it.setHidden(needle not in it.data(Qt.ItemDataRole.UserRole).lower())
        for i, it in enumerate(items):
            if it.data(KIND) == "head":
                section = []
                for nxt in items[i + 1:]:
                    if nxt.data(KIND) == "head":
                        break
                    section.append(nxt)
                it.setHidden(all(x.isHidden() for x in section))

    def start_search(self, text: str) -> None:
        self.search.setFocus()
        self.search.setText(text)

    def _search_enter(self) -> None:
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it.data(KIND) == "task" and not it.isHidden():
                self.search.clear()
                self.task_clicked.emit(it.data(Qt.ItemDataRole.UserRole))
                break
        self.search_done.emit()

    def eventFilter(self, obj, event) -> bool:
        if obj is self.search and event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
            self.search.clear()
            self.search_done.emit()
            return True
        return super().eventFilter(obj, event)

    def _clicked(self, it: QListWidgetItem) -> None:
        name = it.data(Qt.ItemDataRole.UserRole)
        if name:
            self.task_clicked.emit(name)
        self.list.clearSelection()

    def _double_clicked(self, it: QListWidgetItem) -> None:
        name = it.data(Qt.ItemDataRole.UserRole)
        if name:
            self.edit_task.emit(name)

    def _context(self, pos) -> None:
        from PySide6.QtWidgets import QMenu

        it = self.list.itemAt(pos)
        name = it.data(Qt.ItemDataRole.UserRole) if it else None
        menu = QMenu(self)
        menu.addAction("New task…", self.new_task.emit)
        if name:
            menu.addAction(f"Edit '{name}'…", lambda: self.edit_task.emit(name))
            menu.addAction(f"Delete '{name}'", lambda: self.delete_task.emit(name))
            if it.data(KIND) == "quick":
                menu.addAction("Remove from quick keys", lambda: self.forget_quick.emit(name))
        menu.exec(self.list.mapToGlobal(pos))
