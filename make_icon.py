"""Draw the app icon into assets/ (icon.png, icon.ico, icon.icns).

Run once with `uv run python make_icon.py`; the files are committed so the
normal build doesn't need to regenerate them.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter

ASSETS = Path(__file__).resolve().parent / "assets"

# Three columns of colored blocks, like the schedule grid.
COLUMNS = [
    [("#cfe0f2", 0.30), ("#f9d3b5", 0.10), ("#cdebd6", 0.35), ("#f6b98a", 0.25)],
    [("#cfe0f2", 0.30), ("#fff0b3", 0.25), ("#cdebd6", 0.20), ("#f6b98a", 0.25)],
    [("#e0d4f5", 0.45), ("#f9d3b5", 0.10), ("#cdebd6", 0.45)],
]


def draw(size: int) -> QImage:
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    r = size * 0.18
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#0b2a4a"))
    p.drawRoundedRect(QRectF(0, 0, size, size), r, r)

    pad = size * 0.14
    header = size * 0.16
    gap = size * 0.035
    inner_w = size - 2 * pad
    col_w = (inner_w - gap * (len(COLUMNS) - 1)) / len(COLUMNS)
    top = pad + header
    height = size - pad - top
    for i, col in enumerate(COLUMNS):
        x = pad + i * (col_w + gap)
        # column header stripe
        p.setBrush(QColor("#1f4e79"))
        p.drawRoundedRect(QRectF(x, pad, col_w, header - gap), size * 0.02, size * 0.02)
        y = top
        for color, frac in col:
            h = height * frac - gap * 0.6
            p.setBrush(QColor(color))
            p.drawRoundedRect(QRectF(x, y, col_w, h), size * 0.02, size * 0.02)
            y += height * frac
    p.end()
    return img


def main() -> None:
    QGuiApplication(sys.argv)
    ASSETS.mkdir(exist_ok=True)
    big = draw(512)
    big.save(str(ASSETS / "icon.png"))
    ok_ico = draw(256).save(str(ASSETS / "icon.ico"))
    ok_icns = big.save(str(ASSETS / "icon.icns"))
    print("png ok, ico", ok_ico, ", icns", ok_icns)


if __name__ == "__main__":
    main()
