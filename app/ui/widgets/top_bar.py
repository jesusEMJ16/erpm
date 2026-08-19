"""Top application bar with quick actions."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QMessageBox, QPushButton

from app.core.theme import ON_SURFACE, ON_SEC_CONT, PRIMARY, SURFACE, SURFACE_BRIGHT


class TopBar(QFrame):
    def __init__(self, title: str = "EMINENT ERP", username: str = "Admin", on_open_settings=None, parent=None):
        super().__init__(parent)
        self.setObjectName("top_bar")
        self.setFixedHeight(56)
        self._on_open_settings = on_open_settings

        self.setStyleSheet(
            f"""
            QFrame#top_bar {{
                background-color: {SURFACE};
                border-bottom: 1px solid rgba(90,64,60,0.25);
            }}
            """
        )

        root = QHBoxLayout(self)
        root.setContentsMargins(20, 0, 20, 0)
        root.setSpacing(10)

        title_lbl = QLabel(title)
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet(
            f"color: {PRIMARY}; font-size: 12px; font-weight: 800; letter-spacing: 3px;"
        )

        root.addWidget(title_lbl)
        root.addStretch()

        notif_btn = self._icon_button("N", "Notifications", self._show_notifications)
        settings_btn = self._icon_button("S", "Settings", self._show_settings)

        initials = (username[:2] or "US").upper()
        avatar_lbl = QLabel(initials)
        avatar_lbl.setAlignment(Qt.AlignCenter)
        avatar_lbl.setFixedSize(32, 32)
        avatar_lbl.setStyleSheet(
            f"""
            color: {PRIMARY};
            background-color: rgba(139,0,0,0.4);
            border: 1px solid rgba(255,180,168,0.3);
            border-radius: 2px;
            font-size: 11px;
            font-weight: 700;
            """
        )

        root.addWidget(notif_btn)
        root.addWidget(settings_btn)
        root.addSpacing(4)
        root.addWidget(avatar_lbl)

    def _icon_button(self, text: str, tooltip: str, callback):
        btn = QPushButton(text)
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedSize(36, 36)
        btn.clicked.connect(callback)
        btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                color: {ON_SURFACE};
                border: none;
                border-radius: 2px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {SURFACE_BRIGHT};
                color: {PRIMARY};
            }}
            """
        )
        return btn

    def _show_notifications(self):
        QMessageBox.information(self, "Notifications", "No new notifications.")

    def _show_settings(self):
        if self._on_open_settings:
            self._on_open_settings()
            return
        QMessageBox.information(self, "Settings", "Settings action is not configured.")
