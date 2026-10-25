"""Entry point: `uv run stocking-scheduler` or `uv run python -m scheduler`.

`--smoke-test` opens the main window, waits a moment and exits with 0 — used to
verify packaged builds without a person clicking around.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .storage import Storage


def resource_path(relative: str) -> Path:
    """Path to a bundled file (works from source and from a PyInstaller build)."""
    base = getattr(sys, "_MEIPASS", None)
    root = Path(base) if base else Path(__file__).resolve().parent.parent
    return root / relative


def use_light_theme(app: QApplication) -> None:
    """The schedule's colors (task pastels, white grid, navy headers) are fixed, so
    keep the rest of the UI light too — a dark desktop theme would otherwise put
    white text on the pastel task rows."""
    app.setStyle("Fusion")
    hints = app.styleHints()
    if hasattr(hints, "setColorScheme"):  # Qt 6.8+
        hints.setColorScheme(Qt.ColorScheme.Light)
    app.setPalette(app.style().standardPalette())


def main() -> int:
    # Imported here so a broken Qt install produces a readable error rather than
    # failing while the module is still loading.
    from .ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Stocking Scheduler")
    use_light_theme(app)
    icon = resource_path("assets/icon.png")
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))
    font = app.font()
    if font.pointSizeF() < 10:
        font.setPointSizeF(10)
        app.setFont(font)

    window = MainWindow(Storage())
    window.show()

    if "--smoke-test" in sys.argv:
        QTimer.singleShot(1500, app.quit)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
