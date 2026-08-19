"""Custom title bar for frameless windows. (Restored to EXACT BLACKDB pattern)"""

from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt

from app.core.theme import ON_SURFACE


class TitleBar(QFrame):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("title_bar")
        self.setFixedHeight(34)
        self._drag_pos = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 8, 0)
        layout.setSpacing(8)

        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet(
            f"color: {ON_SURFACE}; font-size: 12px; font-weight: 600;"
        )
        self.title_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout.addWidget(self.title_lbl)
        layout.addStretch()

        self.min_btn = QPushButton("-")
        self.min_btn.setObjectName("title_btn")
        self.min_btn.setFixedSize(28, 22)
        self.min_btn.clicked.connect(self._minimize)

        self.max_btn = QPushButton("[]")
        self.max_btn.setObjectName("title_btn")
        self.max_btn.setFixedSize(28, 22)
        self.max_btn.clicked.connect(self._toggle_maximize)

        self.close_btn = QPushButton("x")
        self.close_btn.setObjectName("title_btn_close")
        self.close_btn.setFixedSize(28, 22)
        self.close_btn.clicked.connect(self._close)

        layout.addWidget(self.min_btn)
        layout.addWidget(self.max_btn)
        layout.addWidget(self.close_btn)

    def set_title(self, title: str) -> None:
        self.title_lbl.setText(title)

    def _window(self):
        return self.window()

    def _minimize(self):
        self._window().showMinimized()

    def _toggle_maximize(self):
        window = self._window()
        if window.isMaximized():
            window.showNormal()
        else:
            window.showMaximized()

    def _close(self):
        self._window().close()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            window = self._window()
            self._drag_pos = event.globalPos() - window.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos and (event.buttons() & Qt.LeftButton):
            window = self._window()
            if window.isMaximized():
                window.showNormal()
                self._drag_pos = event.globalPos() - window.frameGeometry().topLeft()
            window.move(event.globalPos() - self._drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._toggle_maximize()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)