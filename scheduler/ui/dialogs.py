"""All the small dialogs: assign task, edit associate, edit task, settings…"""

from __future__ import annotations

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QPixmap, QIcon, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..models import (
    Team,
    Day,
    Associate,
    DayAssociate,
    Task,
    Segment,
    ROLES,
    ROLE_STOCKER,
    CATEGORIES,
    CATEGORY_COLORS,
    minutes_to_label,
    label_to_minutes,
    working_associates,
)


def color_icon(hex_color: str, size: int = 14) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setPen(QPen(QColor(hex_color).darker(140), 1))
    p.setBrush(QColor(hex_color))
    p.drawRoundedRect(0, 0, size - 1, size - 1, 3, 3)
    p.end()
    return QIcon(pm)


def fill_task_combo(combo: QComboBox, team: Team, current: str | None = None) -> None:
    combo.clear()
    for cat in CATEGORIES:
        names = [t for t in team.tasks if t.category == cat]
        if not names:
            continue
        for t in names:
            combo.addItem(color_icon(t.effective_color()), t.name)
    # tasks that exist in the schedule but were deleted from the list
    if current and combo.findText(current) < 0:
        combo.addItem(color_icon("#dddddd"), current)
    if current:
        combo.setCurrentText(current)
    combo.setIconSize(QSize(14, 14))


class TimeCombo(QComboBox):
    """Editable combo listing the grid's slot times; accepts typed times too."""

    def __init__(self, minutes: list[int], parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self._minutes = minutes
        for m in minutes:
            self.addItem(minutes_to_label(m, ampm=True), m)
        self.setMinimumWidth(110)

    def minutes(self) -> int | None:
        idx = self.currentIndex()
        if idx >= 0 and self.itemText(idx) == self.currentText():
            return self.itemData(idx)
        return label_to_minutes(self.currentText())

    def set_minutes(self, m: int) -> None:
        idx = self.findData(m)
        if idx >= 0:
            self.setCurrentIndex(idx)
        else:
            self.setEditText(minutes_to_label(m, ampm=True))


class AssignDialog(QDialog):
    """Assign one task to any number of people over a time range."""

    def __init__(self, team: Team, day: Day, parent=None, task: str | None = None,
                 start: int | None = None, end: int | None = None, people: list[str] | None = None):
        super().__init__(parent)
        self.setWindowTitle("Assign Task")
        self.team, self.day = team, day
        s = team.settings
        slots = s.slots()
        ends = [m + s.slot_minutes for m in slots]

        self.task = QComboBox()
        fill_task_combo(self.task, team, task)
        new_btn = QPushButton("New task…")
        new_btn.clicked.connect(self._new_task)
        trow = QHBoxLayout()
        trow.addWidget(self.task, 1)
        trow.addWidget(new_btn)

        self.start = TimeCombo(slots)
        self.end = TimeCombo(ends)
        self.start.set_minutes(start if start is not None else slots[0])
        self.end.set_minutes(end if end is not None else slots[0] + s.slot_minutes)
        time_row = QHBoxLayout()
        time_row.addWidget(QLabel("From"))
        time_row.addWidget(self.start)
        time_row.addWidget(QLabel("to"))
        time_row.addWidget(self.end)
        time_row.addStretch(1)

        self.note = QLineEdit()
        self.note.setPlaceholderText("optional — e.g. '70 cases', 'Joe C helps'")

        self.people = QListWidget()
        self.people.setMinimumHeight(160)
        for a, w in working_associates(team, day):
            it = QListWidgetItem(f"{a.name}   ({a.role}{' · ' + w.duty if w.duty else ''})")
            it.setData(Qt.ItemDataRole.UserRole, a.id)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked if people and a.id in people else Qt.CheckState.Unchecked)
            self.people.addItem(it)
        quick = QHBoxLayout()
        for label, fn in (("Everyone", self._all), ("Stockers only", self._stockers), ("None", self._none)):
            b = QPushButton(label)
            b.clicked.connect(fn)
            quick.addWidget(b)
        quick.addStretch(1)

        form = QFormLayout()
        form.addRow("Task", trow)
        form.addRow("Time", time_row)
        form.addRow("Note", self.note)
        form.addRow("People", self.people)
        form.addRow("", quick)

        self.buttons = QDialogButtonBox()
        self.apply_btn = self.buttons.addButton("Assign", QDialogButtonBox.ButtonRole.ApplyRole)
        self.apply_btn.setDefault(True)
        self.buttons.addButton(QDialogButtonBox.StandardButton.Close)
        self.buttons.rejected.connect(self.reject)
        self.apply_btn.clicked.connect(self._apply)

        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(QLabel("<i>Tip: you can also select cells in the grid and click a task in the palette.</i>"))
        lay.addWidget(self.buttons)
        self.resize(520, 480)
        self.applied = False  # set when at least one assignment was made

    def _set_all(self, pred):
        for i in range(self.people.count()):
            it = self.people.item(i)
            on = pred(self.team.get(it.data(Qt.ItemDataRole.UserRole)))
            it.setCheckState(Qt.CheckState.Checked if on else Qt.CheckState.Unchecked)

    def _all(self):
        self._set_all(lambda a: True)

    def _stockers(self):
        self._set_all(lambda a: a is not None and a.role == ROLE_STOCKER)

    def _none(self):
        self._set_all(lambda a: False)

    def _new_task(self):
        dlg = TaskDialog(self.team, parent=self)
        if dlg.exec():
            self.team.tasks.append(dlg.result_task())
            fill_task_combo(self.task, self.team, dlg.result_task().name)
            self.parent().team_changed()  # type: ignore[attr-defined]

    def selected_ids(self) -> list[str]:
        return [
            self.people.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.people.count())
            if self.people.item(i).checkState() == Qt.CheckState.Checked
        ]

    def _apply(self):
        start, end = self.start.minutes(), self.end.minutes()
        if start is None or end is None:
            QMessageBox.warning(self, "Time", "Enter times like 9:15 or 1:30 PM.")
            return
        if end <= start:
            QMessageBox.warning(self, "Time", "The end time must be after the start time.")
            return
        ids = self.selected_ids()
        if not ids:
            QMessageBox.warning(self, "People", "Check at least one person.")
            return
        task = self.task.currentText().strip()
        if not task:
            return
        self.parent().assign(ids, start, end, task, self.note.text().strip())  # type: ignore[attr-defined]
        self.applied = True
        # keep the dialog open for the next assignment; advance the time window
        length = end - start
        self.start.set_minutes(end)
        self.end.set_minutes(end + length)
        self.note.clear()


class BlockDialog(QDialog):
    """Edit one block (task / note / time) for a single associate."""

    def __init__(self, team: Team, assoc: Associate, seg: Segment | None, start: int, end: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{assoc.name} — edit block")
        s = team.settings
        slots = s.slots()
        self.task = QComboBox()
        fill_task_combo(self.task, team, seg.task if seg else None)
        self.note = QLineEdit(seg.note if seg else "")
        self.note.setPlaceholderText("optional")
        self.start = TimeCombo(slots)
        self.end = TimeCombo([m + s.slot_minutes for m in slots])
        self.start.set_minutes(seg.start if seg else start)
        self.end.set_minutes(seg.end if seg else end)
        trow = QHBoxLayout()
        trow.addWidget(self.start)
        trow.addWidget(QLabel("to"))
        trow.addWidget(self.end)
        form = QFormLayout(self)
        form.addRow("Task", self.task)
        form.addRow("Note", self.note)
        form.addRow("Time", trow)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        if seg:
            clear = bb.addButton("Clear block", QDialogButtonBox.ButtonRole.DestructiveRole)
            clear.clicked.connect(self._clear)
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        form.addRow(bb)
        self.cleared = False

    def _clear(self):
        self.cleared = True
        self.accept()

    def _ok(self):
        a, b = self.start.minutes(), self.end.minutes()
        if a is None or b is None or b <= a:
            QMessageBox.warning(self, "Time", "Enter a valid time range.")
            return
        self.accept()

    def values(self) -> tuple[str, str, int, int]:
        return self.task.currentText().strip(), self.note.text().strip(), self.start.minutes(), self.end.minutes()


class AssociateDialog(QDialog):
    """Add / edit a roster member."""

    def __init__(self, assoc: Associate | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Associate" if assoc else "Add Associate")
        self.name = QLineEdit(assoc.name if assoc else "")
        self.role = QComboBox()
        self.role.addItems(ROLES)
        self.role.setCurrentText(assoc.role if assoc else ROLE_STOCKER)
        self.optional = QCheckBox("Optional / floater (only works some days)")
        self.optional.setChecked(bool(assoc and assoc.optional))
        self.duty = QLineEdit(assoc.duty if assoc else "")
        self.duty.setPlaceholderText("e.g. Helps Pick GM")
        self.aisles = QLineEdit(assoc.aisles if assoc else "")
        self.aisles.setPlaceholderText("e.g. A18/A19")
        form = QFormLayout(self)
        form.addRow("Name", self.name)
        form.addRow("Role", self.role)
        form.addRow("", self.optional)
        form.addRow("Usual duty", self.duty)
        form.addRow("Usual topstock aisles", self.aisles)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        form.addRow(bb)
        self.name.setFocus()

    def _ok(self):
        if not self.name.text().strip():
            QMessageBox.warning(self, "Name", "Enter a name.")
            return
        self.accept()

    def apply_to(self, a: Associate) -> None:
        a.name = self.name.text().strip()
        a.role = self.role.currentText()
        a.optional = self.optional.isChecked()
        a.duty = self.duty.text().strip()
        a.aisles = self.aisles.text().strip()


class DayAssociateDialog(QDialog):
    """Per-day details for one associate (duty, aisles, shift)."""

    def __init__(self, team: Team, assoc: Associate, w: DayAssociate, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{assoc.name} — today")
        s = team.settings
        self.duty = QLineEdit(w.duty)
        self.duty.setPlaceholderText("e.g. Helps Pick GM")
        self.aisles = QLineEdit(w.aisles)
        self.aisles.setPlaceholderText("e.g. A18/A19")
        self.shift = QCheckBox("Custom shift (otherwise the whole day)")
        slots = s.slots()
        self.start = TimeCombo(slots)
        self.end = TimeCombo([m + s.slot_minutes for m in slots])
        has = w.shift_start is not None and w.shift_end is not None
        self.shift.setChecked(has)
        self.start.set_minutes(w.shift_start if has else s.day_start)
        self.end.set_minutes(w.shift_end if has else s.day_end)
        self.start.setEnabled(has)
        self.end.setEnabled(has)
        self.shift.toggled.connect(self.start.setEnabled)
        self.shift.toggled.connect(self.end.setEnabled)
        trow = QHBoxLayout()
        trow.addWidget(self.start)
        trow.addWidget(QLabel("to"))
        trow.addWidget(self.end)
        self.save_default = QCheckBox("Also save duty & aisles as this person's usual values")
        form = QFormLayout(self)
        form.addRow(QLabel(f"<b>{assoc.name}</b> · {assoc.role}"))
        form.addRow("Duty today", self.duty)
        form.addRow("Topstock aisles", self.aisles)
        form.addRow("", self.shift)
        form.addRow("Shift", trow)
        form.addRow("", self.save_default)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        form.addRow(bb)

    def apply_to(self, w: DayAssociate, a: Associate) -> None:
        w.duty = self.duty.text().strip()
        w.aisles = self.aisles.text().strip()
        if self.shift.isChecked() and self.start.minutes() is not None and self.end.minutes() is not None:
            w.shift_start, w.shift_end = self.start.minutes(), self.end.minutes()
        else:
            w.shift_start = w.shift_end = None
        if self.save_default.isChecked():
            a.duty, a.aisles = w.duty, w.aisles


class TaskDialog(QDialog):
    """Create or edit a task type (name, category, color)."""

    def __init__(self, team: Team, task: Task | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Task" if task else "New Task")
        self.team, self.original = team, task
        self.name = QLineEdit(task.name if task else "")
        self.category = QComboBox()
        self.category.addItems(CATEGORIES)
        self.category.setCurrentText(task.category if task else CATEGORIES[0])
        self._color = task.effective_color() if task else CATEGORY_COLORS[CATEGORIES[0]]
        self.color_btn = QPushButton()
        self.color_btn.clicked.connect(self._pick_color)
        self.category.currentTextChanged.connect(self._category_changed)
        self._update_swatch()
        form = QFormLayout(self)
        form.addRow("Name", self.name)
        form.addRow("Category", self.category)
        form.addRow("Color", self.color_btn)
        if task:
            form.addRow(QLabel("<i>Renaming updates today's schedule; other days keep the old name.</i>"))
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        form.addRow(bb)
        self.name.setFocus()

    def _category_changed(self, cat: str):
        if self.original is None or not self.original.color:
            self._color = CATEGORY_COLORS.get(cat, self._color)
            self._update_swatch()

    def _update_swatch(self):
        self.color_btn.setIcon(color_icon(self._color, 18))
        self.color_btn.setText(f"  {self._color}   (click to change)")

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(self._color), self, "Task color")
        if c.isValid():
            self._color = c.name()
            self._update_swatch()

    def _ok(self):
        name = self.name.text().strip()
        if not name:
            QMessageBox.warning(self, "Name", "Enter a task name.")
            return
        clash = self.team.task(name)
        if clash and clash is not self.original:
            QMessageBox.warning(self, "Name", f"A task called '{name}' already exists.")
            return
        self.accept()

    def result_task(self) -> Task:
        return Task(self.name.text().strip(), self.category.currentText(), self._color)


class SettingsDialog(QDialog):
    def __init__(self, team: Team, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        s = team.settings
        self.title = QLineEdit(s.title)
        self.start = QLineEdit(minutes_to_label(s.day_start, ampm=True))
        self.end = QLineEdit(minutes_to_label(s.day_end, ampm=True))
        self.slot = QComboBox()
        for m in (10, 15, 20, 30, 60):
            self.slot.addItem(f"{m} minutes", m)
        self.slot.setCurrentIndex(max(0, self.slot.findData(s.slot_minutes)))
        self.footer = QPlainTextEdit(s.footer)
        self.footer.setFixedHeight(70)
        form = QFormLayout(self)
        form.addRow("Sheet title", self.title)
        form.addRow("Day starts", self.start)
        form.addRow("Day ends", self.end)
        form.addRow("Grid rows every", self.slot)
        form.addRow("Footer note", self.footer)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        form.addRow(bb)
        self.resize(520, 300)

    def _ok(self):
        a, b = label_to_minutes(self.start.text()), label_to_minutes(self.end.text())
        if a is None or b is None or b <= a:
            QMessageBox.warning(self, "Times", "Enter valid start/end times, e.g. 7:00 AM and 4:00 PM.")
            return
        self.accept()

    def apply_to(self, team: Team) -> None:
        s = team.settings
        s.title = self.title.text().strip() or s.title
        s.day_start = label_to_minutes(self.start.text())
        s.day_end = label_to_minutes(self.end.text())
        s.slot_minutes = self.slot.currentData()
        s.footer = self.footer.toPlainText().strip()


def pick_from_list(parent: QWidget, title: str, label: str, items: list[str]) -> str | None:
    if not items:
        QMessageBox.information(parent, title, "Nothing to choose from yet.")
        return None
    value, ok = QInputDialog.getItem(parent, title, label, items, 0, False)
    return value if ok and value else None


def ask_text(parent: QWidget, title: str, label: str, default: str = "") -> str | None:
    value, ok = QInputDialog.getText(parent, title, label, text=default)
    value = value.strip()
    return value if ok and value else None
