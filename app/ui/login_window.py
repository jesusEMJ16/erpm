"""Login window matching the BLACKDB interface and behavior."""

from __future__ import annotations

from PyQt5.QtCore import QEasingCurve, QPropertyAnimation, QTimer, Qt
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizeGrip,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.core.theme import APP_STYLE, ON_SEC_CONT, SURFACE
from app.core.windowing import MIN_SIZE
from app.ui.icon_utils import load_logo_pixmap
from app.ui.widgets.title_bar import TitleBar


class IconLineEdit(QFrame):
    """A QLineEdit wrapped in a frame with a left icon label."""

    _FRAME_NORMAL = (
        "QFrame#input_frame {"
        "  background-color: #171717;"
        "  border: 1px solid rgba(138,138,138,0.55);"
        "  border-radius: 4px;"
        "}"
    )
    _FRAME_FOCUS = (
        "QFrame#input_frame {"
        "  background-color: #171717;"
        "  border: 1px solid rgba(172,172,172,0.9);"
        "  border-radius: 4px;"
        "}"
    )

    def __init__(self, icon: str, placeholder: str, echo_mode=QLineEdit.Normal, parent=None):
        super().__init__(parent)
        self.setObjectName("input_frame")
        self.setFixedHeight(48)
        self.setStyleSheet(self._FRAME_NORMAL)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(6)

        self.icon_lbl = QLabel(icon)
        self.icon_lbl.setFixedWidth(28)
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        self.icon_lbl.setStyleSheet(
            "color: rgba(235,235,235,0.88); font-size: 15px; background: transparent;"
        )

        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        self.edit.setEchoMode(echo_mode)
        self.edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.edit.setStyleSheet(
            "QLineEdit {"
            "  background: transparent;"
            "  border: none;"
            "  color: #e8e8e8;"
            "  font-size: 13px;"
            "  padding: 0px 4px;"
            "}"
            "QLineEdit::placeholder { color: rgba(120,120,130,0.7); }"
        )
        self.edit.installEventFilter(self)

        layout.addWidget(self.icon_lbl)
        layout.addWidget(self.edit)

        if echo_mode == QLineEdit.Password:
            self.toggle_btn = QPushButton("👁")
            self.toggle_btn.setFixedSize(28, 28)
            self.toggle_btn.setStyleSheet(
                "background: transparent; color: rgba(235,235,235,0.86); "
                "border: none; font-size: 13px;"
            )
            self.toggle_btn.setCursor(Qt.PointingHandCursor)
            self.toggle_btn.clicked.connect(self._toggle_visibility)
            layout.addWidget(self.toggle_btn)
            self._visible = False

    def eventFilter(self, obj, event):
        from PyQt5.QtCore import QEvent
        if obj is self.edit:
            if event.type() == QEvent.FocusIn:
                self.setStyleSheet(self._FRAME_FOCUS)
                self.icon_lbl.setStyleSheet(
                    "color: rgba(255,255,255,1.0); font-size: 15px; background: transparent;"
                )
            elif event.type() == QEvent.FocusOut:
                self.setStyleSheet(self._FRAME_NORMAL)
                self.icon_lbl.setStyleSheet(
                    "color: rgba(235,235,235,0.88); font-size: 15px; background: transparent;"
                )
        return super().eventFilter(obj, event)

    def _toggle_visibility(self):
        self._visible = not self._visible
        self.edit.setEchoMode(QLineEdit.Normal if self._visible else QLineEdit.Password)
        self.toggle_btn.setText("🙈" if self._visible else "👁")

    def text(self):
        return self.edit.text()


_LOGIN_CARD_STYLE_DEFAULT = """
    QFrame#login_card {
        background-color: rgba(16, 16, 16, 0.97);
        border: 1px solid rgba(128, 128, 128, 0.5);
        border-radius: 6px;
    }
"""

_LOGIN_CARD_STYLE_ERROR = """
    QFrame#login_card {
        background-color: rgba(16, 16, 16, 0.97);
        border: 1px solid rgba(176, 176, 176, 0.78);
        border-radius: 6px;
    }
"""


class LoginCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("login_card")
        self.setFixedWidth(420)
        self.setStyleSheet(_LOGIN_CARD_STYLE_DEFAULT)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 48, 48, 48)
        layout.setSpacing(0)

        brand_layout = QVBoxLayout()
        brand_layout.setAlignment(Qt.AlignCenter)
        brand_layout.setSpacing(10)

        icon_lbl = QLabel()
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setFixedSize(88, 88)
        pixmap = load_logo_pixmap(78)
        if pixmap is None or pixmap.isNull():
            icon_lbl.setText("🔒")
            icon_lbl.setStyleSheet("font-size: 60px; background: transparent;")
        else:
            icon_lbl.setPixmap(pixmap)
            icon_lbl.setStyleSheet("background: transparent;")

        title_lbl = QLabel("EMINENT")
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet(
            "color: #f4f4f4; font-size: 20px; font-weight: 800; "
            "letter-spacing: 4px; background: transparent;"
        )

        subtitle_lbl = QLabel("SECURE DIGITAL VAULT")
        subtitle_lbl.setAlignment(Qt.AlignCenter)
        subtitle_lbl.setStyleSheet(
            "color: #c8cbd4; font-size: 12px; letter-spacing: 3px; "
            "background: transparent; margin-top: 2px;"
        )

        brand_layout.addWidget(icon_lbl, 0, Qt.AlignHCenter)
        brand_layout.addWidget(title_lbl)
        brand_layout.addWidget(subtitle_lbl)
        layout.addLayout(brand_layout)

        layout.addSpacing(36)

        self.error_slot = QFrame()
        self.error_slot.setFixedHeight(38)
        self.error_slot.setStyleSheet("background: transparent; border: none;")
        error_layout = QVBoxLayout(self.error_slot)
        error_layout.setContentsMargins(0, 0, 0, 0)
        error_layout.setSpacing(0)

        self.error_lbl = QLabel("")
        self.error_lbl.setAlignment(Qt.AlignCenter)
        self.error_lbl.setWordWrap(True)
        self.error_lbl.setStyleSheet(
            "color: #d0d3db; font-size: 12px; font-weight: 500; "
            "background: rgba(139, 0, 0, 0.15); border: 1px solid rgba(140, 140, 140, 0.35); "
            "border-radius: 3px; padding: 8px 12px;"
        )
        self.error_lbl.setVisible(False)
        error_layout.addWidget(self.error_lbl)
        layout.addWidget(self.error_slot)
        layout.addSpacing(12)

        # --- Separator line above fields ---
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(130,130,130,0.45); border: none;")
        layout.addWidget(sep)
        layout.addSpacing(20)

        user_lbl = QLabel("USERNAME")
        user_lbl.setStyleSheet(
            "color: rgba(244,244,244,0.94); font-size: 9px; font-weight: 700; "
            "letter-spacing: 3px; background: transparent;"
        )
        layout.addWidget(user_lbl)
        layout.addSpacing(5)

        self.username_input = IconLineEdit("👤", "Enter your username")
        layout.addWidget(self.username_input)

        layout.addSpacing(18)

        pwd_header = QHBoxLayout()
        pwd_lbl = QLabel("PASSWORD")
        pwd_lbl.setStyleSheet(
            "color: rgba(244,244,244,0.94); font-size: 9px; font-weight: 700; "
            "letter-spacing: 3px; background: transparent;"
        )
        forgot_btn = QPushButton("Forgot Password?")
        forgot_btn.setStyleSheet(
            "background: transparent; border: none; "
            "color: rgba(236,236,236,0.78); "
            "font-size: 10px; padding: 0;"
        )
        forgot_btn.setCursor(Qt.PointingHandCursor)
        pwd_header.addWidget(pwd_lbl)
        pwd_header.addStretch()
        pwd_header.addWidget(forgot_btn)

        layout.addLayout(pwd_header)
        layout.addSpacing(5)

        self.password_input = IconLineEdit("🔑", "Enter your password", QLineEdit.Password)
        layout.addWidget(self.password_input)

        layout.addSpacing(32)

        self.signin_btn = QPushButton("  Sign In  →")
        self.signin_btn.setObjectName("btn_primary")
        self.signin_btn.setFixedHeight(50)
        self.signin_btn.setCursor(Qt.PointingHandCursor)
        self.signin_btn.setStyleSheet(
            """
            QPushButton#btn_primary {
                background-color: #8b0000;
                color: #ffffff;
                border: 1px solid rgba(150,150,150,0.5);
                border-radius: 2px;
                font-size: 14px;
                font-weight: 700;
                letter-spacing: 2px;
                padding: 0;
            }
            QPushButton#btn_primary:hover {
                background-color: #9e0000;
                border-color: rgba(185,185,185,0.92);
            }
            QPushButton#btn_primary:pressed {
                background-color: #700000;
            }
            """
        )
        layout.addWidget(self.signin_btn)

        hint_lbl = QLabel("Default: admin / admin  |  operator / operator")
        hint_lbl.setAlignment(Qt.AlignCenter)
        hint_lbl.setStyleSheet(
            "color: rgba(120,120,130,0.5); font-size: 10px; "
            "background: transparent; margin-top: 12px;"
        )
        layout.addWidget(hint_lbl)
        # ── Explicit tab order ──────────────────────────────────────
        self.setTabOrder(self.username_input.edit, self.password_input.edit)
        self.setTabOrder(self.password_input.edit, self.signin_btn)

    def show_error(self, message: str):
        self.error_lbl.setText(message)
        self.error_lbl.setVisible(True)

    def hide_error(self):
        self.error_lbl.setVisible(False)


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self._login_in_progress = False
        self.setWindowTitle("EMINENT ERP – Sign In")
        self.setMinimumSize(MIN_SIZE)
        self.setStyleSheet(
            APP_STYLE
            + f"""
            LoginWindow {{
                background-color: #0e0e0e;
            }}
            """
        )
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.title_bar = TitleBar(self.windowTitle(), parent=self)
        root.addWidget(self.title_bar)

        bg_top = QFrame()
        bg_top.setFixedHeight(2)
        bg_top.setStyleSheet("background-color: rgba(160,20,20,0.7);")
        root.addWidget(bg_top)

        center_h = QHBoxLayout()
        center_h.setContentsMargins(0, 14, 0, 0)
        center_h.setAlignment(Qt.AlignCenter)

        center_v = QVBoxLayout()
        center_v.setAlignment(Qt.AlignCenter)
        center_v.setSpacing(20)

        self.card = LoginCard()
        center_v.addWidget(self.card)

        footer = QLabel(
            "© 2026 EMINENT ERP  •  Secure Digital Vault Interface\n"
            "Privacy Policy   Terms of Service   Security Architecture"
        )
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet(
            "color: rgba(66,71,84,0.8); font-size: 10px; "
            "letter-spacing: 1.5px; background: transparent; line-height: 1.8;"
        )
        center_v.addWidget(footer)

        center_h.addLayout(center_v)
        root.addStretch()
        root.addLayout(center_h)
        root.addStretch()
        self.size_grip = QSizeGrip(self)
        root.addWidget(self.size_grip, 0, Qt.AlignRight | Qt.AlignBottom)

        self.card.signin_btn.clicked.connect(self._handle_login)
        self.card.password_input.edit.returnPressed.connect(self._handle_login)
        self.card.username_input.edit.returnPressed.connect(self._handle_login)

        self.card.username_input.edit.textChanged.connect(self._on_input_changed)
        self.card.password_input.edit.textChanged.connect(self._on_input_changed)

    def _on_input_changed(self):
        self.card.hide_error()
        self.card.setStyleSheet(_LOGIN_CARD_STYLE_DEFAULT)

    def _handle_login(self):
        if self._login_in_progress:
            return

        username = self.card.username_input.text().strip()
        password = self.card.password_input.text().strip()

        if not username and not password:
            self.card.show_error("Please enter your username and password.")
            self._shake_card()
            return

        if not username:
            self.card.show_error("Please enter your username.")
            self._shake_card()
            return

        if not password:
            self.card.show_error("Please enter your password.")
            self._shake_card()
            return

        default_credentials = {
            "admin": {"password": "admin", "role": "admin"},
            "operator": {"password": "operator", "role": "operator"},
        }
        normalized_username = username.lower()
        user_auth = default_credentials.get(normalized_username)

        if user_auth is None or password.lower() != user_auth["password"]:
            self.card.show_error("Invalid username or password.")
            self._shake_card()
            return

        self._login_in_progress = True
        self.card.signin_btn.setEnabled(False)
        self._open_dashboard({"username": username, "role": user_auth["role"]})

    def _open_dashboard(self, user: dict):
        from app.ui.shell_window import AppShellWindow
        from app.core.windowing import apply_initial_size, TARGET_SIZE

        try:
            self.main_window = AppShellWindow(
                username=user["username"],
            )
            apply_initial_size(self.main_window, TARGET_SIZE)
            self.main_window.show()
            self.close()
        except Exception:
            self._login_in_progress = False
            self.card.signin_btn.setEnabled(True)
            raise

    def _shake_card(self):
        original = self.card.pos()
        anim = QPropertyAnimation(self.card, b"pos")
        anim.setDuration(300)
        anim.setEasingCurve(QEasingCurve.InOutSine)
        anim.setKeyValueAt(0.0, original)
        anim.setKeyValueAt(0.15, original + type(original)(10, 0))
        anim.setKeyValueAt(0.35, original + type(original)(-10, 0))
        anim.setKeyValueAt(0.55, original + type(original)(6, 0))
        anim.setKeyValueAt(0.75, original + type(original)(-6, 0))
        anim.setKeyValueAt(1.0, original)
        anim.start()
        self._anim = anim

        self.card.setStyleSheet(_LOGIN_CARD_STYLE_ERROR)
        QTimer.singleShot(1500, self._reset_card_border)

    def _reset_card_border(self):
        self.card.setStyleSheet(_LOGIN_CARD_STYLE_DEFAULT)
