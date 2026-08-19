"""Left sidebar navigation used by the app shell."""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout

from app.core.theme import ON_SEC_CONT, ON_SURFACE, PRIMARY, SURFACE_LOWEST


class SideNav(QFrame):
    page_requested = pyqtSignal(str)

    _MAIN_ITEMS = [
        ("dashboard", "Dashboard"),
        ("production", "Produccion en linea"),
        ("shipments", "Shipments"),
        ("traceability", "Trazabilidad"),
        ("reception", "Reception"),
        ("inventory", "Inventory"),
        ("settings", "Settings"),
    ]

    _BOTTOM_ITEMS = [
        ("logout", "Sign Out"),
    ]

    def __init__(self, active_page: str = "dashboard", parent=None):
        super().__init__(parent)
        self.setObjectName("side_nav")
        self.setFixedWidth(240)
        self.setStyleSheet(
            f"QFrame#side_nav {{ background-color: {SURFACE_LOWEST}; }}"
        )

        self._buttons: dict[str, QPushButton] = {}
        self._active = active_page

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._build_brand(root)
        self._build_buttons(root, self._MAIN_ITEMS)

        root.addStretch()
        self._build_divider(root)
        self._build_buttons(root, self._BOTTOM_ITEMS)
        root.addSpacing(16)

    def _build_brand(self, root: QVBoxLayout) -> None:
        frame = QFrame()
        frame.setFixedHeight(96)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(2)

        title = QLabel("EMINENT")
        title.setStyleSheet(
            f"color: {ON_SURFACE}; font-size: 13px; font-weight: 800; letter-spacing: 2px;"
        )
        subtitle = QLabel("ERP CONTROL CENTER")
        subtitle.setStyleSheet(
            f"color: {ON_SEC_CONT}; font-size: 10px; letter-spacing: 1px;"
        )
        marker = QLabel("STATUS: ONLINE")
        marker.setStyleSheet(
            f"color: {PRIMARY}; font-size: 10px; font-weight: 600; letter-spacing: 1px;"
        )

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(4)
        layout.addWidget(marker)
        root.addWidget(frame)

    def _build_divider(self, root: QVBoxLayout) -> None:
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: rgba(90,64,60,0.3); margin: 0 16px;")
        root.addWidget(sep)

    def _build_buttons(self, root: QVBoxLayout, items: list[tuple[str, str]]) -> None:
        for key, label in items:
            btn = QPushButton(label)
            btn.setProperty("active", key == self._active)
            btn.setProperty("nav", True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(44)
            btn.setMinimumWidth(200)
            btn.clicked.connect(lambda checked, page=key: self._on_nav_click(page))
            self._buttons[key] = btn
            root.addWidget(btn)

    def _on_nav_click(self, key: str) -> None:
        self._set_active_state(key)
        self.page_requested.emit(key)

    def _set_active_state(self, key: str) -> None:
        for page, button in self._buttons.items():
            button.setProperty("active", page == key)
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()
        self._active = key

    def set_active_page(self, key: str, emit: bool = False) -> None:
        if emit:
            self._on_nav_click(key)
            return
        self._set_active_state(key)
