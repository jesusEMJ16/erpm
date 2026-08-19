"""Reusable helpers for initial window sizing and transitions."""

from __future__ import annotations

from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QApplication

TARGET_SIZE = QSize(1600, 900)
MIN_SIZE = QSize(900, 600)


def apply_initial_size(window, size: QSize | None = None) -> None:
    target = size or TARGET_SIZE
    window.resize(target)


def show_inherited(window, source=None) -> None:
    """Transfer position/size from source to window (BLACKDB pattern)."""
    if source is not None and source.isMaximized():
        window.showMaximized()
        return
    if source is not None:
        window.showNormal()
        window.setGeometry(source.geometry())
    window.show()
