"""Inventory page with themed table and client-side filtering."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.mock_data import inventory_rows
from app.ui.widgets.themed_table import SortableTableItem, ThemedTable

_STATUS_ORDER = {"Out of Stock": 0, "Low Stock": 1, "In Stock": 2}


class InventoryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._rows: list[dict] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel("Inventory")
        title.setStyleSheet("font-size: 20px; font-weight: 600; letter-spacing: 0.5px;")

        subtitle = QLabel("Clean baseline of the BLACKDB table behavior and styling.")
        subtitle.setStyleSheet("color: #b0b5c4; font-size: 11px;")

        root.addWidget(title)
        root.addWidget(subtitle)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by id, product or description")
        self.search_edit.textChanged.connect(self._apply_filter)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["All Status", "In Stock", "Low Stock", "Out of Stock"])
        self.status_combo.currentTextChanged.connect(self._apply_filter)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._load_rows)

        filter_row.addWidget(self.search_edit, 1)
        filter_row.addWidget(self.status_combo)
        filter_row.addWidget(refresh_btn)

        root.addLayout(filter_row)

        table_frame = QFrame()
        table_frame.setProperty("class", "card")
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(10, 10, 10, 10)

        self.table = ThemedTable(["ID", "Product Name", "Description", "Price", "Stock", "Status"])
        self.table.set_resize_modes(
            {
                0: QHeaderView.ResizeToContents,
                1: QHeaderView.Stretch,
                2: QHeaderView.Stretch,
                3: QHeaderView.ResizeToContents,
                4: QHeaderView.ResizeToContents,
                5: QHeaderView.Fixed,
            },
            widths={5: 140},
        )
        table_layout.addWidget(self.table)
        root.addWidget(table_frame, 1)

        self._load_rows()

    def _load_rows(self) -> None:
        self._rows = inventory_rows()
        self._render_rows(self._rows)

    def _render_rows(self, rows: list[dict]) -> None:
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)

        for payload in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setRowHeight(row, 48)

            id_item = SortableTableItem(str(payload["id"]), int(payload["id"]))
            name_item = QTableWidgetItem(payload["name"])
            desc_item = QTableWidgetItem(payload["description"])
            price_value = float(payload["price"])
            price_item = SortableTableItem(f"${price_value:.2f}", price_value)
            price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            stock_value = int(payload["stock"])
            stock_item = SortableTableItem(str(stock_value), stock_value)
            stock_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            status = payload["status"]
            status_item = SortableTableItem("", _STATUS_ORDER.get(status, 99))
            status_item.setData(Qt.UserRole, status)

            self.table.setItem(row, 0, id_item)
            self.table.setItem(row, 1, name_item)
            self.table.setItem(row, 2, desc_item)
            self.table.setItem(row, 3, price_item)
            self.table.setItem(row, 4, stock_item)
            self.table.setItem(row, 5, status_item)
            self.table.setCellWidget(row, 5, self._build_status_badge(status))

        self.table.setSortingEnabled(True)

    def _build_status_badge(self, status: str) -> QWidget:
        label = QLabel(status)
        label.setAlignment(Qt.AlignCenter)
        label.setFixedHeight(24)

        styles = {
            "In Stock": "background-color: #353534; color: #e5e2e1; border: 1px solid rgba(90,64,60,0.3);",
            "Low Stock": "background-color: rgba(139,0,0,0.2); color: #d0d3db; border: 1px solid rgba(255,180,168,0.3);",
            "Out of Stock": "background-color: #353534; color: #b0b5c4; border: 1px solid rgba(90,64,60,0.3);",
        }
        label.setStyleSheet(
            f"QLabel {{ {styles.get(status, styles['In Stock'])} border-radius: 2px; padding: 0 8px; font-size: 11px; }}"
        )

        wrap = QWidget()
        wrap.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(wrap)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.addWidget(label)
        layout.setAlignment(Qt.AlignCenter)
        return wrap

    def _apply_filter(self) -> None:
        text = self.search_edit.text().strip().lower()
        status_filter = self.status_combo.currentText()

        filtered: list[dict] = []
        for row in self._rows:
            matches_text = (
                not text
                or text in str(row["id"]).lower()
                or text in row["name"].lower()
                or text in row["description"].lower()
            )
            matches_status = status_filter == "All Status" or row["status"] == status_filter
            if matches_text and matches_status:
                filtered.append(row)

        self._render_rows(filtered)
