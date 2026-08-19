"""KPI card widget matching the BLACKDB visual style."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout

from app.core.theme import ON_SEC_CONT, ON_SURFACE, PRIMARY_CONT, SURFACE_LOW


class KPICard(QFrame):
    def __init__(self, label: str, value: str, sub_text: str, critical: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName("kpi_card")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(118)
        self._critical = critical

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(8)

        top = QHBoxLayout()
        self.label_lbl = QLabel(label.upper())
        self.label_lbl.setStyleSheet(
            f"color: {ON_SEC_CONT}; font-size: 10px; font-weight: 600; letter-spacing: 1.4px;"
        )
        critical_mark = QLabel("!" if critical else "")
        critical_mark.setStyleSheet(
            f"color: {ON_SURFACE}; font-size: 12px; font-weight: 700;"
        )
        top.addWidget(self.label_lbl)
        top.addStretch()
        top.addWidget(critical_mark)

        self.value_lbl = QLabel(value)
        self.value_lbl.setStyleSheet(
            "font-size: 30px; font-weight: 300; letter-spacing: -1px;"
        )

        self.sub_lbl = QLabel(sub_text)
        self.sub_lbl.setStyleSheet(f"color: {ON_SEC_CONT}; font-size: 11px;")

        root.addLayout(top)
        root.addWidget(self.value_lbl)
        root.addWidget(self.sub_lbl)
        self._apply_style()

    def _apply_style(self) -> None:
        if self._critical:
            self.setStyleSheet(
                f"""
                QFrame#kpi_card {{
                    background-color: {SURFACE_LOW};
                    border: 1px solid rgba(139,0,0,0.3);
                    border-left: 3px solid {PRIMARY_CONT};
                    border-radius: 2px;
                }}
                """
            )
            self.value_lbl.setStyleSheet(
                f"color: {ON_SURFACE}; font-size: 30px; font-weight: 300; letter-spacing: -1px;"
            )
        else:
            self.setStyleSheet(
                f"""
                QFrame#kpi_card {{
                    background-color: {SURFACE_LOW};
                    border: 1px solid rgba(90,64,60,0.2);
                    border-radius: 2px;
                }}
                QFrame#kpi_card:hover {{
                    border-color: rgba(176,181,196,0.35);
                }}
                """
            )
            self.value_lbl.setStyleSheet(
                f"color: {ON_SURFACE}; font-size: 30px; font-weight: 300; letter-spacing: -1px;"
            )

    def update_data(self, value: str, sub_text: str, critical: bool | None = None) -> None:
        if critical is not None and critical != self._critical:
            self._critical = critical
            self._apply_style()
        self.value_lbl.setText(value)
        self.sub_lbl.setText(sub_text)
