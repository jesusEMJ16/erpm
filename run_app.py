"""Entry point for the clean BLACKERP baseline project."""

from __future__ import annotations

import os
import signal
import sys

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QApplication

from app.core.theme import APP_NAME, APP_STYLE, ORG_NAME, default_app_font
from app.ui.icon_utils import load_app_icon
from app.ui.login_window import LoginWindow
from db.db_initializer import initialize_database


def configure_qt_environment() -> None:
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "0")
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "0")
    os.environ.setdefault("QT_SCALE_FACTOR", "1")
    os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")


def main() -> int:
    configure_qt_environment()

    try:
        initialize_database()
    except Exception as exc:
        # Keep UI available even when SQL Server is temporarily unreachable.
        print(f"[BLACKERP] SQL bootstrap warning: {exc}")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    app.setFont(default_app_font())
    app.setWindowIcon(load_app_icon())
    app.setStyleSheet(APP_STYLE)

    try:
        window = LoginWindow()
        window.show()
        print("[BLACKERP] Login window displayed successfully")
    except Exception as exc:
        print(f"[BLACKERP] Error creating/showing login window: {exc}")
        import traceback
        traceback.print_exc()
        return 1

    # Allow Ctrl+C from console to quit cleanly without a traceback.
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    signal_pump = QTimer()
    signal_pump.setInterval(250)
    signal_pump.timeout.connect(lambda: None)
    signal_pump.start()
    app._signal_pump = signal_pump

    print("[BLACKERP] Starting event loop")
    return app.exec_()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)


