"""Traceability module with box, pallet, and lot monitoring views."""

from __future__ import annotations

from math import ceil

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.mock_data import traceability_module_data
from app.ui.widgets.themed_table import ThemedTable

_TAB_ITEMS = [
    ("boxes", "Trazabilidad de Cajas"),
    ("pallets", "Trazabilidad de Pallets"),
    ("lots", "Trazabilidad de Lotes"),
]

_TABLE_COLUMNS = ["Codigo de caja", "Producto", "Variedad", "Presentacion", "Peso neto", "Estado"]
_DEFAULT_PAGE_SIZE = 4
_TABLE_VISIBLE_ROWS = 12
_TABLE_ROW_HEIGHT = 38


class TraceabilityPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._tab_payloads: dict[str, dict] = traceability_module_data()
        self._active_tab_key = "boxes" if "boxes" in self._tab_payloads else next(iter(self._tab_payloads), "")
        self._page_by_tab = {key: 1 for key in self._tab_payloads}
        self._tab_buttons: dict[str, QPushButton] = {}
        self._active_payload: dict = {}
        self._current_page_rows: list[dict] = []

        self.setObjectName("traceability_page")
        self._apply_local_styles()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.page_scroll = QScrollArea()
        self.page_scroll.setObjectName("trace_page_scroll")
        self.page_scroll.setWidgetResizable(True)
        self.page_scroll.setFrameShape(QFrame.NoFrame)
        self.page_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        root.addWidget(self.page_scroll)

        content_host = QWidget()
        self.page_scroll.setWidget(content_host)

        content_root = QVBoxLayout(content_host)
        content_root.setContentsMargins(18, 14, 18, 14)
        content_root.setSpacing(10)

        title = QLabel("Trazabilidad")
        title.setObjectName("trace_title")
        content_root.addWidget(title)

        content_root.addWidget(self._build_tab_row())

        content = QHBoxLayout()
        content.setSpacing(12)

        left_col = QVBoxLayout()
        left_col.setSpacing(10)
        left_col.addWidget(self._build_search_card())
        left_col.addWidget(self._build_details_card())
        left_col.addWidget(self._build_relationship_card())
        left_col.addWidget(self._build_table_card(), 1)

        right_col = QVBoxLayout()
        right_col.setSpacing(10)
        right_col.addWidget(self._build_summary_card())
        right_col.addWidget(self._build_timeline_card())
        right_col.addWidget(self._build_documents_card())

        content.addLayout(left_col, 5)
        content.addLayout(right_col, 4)

        content_root.addLayout(content, 1)

        if self._active_tab_key:
            self._switch_tab(self._active_tab_key)

    def _apply_local_styles(self) -> None:
        self.setStyleSheet(
            """
            QWidget#traceability_page {
                background: transparent;
            }
            QScrollArea#trace_page_scroll {
                border: none;
                background: transparent;
            }
            QLabel#trace_title {
                font-size: 36px;
                font-weight: 700;
                letter-spacing: 0.2px;
            }
            QFrame#trace_tabs {
                border-bottom: 1px solid rgba(90,64,60,0.32);
            }
            QPushButton[trace_tab="true"] {
                background-color: transparent;
                border: 1px solid transparent;
                border-bottom: 2px solid transparent;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
                color: #b0b5c4;
                font-size: 12px;
                font-weight: 600;
                padding: 8px 14px;
                text-align: left;
            }
            QPushButton[trace_tab="true"]:hover {
                color: #e5e2e1;
                background-color: rgba(45,45,45,0.35);
            }
            QPushButton[trace_tab="true"][active="true"] {
                color: #f0eded;
                background-color: rgba(139,0,0,0.25);
                border-color: rgba(255,180,168,0.26);
                border-bottom: 2px solid #8b0000;
            }
            QFrame#trace_card {
                background-color: #131517;
                border: 1px solid rgba(90,64,60,0.32);
                border-radius: 3px;
            }
            QLabel#card_title {
                font-size: 18px;
                font-weight: 650;
            }
            QLabel#card_hint {
                color: #b0b5c4;
                font-size: 11px;
            }
            QLabel#doc_name {
                color: #e5e2e1;
                font-size: 12px;
            }
            QLineEdit#trace_search_edit {
                background-color: #0f0f10;
                border: 1px solid rgba(90,64,60,0.42);
                border-bottom: 1px solid rgba(90,64,60,0.42);
                border-radius: 2px;
                min-height: 36px;
                padding: 0 12px;
                font-size: 13px;
            }
            QPushButton#scan_btn {
                min-width: 44px;
                max-width: 44px;
                min-height: 36px;
                padding: 0;
                font-size: 15px;
                font-weight: 700;
                letter-spacing: 0;
                border: 1px solid rgba(90,64,60,0.55);
                background-color: rgba(58,57,57,0.34);
                color: #cfd3dc;
            }
            QPushButton#scan_btn:hover {
                border-color: rgba(208,211,219,0.85);
                color: #f0eded;
            }
            QLabel#search_feedback {
                font-size: 11px;
                color: #b0b5c4;
            }
            QLabel#search_feedback[tone="ok"] {
                color: #5c9a70;
            }
            QLabel#search_feedback[tone="error"] {
                color: #d35b5b;
            }
            QLabel#field_label {
                color: #b0b5c4;
                font-size: 11px;
                font-weight: 600;
            }
            QLabel#field_value {
                color: #e5e2e1;
                font-size: 12px;
            }
            QLabel#field_value_muted {
                color: #c8cbd4;
                font-size: 12px;
            }
            QLabel#code_value {
                color: #d94e4e;
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 0;
            }
            QLabel#status_badge,
            QLabel#status_badge_compact {
                border: 1px solid rgba(90,64,60,0.34);
                border-radius: 3px;
                font-size: 9px;
                font-weight: 700;
                padding: 1px 6px;
                letter-spacing: 0.2px;
            }
            QLabel#status_badge {
                min-height: 17px;
                max-height: 17px;
                padding: 0 6px;
                font-size: 9px;
            }
            QLabel#status_badge_compact {
                padding: 0 5px;
                font-size: 8px;
                max-height: 16px;
            }
            QLabel#status_badge[tone="green"],
            QLabel#status_badge_compact[tone="green"] {
                background-color: rgba(92,154,112,0.23);
                color: #d8ffe4;
                border-color: rgba(92,154,112,0.5);
            }
            QLabel#status_badge[tone="blue"],
            QLabel#status_badge_compact[tone="blue"] {
                background-color: rgba(55,124,182,0.24);
                color: #c7e8ff;
                border-color: rgba(97,170,233,0.45);
            }
            QLabel#status_badge[tone="amber"],
            QLabel#status_badge_compact[tone="amber"] {
                background-color: rgba(133,90,33,0.26);
                color: #ffd6a0;
                border-color: rgba(213,160,72,0.42);
            }
            QLabel#status_badge[tone="red"],
            QLabel#status_badge_compact[tone="red"] {
                background-color: rgba(139,0,0,0.25);
                color: #ffd8d8;
                border-color: rgba(255,140,125,0.42);
            }
            QLabel#status_badge[tone="neutral"],
            QLabel#status_badge_compact[tone="neutral"] {
                background-color: rgba(58,57,57,0.45);
                color: #d0d3db;
                border-color: rgba(90,64,60,0.35);
            }
            QFrame#trace_subcard {
                background-color: #101112;
                border: 1px solid rgba(90,64,60,0.28);
                border-radius: 3px;
            }
            QLabel#subcard_title {
                font-size: 15px;
                font-weight: 650;
            }
            QPushButton#page_nav {
                min-height: 27px;
                min-width: 82px;
                max-width: 82px;
                font-size: 11px;
                font-weight: 600;
                padding: 0;
            }
            QPushButton#table_action_btn {
                min-height: 27px;
                padding: 0 12px;
                font-size: 11px;
                font-weight: 600;
                color: #d0d3db;
                background-color: rgba(58,57,57,0.34);
                border: 1px solid rgba(90,64,60,0.45);
                border-radius: 2px;
            }
            QPushButton#table_action_btn:hover {
                border-color: #d0d3db;
                color: #f0eded;
            }
            QPushButton#page_btn {
                background-color: transparent;
                border: 1px solid rgba(90,64,60,0.35);
                border-radius: 2px;
                min-width: 30px;
                max-width: 30px;
                min-height: 24px;
                max-height: 24px;
                padding: 0;
                font-size: 11px;
                color: #d0d3db;
            }
            QPushButton#page_btn:hover {
                border-color: #d0d3db;
            }
            QPushButton#page_btn[active="true"] {
                background-color: #8b0000;
                border-color: #d0d3db;
                color: #f0eded;
            }
            QLabel#page_ellipsis {
                color: #b0b5c4;
                font-size: 11px;
                min-width: 20px;
                qproperty-alignment: AlignCenter;
            }
            QFrame#timeline_event {
                background-color: #0f1011;
                border: 1px solid rgba(90,64,60,0.3);
                border-radius: 4px;
            }
            QLabel#timeline_title {
                font-size: 14px;
                font-weight: 640;
            }
            QLabel#timeline_time {
                color: #9fa4b2;
                font-size: 11px;
                font-weight: 500;
            }
            QLabel#timeline_meta {
                color: #c8cbd4;
                font-size: 12px;
            }
            QFrame#timeline_line {
                background-color: rgba(90,64,60,0.42);
                min-width: 2px;
                max-width: 2px;
                border-radius: 1px;
            }
            QLabel#timeline_dot {
                border-radius: 11px;
                border: 1px solid rgba(90,64,60,0.4);
                font-size: 10px;
                font-weight: 700;
            }
            QLabel#timeline_dot[tone="green"] {
                background-color: rgba(92,154,112,0.23);
                color: #d8ffe4;
                border-color: rgba(92,154,112,0.5);
            }
            QLabel#timeline_dot[tone="blue"] {
                background-color: rgba(55,124,182,0.24);
                color: #c7e8ff;
                border-color: rgba(97,170,233,0.45);
            }
            QLabel#timeline_dot[tone="amber"] {
                background-color: rgba(133,90,33,0.26);
                color: #ffd6a0;
                border-color: rgba(213,160,72,0.42);
            }
            QLabel#timeline_dot[tone="red"] {
                background-color: rgba(139,0,0,0.25);
                color: #ffd8d8;
                border-color: rgba(255,140,125,0.42);
            }
            QLabel#timeline_dot[tone="neutral"] {
                background-color: rgba(58,57,57,0.45);
                color: #d0d3db;
                border-color: rgba(90,64,60,0.35);
            }
            QFrame#doc_row {
                background-color: #0f1011;
                border: 1px solid rgba(90,64,60,0.3);
                border-radius: 3px;
            }
            QLabel#doc_icon {
                color: #d0d3db;
                font-size: 12px;
                min-width: 20px;
                max-width: 20px;
                qproperty-alignment: AlignCenter;
            }
            QPushButton#doc_btn {
                min-width: 28px;
                max-width: 28px;
                min-height: 22px;
                max-height: 22px;
                padding: 0;
                font-size: 9px;
                font-weight: 700;
                color: #d8ffe4;
                border: 1px solid rgba(92,154,112,0.45);
                background-color: rgba(92,154,112,0.2);
                border-radius: 2px;
            }
            QPushButton#doc_btn:hover {
                border-color: rgba(92,154,112,0.8);
            }
            QPushButton#doc_btn:pressed {
                background-color: rgba(92,154,112,0.3);
            }
            """
        )

    def _build_tab_row(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("trace_tabs")

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        for key, label in _TAB_ITEMS:
            button = QPushButton(label)
            button.setProperty("trace_tab", True)
            button.setProperty("active", key == self._active_tab_key)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda checked=False, tab_key=key: self._switch_tab(tab_key))
            self._tab_buttons[key] = button
            layout.addWidget(button)

        layout.addStretch(1)
        return frame

    def _build_search_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("trace_card")
        card.setMinimumHeight(138)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(9)

        self.search_title_lbl = QLabel("Buscar")
        self.search_title_lbl.setObjectName("card_title")

        self.search_hint_lbl = QLabel("Escanear o ingresar codigo")
        self.search_hint_lbl.setObjectName("card_hint")

        row = QHBoxLayout()
        row.setSpacing(8)

        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("trace_search_edit")
        self.search_edit.setPlaceholderText("Escanear codigo...")
        self.search_edit.returnPressed.connect(self._search_current_code)

        scan_btn = QPushButton("⌗")
        scan_btn.setObjectName("scan_btn")
        scan_btn.setCursor(Qt.PointingHandCursor)
        scan_btn.clicked.connect(self._search_current_code)

        row.addWidget(self.search_edit, 1)
        row.addWidget(scan_btn)

        self.search_feedback_lbl = QLabel("Escanea o escribe un codigo para localizarlo.")
        self.search_feedback_lbl.setObjectName("search_feedback")
        self.search_feedback_lbl.setProperty("tone", "neutral")

        layout.addWidget(self.search_title_lbl)
        layout.addWidget(self.search_hint_lbl)
        layout.addLayout(row)
        layout.addWidget(self.search_feedback_lbl)

        return card

    def _build_details_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("trace_card")
        card.setMinimumHeight(118)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 8)
        layout.setSpacing(5)

        self.details_title_lbl = QLabel("Informacion")
        self.details_title_lbl.setObjectName("card_title")

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(4)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        self._details_widgets: list[tuple[QLabel, QLabel]] = []
        for idx in range(8):
            key_lbl = QLabel("-")
            key_lbl.setObjectName("field_label")

            value_lbl = QLabel("-")
            value_lbl.setObjectName("field_value")

            row = idx if idx < 4 else idx - 4
            col_base = 0 if idx < 4 else 2
            grid.addWidget(key_lbl, row, col_base)
            grid.addWidget(value_lbl, row, col_base + 1)
            self._details_widgets.append((key_lbl, value_lbl))

        layout.addWidget(self.details_title_lbl)
        layout.addLayout(grid)

        return card

    def _build_relationship_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("trace_card")
        card.setMinimumHeight(164)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(9)

        self.relationship_title_lbl = QLabel("Informacion Relacionada")
        self.relationship_title_lbl.setObjectName("card_title")

        blocks = QHBoxLayout()
        blocks.setSpacing(9)

        left_frame, self.left_block_title_lbl, self._left_block_widgets = self._create_info_block()
        right_frame, self.right_block_title_lbl, self._right_block_widgets = self._create_info_block()

        blocks.addWidget(left_frame, 1)
        blocks.addWidget(right_frame, 1)

        layout.addWidget(self.relationship_title_lbl)
        layout.addLayout(blocks)

        return card

    def _create_info_block(self) -> tuple[QFrame, QLabel, list[tuple[QLabel, QLabel]]]:
        frame = QFrame()
        frame.setObjectName("trace_subcard")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(9, 9, 9, 9)
        layout.setSpacing(5)

        title_lbl = QLabel("-")
        title_lbl.setObjectName("subcard_title")
        layout.addWidget(title_lbl, 0, Qt.AlignTop)

        rows: list[tuple[QLabel, QLabel]] = []
        for _ in range(4):
            row_wrap = QWidget(frame)
            row_layout = QHBoxLayout(row_wrap)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)

            key_lbl = QLabel("-")
            key_lbl.setObjectName("field_label")
            key_lbl.setMinimumWidth(100)
            key_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            value_lbl = QLabel("-")
            value_lbl.setObjectName("field_value")
            value_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            value_lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

            row_layout.addWidget(key_lbl)
            row_layout.addWidget(value_lbl, 0, Qt.AlignLeft | Qt.AlignVCenter)
            row_layout.addStretch(1)

            layout.addWidget(row_wrap)
            rows.append((key_lbl, value_lbl))
        return frame, title_lbl, rows

    def _build_table_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("trace_card")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.table_title_lbl = QLabel("Cajas")
        self.table_title_lbl.setObjectName("card_title")

        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        self.open_full_table_btn = QPushButton("Ver tabla completa")
        self.open_full_table_btn.setObjectName("table_action_btn")
        self.open_full_table_btn.setCursor(Qt.PointingHandCursor)
        self.open_full_table_btn.clicked.connect(self._open_full_table_dialog)

        header_row.addWidget(self.table_title_lbl)
        header_row.addStretch(1)
        header_row.addWidget(self.open_full_table_btn)

        self.table = ThemedTable(_TABLE_COLUMNS)
        self.table.setSortingEnabled(False)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.table.set_resize_modes(
            {
                0: QHeaderView.ResizeToContents,
                1: QHeaderView.ResizeToContents,
                2: QHeaderView.Stretch,
                3: QHeaderView.ResizeToContents,
                4: QHeaderView.ResizeToContents,
                5: QHeaderView.Fixed,
            },
            widths={5: 122},
        )
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)

        pager_host = QWidget()
        pager = QHBoxLayout(pager_host)
        pager.setContentsMargins(0, 0, 0, 0)
        pager.setSpacing(6)

        self.prev_btn = QPushButton("Anterior")
        self.prev_btn.setObjectName("page_nav")
        self.prev_btn.setCursor(Qt.PointingHandCursor)
        self.prev_btn.clicked.connect(lambda: self._change_page(-1))

        self.next_btn = QPushButton("Siguiente")
        self.next_btn.setObjectName("page_nav")
        self.next_btn.setCursor(Qt.PointingHandCursor)
        self.next_btn.clicked.connect(lambda: self._change_page(1))

        page_wrap = QWidget()
        self.pagination_layout = QHBoxLayout(page_wrap)
        self.pagination_layout.setContentsMargins(0, 0, 0, 0)
        self.pagination_layout.setSpacing(4)

        pager.addWidget(self.prev_btn)
        pager.addStretch(1)
        pager.addWidget(page_wrap)
        pager.addStretch(1)
        pager.addWidget(self.next_btn)

        pager_host.setVisible(False)

        layout.addLayout(header_row)
        layout.addWidget(self.table)
        layout.addWidget(pager_host)

        return card

    def _build_summary_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("trace_card")
        card.setMinimumHeight(126)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 9)
        layout.setSpacing(6)

        self.summary_title_lbl = QLabel("Informacion")
        self.summary_title_lbl.setObjectName("card_title")

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(4)
        grid.setColumnStretch(1, 1)

        self.summary_code_key_lbl = QLabel("Codigo:")
        self.summary_code_key_lbl.setObjectName("field_label")

        self.summary_code_value_lbl = QLabel("-")
        self.summary_code_value_lbl.setObjectName("code_value")
        self.summary_code_value_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        status_key_lbl = QLabel("Estado actual:")
        status_key_lbl.setObjectName("field_label")

        self.summary_status_value_lbl = QLabel("-")
        self.summary_status_value_lbl.setObjectName("status_badge_compact")
        self.summary_status_value_lbl.setAlignment(Qt.AlignCenter)
        self.summary_status_value_lbl.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)

        created_key_lbl = QLabel("Fecha de creacion:")
        created_key_lbl.setObjectName("field_label")

        self.summary_created_value_lbl = QLabel("-")
        self.summary_created_value_lbl.setObjectName("field_value")

        line_key_lbl = QLabel("Linea:")
        line_key_lbl.setObjectName("field_label")

        self.summary_line_value_lbl = QLabel("-")
        self.summary_line_value_lbl.setObjectName("field_value")

        employee_key_lbl = QLabel("Empleado:")
        employee_key_lbl.setObjectName("field_label")

        self.summary_employee_value_lbl = QLabel("-")
        self.summary_employee_value_lbl.setObjectName("field_value")

        grid.addWidget(self.summary_code_key_lbl, 0, 0)
        grid.addWidget(self.summary_code_value_lbl, 0, 1)
        grid.addWidget(status_key_lbl, 1, 0)
        grid.addWidget(self.summary_status_value_lbl, 1, 1, 1, 1, Qt.AlignLeft | Qt.AlignVCenter)
        grid.addWidget(created_key_lbl, 2, 0)
        grid.addWidget(self.summary_created_value_lbl, 2, 1)
        grid.addWidget(line_key_lbl, 3, 0)
        grid.addWidget(self.summary_line_value_lbl, 3, 1)
        grid.addWidget(employee_key_lbl, 4, 0)
        grid.addWidget(self.summary_employee_value_lbl, 4, 1)

        layout.addWidget(self.summary_title_lbl)
        layout.addLayout(grid)

        return card

    def _build_timeline_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("trace_card")
        card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel("Historial de Trazabilidad")
        title.setObjectName("card_title")

        self.timeline_content = QWidget()
        self.timeline_layout = QVBoxLayout(self.timeline_content)
        self.timeline_layout.setContentsMargins(0, 0, 0, 0)
        self.timeline_layout.setSpacing(10)

        layout.addWidget(title)
        layout.addWidget(self.timeline_content)

        return card

    def _build_documents_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("trace_card")
        card.setMinimumHeight(170)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(9)

        title = QLabel("Documentos Relacionados")
        title.setObjectName("card_title")

        self.documents_host = QWidget()
        self.documents_layout = QVBoxLayout(self.documents_host)
        self.documents_layout.setContentsMargins(0, 0, 0, 0)
        self.documents_layout.setSpacing(6)

        layout.addWidget(title)
        layout.addWidget(self.documents_host)

        return card

    def _switch_tab(self, tab_key: str) -> None:
        payload = self._tab_payloads.get(tab_key)
        if payload is None:
            return

        self._active_tab_key = tab_key
        self._active_payload = payload
        for key, button in self._tab_buttons.items():
            button.setProperty("active", key == tab_key)
            self._repolish(button)

        self.search_title_lbl.setText(str(payload.get("search_title", "Buscar")))
        self.search_hint_lbl.setText(str(payload.get("search_hint", "Escanear o ingresar codigo")))
        self.search_edit.setPlaceholderText(str(payload.get("search_placeholder", "Escanear codigo...")))

        self.summary_title_lbl.setText(str(payload.get("summary_title", "Informacion")))
        self.details_title_lbl.setText(str(payload.get("details_title", "Informacion")))
        self.relationship_title_lbl.setText(str(payload.get("relationship_title", "Informacion Relacionada")))
        self.summary_code_key_lbl.setText(str(payload.get("code_label", "Codigo:")))

        self.summary_created_value_lbl.setText(str(payload.get("focus_created", "-")))
        self.summary_line_value_lbl.setText(str(payload.get("focus_line", "-")))
        self.summary_employee_value_lbl.setText(str(payload.get("focus_employee", "-")))

        self._set_summary_code_status(
            str(payload.get("focus_code", "-")),
            str(payload.get("focus_status", "-")),
        )

        self.table_title_lbl.setText(str(payload.get("table_title", "Registros")))

        details_pairs = payload.get("details_pairs", [])
        if not isinstance(details_pairs, list):
            details_pairs = []
        self._render_details_pairs(details_pairs)

        self.left_block_title_lbl.setText(str(payload.get("left_block_title", "-")))
        self.right_block_title_lbl.setText(str(payload.get("right_block_title", "-")))

        self._render_info_block(self._left_block_widgets, payload.get("left_block_rows", []))
        self._render_info_block(self._right_block_widgets, payload.get("right_block_rows", []))

        self.search_edit.clear()
        self._set_search_feedback("Escanea o escribe un codigo para localizarlo.", "neutral")

        self._render_table()
        self._render_documents(payload.get("documents", []))

    def _render_details_pairs(self, pairs: list[tuple[str, str]]) -> None:
        for idx, (key_lbl, value_lbl) in enumerate(self._details_widgets):
            if idx < len(pairs):
                key, value = pairs[idx]
            else:
                key, value = "-", "-"

            key_lbl.setText(f"{key}:")
            value_lbl.setText(value)

    def _render_info_block(self, widgets: list[tuple[QLabel, QLabel]], rows: list[tuple[str, str]]) -> None:
        safe_rows = rows if isinstance(rows, list) else []

        for idx, (key_lbl, value_lbl) in enumerate(widgets):
            if idx < len(safe_rows):
                key, value = safe_rows[idx]
            else:
                key, value = "-", "-"

            key_lbl.setText(f"{key}:")

            if "estado" in key.lower():
                self._set_badge_label(value_lbl, value, self._status_tone(value), compact=True)
                value_lbl.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
            else:
                value_lbl.setObjectName("field_value")
                value_lbl.setProperty("tone", "")
                value_lbl.setText(value)
                value_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                value_lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
                self._repolish(value_lbl)

    def _render_table(self) -> None:
        payload = self._active_payload or self._tab_payloads.get(self._active_tab_key, {})
        all_rows = payload.get("table_rows", [])
        if not isinstance(all_rows, list):
            all_rows = []

        self._current_page_rows = all_rows

        self.table.blockSignals(True)
        self.table.setRowCount(0)

        for row_data in all_rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setRowHeight(row, _TABLE_ROW_HEIGHT)

            self.table.setItem(row, 0, self._table_item(str(row_data.get("codigo", "-"))))
            self.table.setItem(row, 1, self._table_item(str(row_data.get("producto", "-"))))
            self.table.setItem(row, 2, self._table_item(str(row_data.get("variedad", "-"))))
            self.table.setItem(row, 3, self._table_item(str(row_data.get("presentacion", "-"))))
            self.table.setItem(row, 4, self._table_item(str(row_data.get("peso_neto", "-"))))

            status = str(row_data.get("estado", "-"))
            status_item = QTableWidgetItem(status)
            status_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 5, status_item)
            self.table.setCellWidget(row, 5, self._build_status_badge(status, compact=True))

        visible_rows = min(_TABLE_VISIBLE_ROWS, max(1, self.table.rowCount()))
        table_height = (
            self.table.horizontalHeader().height()
            + (visible_rows * _TABLE_ROW_HEIGHT)
            + (self.table.frameWidth() * 2)
            + 2
        )
        self.table.setFixedHeight(max(table_height, 120))

        self.table.blockSignals(False)

        if all_rows:
            self.table.selectRow(0)
            self._apply_row_context(all_rows[0])
        else:
            self._apply_row_context(None)

    def _refresh_pagination(self, total_pages: int) -> None:
        self._clear_layout(self.pagination_layout)

        current_page = self._page_by_tab.get(self._active_tab_key, 1)
        self.prev_btn.setEnabled(current_page > 1)
        self.next_btn.setEnabled(current_page < total_pages)

        for token in self._page_tokens(current_page, total_pages):
            if token == "...":
                label = QLabel("...")
                label.setObjectName("page_ellipsis")
                self.pagination_layout.addWidget(label)
                continue

            page = int(token)
            button = QPushButton(str(page))
            button.setObjectName("page_btn")
            button.setProperty("active", page == current_page)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda checked=False, value=page: self._set_page(value, total_pages))
            self.pagination_layout.addWidget(button)
            self._repolish(button)

    def _search_current_code(self) -> None:
        query = self.search_edit.text().strip().lower()
        if not query:
            self._set_search_feedback("Ingresa un codigo para buscar en la vista activa.", "error")
            return

        payload = self._active_payload or self._tab_payloads.get(self._active_tab_key, {})
        all_rows = payload.get("table_rows", [])
        if not isinstance(all_rows, list):
            all_rows = []

        found_index = next(
            (idx for idx, row in enumerate(all_rows) if query in str(row.get("codigo", "")).lower()),
            None,
        )

        if found_index is None:
            self._set_search_feedback("No se encontro coincidencia para ese codigo.", "error")
            return

        self._render_table()

        if found_index < self.table.rowCount():
            self.table.selectRow(found_index)
            selected_item = self.table.item(found_index, 0)
            if selected_item is not None:
                self.table.scrollToItem(selected_item, QAbstractItemView.PositionAtCenter)

        selected = all_rows[found_index]
        self._apply_row_context(selected)
        self._set_search_feedback("Codigo localizado en la tabla.", "ok")

    def _open_full_table_dialog(self) -> None:
        payload = self._active_payload or self._tab_payloads.get(self._active_tab_key, {})
        all_rows = payload.get("table_rows", [])
        if not isinstance(all_rows, list):
            all_rows = []

        dialog = QDialog(self)
        dialog.setWindowTitle(str(payload.get("table_title", "Tabla completa")))
        dialog.resize(1080, 680)
        dialog.setStyleSheet(self.styleSheet())

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel(str(payload.get("table_title", "Tabla completa")))
        title.setObjectName("card_title")

        full_table = ThemedTable(_TABLE_COLUMNS)
        full_table.setSortingEnabled(False)
        full_table.set_resize_modes(
            {
                0: QHeaderView.ResizeToContents,
                1: QHeaderView.ResizeToContents,
                2: QHeaderView.Stretch,
                3: QHeaderView.ResizeToContents,
                4: QHeaderView.ResizeToContents,
                5: QHeaderView.Fixed,
            },
            widths={5: 122},
        )

        for row_data in all_rows:
            row = full_table.rowCount()
            full_table.insertRow(row)
            full_table.setRowHeight(row, _TABLE_ROW_HEIGHT)

            full_table.setItem(row, 0, self._table_item(str(row_data.get("codigo", "-"))))
            full_table.setItem(row, 1, self._table_item(str(row_data.get("producto", "-"))))
            full_table.setItem(row, 2, self._table_item(str(row_data.get("variedad", "-"))))
            full_table.setItem(row, 3, self._table_item(str(row_data.get("presentacion", "-"))))
            full_table.setItem(row, 4, self._table_item(str(row_data.get("peso_neto", "-"))))

            status = str(row_data.get("estado", "-"))
            status_item = QTableWidgetItem(status)
            status_item.setTextAlignment(Qt.AlignCenter)
            full_table.setItem(row, 5, status_item)
            full_table.setCellWidget(row, 5, self._build_status_badge(status, compact=True))

        close_btn = QPushButton("Cerrar")
        close_btn.setObjectName("table_action_btn")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(dialog.accept)

        actions = QHBoxLayout()
        actions.addStretch(1)
        actions.addWidget(close_btn)

        layout.addWidget(title)
        layout.addWidget(full_table, 1)
        layout.addLayout(actions)

        dialog.exec_()

    def _on_table_selection_changed(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return

        selected = self._row_payload_for_index(row)
        if selected is None:
            return
        self._apply_row_context(selected)

    def _row_payload_for_index(self, row_index: int) -> dict | None:
        if row_index < 0 or row_index >= len(self._current_page_rows):
            return None
        return self._current_page_rows[row_index]

    def _apply_row_context(self, row_payload: dict | None) -> None:
        payload = self._active_payload or self._tab_payloads.get(self._active_tab_key, {})

        if row_payload is None:
            code = str(payload.get("focus_code", "-"))
            status = str(payload.get("focus_status", "-"))
            details_rows = payload.get("details_pairs", [])
            left_rows = payload.get("left_block_rows", [])
            timeline = payload.get("timeline", [])
        else:
            code = str(row_payload.get("codigo", payload.get("focus_code", "-")))
            status = str(row_payload.get("estado", payload.get("focus_status", "-")))
            details_rows = self._inject_row_details(payload.get("details_pairs", []), row_payload)
            left_rows = self._inject_row_left_block(payload.get("left_block_rows", []), row_payload)
            timeline = self._inject_row_timeline(payload.get("timeline", []), row_payload)

        self._set_summary_code_status(code, status)
        self._render_details_pairs(details_rows if isinstance(details_rows, list) else [])
        self._render_info_block(self._left_block_widgets, left_rows if isinstance(left_rows, list) else [])
        self._render_timeline(timeline if isinstance(timeline, list) else [])

    @staticmethod
    def _inject_row_details(base_pairs: list[tuple[str, str]], row_payload: dict) -> list[tuple[str, str]]:
        rows: list[tuple[str, str]] = []
        for item in base_pairs if isinstance(base_pairs, list) else []:
            if not isinstance(item, tuple) or len(item) != 2:
                continue
            key, value = item
            normalized = str(key).lower()
            if "producto" in normalized:
                value = str(row_payload.get("producto", value))
            elif "variedad" in normalized:
                value = str(row_payload.get("variedad", value))
            elif "presentacion" in normalized:
                value = str(row_payload.get("presentacion", value))
            elif "peso" in normalized:
                value = str(row_payload.get("peso_neto", value))
            rows.append((str(key), str(value)))
        return rows

    @staticmethod
    def _inject_row_left_block(base_rows: list[tuple[str, str]], row_payload: dict) -> list[tuple[str, str]]:
        rows: list[tuple[str, str]] = []
        for item in base_rows if isinstance(base_rows, list) else []:
            if not isinstance(item, tuple) or len(item) != 2:
                continue
            key, value = item
            normalized = str(key).lower()
            if "estado" in normalized:
                value = str(row_payload.get("estado", value))
            rows.append((str(key), str(value)))
        return rows

    @staticmethod
    def _inject_row_timeline(base_timeline: list[dict], row_payload: dict) -> list[dict]:
        items: list[dict] = []
        for index, event in enumerate(base_timeline if isinstance(base_timeline, list) else []):
            if not isinstance(event, dict):
                continue
            item = dict(event)
            if index == 0:
                item["line1"] = f"Codigo: {row_payload.get('codigo', '-')}"
            items.append(item)
        return items

    def _set_summary_code_status(self, code: str, status: str) -> None:
        self.summary_code_value_lbl.setText(code)
        self._set_badge_label(self.summary_status_value_lbl, status, self._status_tone(status), compact=True)

    def _set_badge_label(self, label: QLabel, text: str, tone: str, compact: bool) -> None:
        label.setObjectName("status_badge_compact" if compact else "status_badge")
        label.setAlignment(Qt.AlignCenter)
        label.setProperty("tone", tone)
        label.setText(text)
        if compact:
            label.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        else:
            label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._repolish(label)

    def _render_timeline(self, events: list[dict]) -> None:
        self._clear_layout(self.timeline_layout)

        safe_events = events if isinstance(events, list) else []
        if not safe_events:
            empty = QLabel("No hay eventos disponibles para esta vista.")
            empty.setObjectName("field_value_muted")
            self.timeline_layout.addWidget(empty)
            return

        total = len(safe_events)
        for index, event in enumerate(safe_events):
            self.timeline_layout.addWidget(self._build_timeline_event(event, index, total))

    def _build_timeline_event(self, event: dict, index: int, total: int) -> QWidget:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(3, 0, 10, 0)
        row_layout.setSpacing(12)

        marker = QWidget()
        marker.setFixedWidth(36)

        marker_layout = QVBoxLayout(marker)
        marker_layout.setContentsMargins(7, 0, 7, 0)
        marker_layout.setSpacing(0)

        top_line = QFrame(marker)
        top_line.setObjectName("timeline_line")
        top_line.setVisible(index > 0)
        top_line.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        dot = QLabel(self._timeline_marker_icon(str(event.get("icon", ""))), marker)
        dot.setObjectName("timeline_dot")
        dot.setProperty("tone", str(event.get("tone", "neutral")))
        dot.setAlignment(Qt.AlignCenter)
        dot.setFixedSize(22, 22)

        bottom_line = QFrame(marker)
        bottom_line.setObjectName("timeline_line")
        bottom_line.setVisible(index < (total - 1))
        bottom_line.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        marker_layout.addWidget(top_line, 1)
        marker_layout.addWidget(dot, 0, Qt.AlignHCenter)
        marker_layout.addWidget(bottom_line, 1)

        card = QFrame()
        card.setObjectName("timeline_event")
        card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(4)

        title_row = QHBoxLayout()
        title_row.setSpacing(10)

        title_lbl = QLabel(str(event.get("title", "Evento")))
        title_lbl.setObjectName("timeline_title")
        title_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        time_lbl = QLabel(str(event.get("time", "-")))
        time_lbl.setObjectName("timeline_time")
        time_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        time_lbl.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)

        title_row.addWidget(title_lbl, 1)
        title_row.addWidget(time_lbl)

        line1_lbl = QLabel(str(event.get("line1", "")))
        line1_lbl.setObjectName("timeline_meta")
        line1_lbl.setWordWrap(True)

        line2_lbl = QLabel(str(event.get("line2", "")))
        line2_lbl.setObjectName("timeline_meta")
        line2_lbl.setWordWrap(True)

        card_layout.addLayout(title_row)
        card_layout.addWidget(line1_lbl)
        card_layout.addWidget(line2_lbl)

        row_layout.addWidget(marker)
        row_layout.addWidget(card, 1)

        return row

    @staticmethod
    def _timeline_marker_icon(marker_code: str) -> str:
        return "↓"

    def _render_documents(self, docs: list[dict]) -> None:
        self._clear_layout(self.documents_layout)

        safe_docs = docs if isinstance(docs, list) else []
        if not safe_docs:
            empty = QLabel("No hay documentos relacionados.")
            empty.setObjectName("field_value_muted")
            self.documents_layout.addWidget(empty)
            return

        for payload in safe_docs:
            row = QFrame()
            row.setObjectName("doc_row")

            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(10, 6, 8, 6)
            row_layout.setSpacing(8)

            icon_lbl = QLabel("◧")
            icon_lbl.setObjectName("doc_icon")

            name = str(payload.get("name", "Documento"))
            name_lbl = QLabel(name)
            name_lbl.setObjectName("doc_name")

            download_btn = QPushButton("DL")
            download_btn.setObjectName("doc_btn")
            download_btn.setCursor(Qt.PointingHandCursor)
            download_btn.setText("")
            download_btn.setIcon(self.style().standardIcon(QStyle.SP_ArrowDown))
            download_btn.setIconSize(QSize(10, 10))
            download_btn.clicked.connect(
                lambda checked=False, doc_name=name: self._set_search_feedback(
                    f"Documento listo para descarga: {doc_name}",
                    "ok",
                )
            )

            row_layout.addWidget(icon_lbl)
            row_layout.addWidget(name_lbl, 1)
            row_layout.addWidget(download_btn)

            self.documents_layout.addWidget(row)

        self.documents_layout.addStretch(1)

    def _change_page(self, delta: int) -> None:
        current = self._page_by_tab.get(self._active_tab_key, 1)
        self._set_page(current + delta)

    def _set_page(self, target_page: int, total_pages: int | None = None) -> None:
        if total_pages is None:
            payload = self._tab_payloads.get(self._active_tab_key, {})
            rows = payload.get("table_rows", [])
            if not isinstance(rows, list):
                rows = []
            total_pages = max(1, int(ceil(len(rows) / _DEFAULT_PAGE_SIZE)))

        clamped = min(max(int(target_page), 1), int(total_pages))
        self._page_by_tab[self._active_tab_key] = clamped
        self._render_table()

    @staticmethod
    def _page_tokens(current: int, total: int) -> list[int | str]:
        if total <= 6:
            return list(range(1, total + 1))

        if current <= 3:
            return [1, 2, 3, 4, "...", total]

        if current >= total - 2:
            return [1, "...", total - 3, total - 2, total - 1, total]

        return [1, "...", current - 1, current, current + 1, "...", total]

    @staticmethod
    def _status_tone(status: str) -> str:
        normalized = status.upper()

        if any(token in normalized for token in ("ALERTA", "DESV", "RECHAZ", "ERROR")):
            return "red"
        if any(token in normalized for token in ("PEND", "REVISION", "ESPERA", "HOLD")):
            return "amber"
        if any(token in normalized for token in ("TRANSITO", "RUTA", "MOV", "TRACK")):
            return "blue"
        if any(token in normalized for token in ("EMBARC", "CERRAD", "COMPLET", "VALID", "OK")):
            return "green"

        return "neutral"

    def _build_status_badge(self, status: str, compact: bool) -> QWidget:
        label = QLabel(status)
        self._set_badge_label(label, status, self._status_tone(status), compact=compact)

        wrap = QWidget()
        layout = QHBoxLayout(wrap)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.setSpacing(0)
        layout.addWidget(label)
        layout.setAlignment(Qt.AlignCenter)
        return wrap

    def _set_search_feedback(self, message: str, tone: str) -> None:
        self.search_feedback_lbl.setText(message)
        self.search_feedback_lbl.setProperty("tone", tone)
        self._repolish(self.search_feedback_lbl)

    def _clear_layout(self, layout: QVBoxLayout | QHBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            child_widget = item.widget()
            child_layout = item.layout()

            if child_widget is not None:
                child_widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)

    @staticmethod
    def _repolish(widget: QWidget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()

    @staticmethod
    def _table_item(text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        return item
