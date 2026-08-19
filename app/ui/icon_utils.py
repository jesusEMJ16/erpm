"""Icon helpers for loading and scaling the app logo consistently."""

from __future__ import annotations

import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QImage, QPixmap

_ICON_FILENAMES = ("ERP-42.ico", "ERP 42.png")


def _icon_path() -> str:
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ICONS"))
    for name in _ICON_FILENAMES:
        path = os.path.join(base, name)
        if os.path.exists(path):
            return path
    return os.path.join(base, _ICON_FILENAMES[0])


def _crop_transparent(image: QImage) -> QImage:
    if image.isNull() or not image.hasAlphaChannel():
        return image

    width = image.width()
    height = image.height()
    left = width
    right = -1
    top = height
    bottom = -1

    for y in range(height):
        for x in range(width):
            if image.pixelColor(x, y).alpha() > 0:
                if x < left:
                    left = x
                if x > right:
                    right = x
                if y < top:
                    top = y
                if y > bottom:
                    bottom = y

    if right == -1:
        return image

    return image.copy(left, top, right - left + 1, bottom - top + 1)


def load_logo_pixmap(target_size: int) -> QPixmap | None:
    path = _icon_path()
    icon = QIcon(path)
    if not icon.isNull():
        pixmap = icon.pixmap(target_size, target_size)
        if not pixmap.isNull():
            image = _crop_transparent(pixmap.toImage())
            pixmap = QPixmap.fromImage(image)
            return pixmap.scaled(
                target_size, target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )

    image = QImage(path)
    if image.isNull():
        return None
    image = _crop_transparent(image)
    pixmap = QPixmap.fromImage(image)
    return pixmap.scaled(
        target_size, target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
    )


def load_app_icon() -> QIcon:
    path = _icon_path()
    icon = QIcon(path)
    base_pixmap = None
    if not icon.isNull():
        base_pixmap = icon.pixmap(512, 512)
        if base_pixmap.isNull():
            base_pixmap = icon.pixmap(256, 256)

    if base_pixmap is None or base_pixmap.isNull():
        image = QImage(path)
        if image.isNull():
            return QIcon()
        base_pixmap = QPixmap.fromImage(image)

    image = _crop_transparent(base_pixmap.toImage())
    base = QPixmap.fromImage(image)
    built = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256, 512):
        built.addPixmap(
            base.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
    return built
