"""Main shell window with stacked pages and shared navigation."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget

from app.core.theme import APP_NAME
from app.core.windowing import MIN_SIZE, TARGET_SIZE, apply_initial_size, show_inherited
from app.services.settings_store import load_settings
from app.ui.pages.dashboard_page import DashboardPage
from app.ui.pages.inventory_page import InventoryPage
from app.ui.pages.production_page import ProductionPage
from app.ui.pages.reception_page import ReceptionPage
from app.ui.pages.shipments_page import ShipmentsPage
from app.ui.pages.traceability_page import TraceabilityPage
from app.ui.pages.settings_page import SettingsPage
from app.ui.widgets.side_nav import SideNav
from app.ui.widgets.title_bar import TitleBar
from app.ui.widgets.top_bar import TopBar


class AppShellWindow(QWidget):
    def __init__(self, username: str = "Admin", parent=None):
        super().__init__(parent)
        self.username = username
        settings_payload = load_settings()
        startup_page = str(settings_payload.get("startup_page", "dashboard"))
        self._app_title = str(settings_payload.get("company_name", APP_NAME)).strip() or APP_NAME

        allowed_pages = {
            "dashboard",
            "production",
            "shipments",
            "traceability",
            "reception",
            "inventory",
            "settings",
        }
        self._current_page = startup_page if startup_page in allowed_pages else "dashboard"

        initial_title = self._page_title(self._current_page)
        self.setWindowTitle(f"{self._app_title} - {initial_title}")
        self.setMinimumSize(MIN_SIZE)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        apply_initial_size(self, TARGET_SIZE)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.title_bar = TitleBar(self.windowTitle(), parent=self)
        root.addWidget(self.title_bar)

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.nav = SideNav(active_page=self._current_page)
        self.nav.page_requested.connect(self._navigate)
        body_layout.addWidget(self.nav)

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)

        self.top_bar = TopBar(
            title=self._app_title,
            username=username,
            on_open_settings=lambda: self._navigate("settings"),
        )
        right.addWidget(self.top_bar)

        from PyQt5.QtWidgets import QScrollArea, QFrame

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        # Ocultar la barra horizontal para mantener el diseño limpio
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.stack = QStackedWidget()
        self.scroll_area.setWidget(self.stack)
        right.addWidget(self.scroll_area, 1)

        body_layout.addLayout(right)
        root.addWidget(body)

        self.pages = {
            "dashboard": DashboardPage(),
            "production": ProductionPage(),
            "shipments": ShipmentsPage(),
            "traceability": TraceabilityPage(),
            "reception": ReceptionPage(),
            "inventory": InventoryPage(),
            "settings": SettingsPage(),
        }

        for page in self.pages.values():
            self.stack.addWidget(page)

        self._set_page(self._current_page)

    def _set_page(self, page_key: str) -> bool:
        page = self.pages.get(page_key)
        if page is None:
            return False

        self.stack.setCurrentWidget(page)
        self.nav.set_active_page(page_key)

        title = self._page_title(page_key)
        window_title = f"{self._app_title} - {title}"
        self.setWindowTitle(window_title)
        self.title_bar.set_title(window_title)

        self._current_page = page_key
        return True

    @staticmethod
    def _page_title(page_key: str) -> str:
        custom_titles = {
            "traceability": "Trazabilidad",
        }
        return custom_titles.get(page_key, page_key.replace("_", " ").title())

    def _navigate(self, page_key: str) -> None:
        if page_key == "logout":
            from app.ui.login_window import LoginWindow

            self.login_window = LoginWindow()
            show_inherited(self.login_window, source=self)
            self.close()
            return

        if not self._set_page(page_key):
            self.nav.set_active_page(self._current_page)