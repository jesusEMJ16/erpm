"""Reusable themed table and sortable item helpers."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem

SORT_ROLE = Qt.UserRole + 1


class SortableTableItem(QTableWidgetItem):
    def __init__(self, text: str = "", sort_value=None):
        super().__init__(text)
        if sort_value is not None:
            self.setData(SORT_ROLE, sort_value)

    def __lt__(self, other):
        if not isinstance(other, QTableWidgetItem):
            return super().__lt__(other)

        left = self.data(SORT_ROLE)
        right = other.data(SORT_ROLE)

        if left is not None and right is not None:
            try:
                return left < right
            except TypeError:
                return str(left) < str(right)

        return super().__lt__(other)


class ThemedTable(QTableWidget):
    def __init__(self, columns: list[str], parent=None):
        super().__init__(0, len(columns), parent)
        self._columns = columns
        self._configure()

    def _configure(self) -> None:
        self.setHorizontalHeaderLabels(self._columns)
        header = self.horizontalHeader()
        for idx in range(len(self._columns)):
            header.setSectionResizeMode(idx, QHeaderView.Stretch)

        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setFocusPolicy(Qt.NoFocus)
        self.setSortingEnabled(True)

    def set_resize_modes(self, modes: dict[int, QHeaderView.ResizeMode], widths: dict[int, int] | None = None) -> None:
        header = self.horizontalHeader()
        for column, mode in modes.items():
            header.setSectionResizeMode(column, mode)

        if widths:
            for column, width in widths.items():
                self.setColumnWidth(column, width)

    @staticmethod
    def muted_foreground(item: QTableWidgetItem) -> None:
        item.setForeground(QColor(176, 181, 196))
