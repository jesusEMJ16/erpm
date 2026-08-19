"""Global UI theme tokens and QSS styles for BLACKERP."""

from __future__ import annotations

from PyQt5.QtGui import QFont

APP_NAME = "EMINENT ERP"
ORG_NAME = "Noir Command"

# Color tokens inherited from BLACKDB look-and-feel.
SURFACE = "#131313"
SURFACE_LOW = "#1c1b1b"
SURFACE_HIGH = "#2a2a2a"
SURFACE_HIGHEST = "#353534"
SURFACE_LOWEST = "#0e0e0e"
SURFACE_BRIGHT = "#3a3939"

PRIMARY = "#d0d3db"
PRIMARY_CONT = "#8b0000"
ON_PRIMARY_CONT = "#f0eded"

ON_SURFACE = "#e5e2e1"
ON_SURFACE_VAR = "#c8cbd4"
ON_SEC_CONT = "#b0b5c4"

OUTLINE_VAR = "#5a403c"

APP_STYLE = f"""
QWidget {{
    background-color: {SURFACE};
    color: {ON_SURFACE};
    font-family: \"Segoe UI\";
    font-size: 13px;
    border: none;
    outline: none;
}}

QScrollArea, QScrollArea > QWidget > QWidget {{
    background-color: transparent;
}}

QScrollBar:vertical {{
    background: {SURFACE_LOW};
    width: 6px;
    margin: 0;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {OUTLINE_VAR};
    min-height: 30px;
    border-radius: 3px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: {SURFACE_LOW};
    height: 6px;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal {{
    background: {OUTLINE_VAR};
    min-width: 30px;
    border-radius: 3px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

QLabel {{
    background: transparent;
    color: {ON_SURFACE};
}}

QLineEdit {{
    background-color: {SURFACE_LOWEST};
    color: {ON_SURFACE};
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 2px;
    padding: 10px 12px;
    font-size: 13px;
    selection-background-color: {PRIMARY_CONT};
}}
QLineEdit:focus {{
    border-bottom: 2px solid {PRIMARY};
}}
QLineEdit::placeholder {{
    color: {ON_SEC_CONT};
}}

QComboBox {{
    background-color: {SURFACE_LOWEST};
    color: {ON_SURFACE};
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 2px;
    padding: 8px 36px 8px 12px;
    font-size: 13px;
    min-width: 120px;
}}
QComboBox:focus {{
    border-bottom: 2px solid {PRIMARY};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {ON_SEC_CONT};
    margin-right: 6px;
}}
QComboBox QAbstractItemView {{
    background-color: {SURFACE_HIGH};
    color: {ON_SURFACE};
    border: 1px solid {OUTLINE_VAR};
    selection-background-color: {PRIMARY_CONT};
    selection-color: {ON_PRIMARY_CONT};
    outline: none;
    padding: 4px;
}}

QPushButton {{
    background-color: {SURFACE_HIGHEST};
    color: {ON_SURFACE};
    border: 1px solid {OUTLINE_VAR};
    border-radius: 2px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
    letter-spacing: 0.4px;
}}
QPushButton:hover {{
    background-color: {SURFACE_BRIGHT};
    border-color: {PRIMARY};
}}
QPushButton:pressed {{
    background-color: {PRIMARY_CONT};
    color: {ON_PRIMARY_CONT};
}}

QPushButton#btn_primary {{
    background-color: {PRIMARY_CONT};
    color: {ON_PRIMARY_CONT};
    border: 1px solid {PRIMARY};
    font-weight: 600;
    letter-spacing: 1px;
}}
QPushButton#btn_primary:hover {{
    background-color: #9b0000;
}}

QTableWidget {{
    background-color: {SURFACE_LOWEST};
    gridline-color: {OUTLINE_VAR};
    border: 1px solid {OUTLINE_VAR};
    border-radius: 2px;
    selection-background-color: {PRIMARY_CONT};
    selection-color: {ON_PRIMARY_CONT};
    alternate-background-color: {SURFACE};
    font-size: 13px;
}}
QTableWidget::item {{
    padding: 8px 14px;
    border-bottom: 1px solid rgba(90,64,60,0.2);
}}
QTableWidget::item:hover {{
    background-color: {SURFACE_BRIGHT};
}}
QHeaderView::section {{
    background-color: {SURFACE_LOW};
    color: {ON_SEC_CONT};
    padding: 10px 14px;
    border: none;
    border-bottom: 1px solid {OUTLINE_VAR};
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1px;
}}

QFrame#title_bar {{
    background-color: {SURFACE_LOWEST};
    border-bottom: 1px solid rgba(90,64,60,0.25);
}}
QPushButton#title_btn {{
    background-color: transparent;
    color: {ON_SEC_CONT};
    border: none;
    border-radius: 2px;
    padding: 2px 6px;
    font-size: 11px;
}}
QPushButton#title_btn:hover {{
    background-color: {SURFACE_BRIGHT};
    color: {ON_SURFACE};
}}
QPushButton#title_btn_close {{
    background-color: transparent;
    color: {ON_SEC_CONT};
    border: none;
    border-radius: 2px;
    padding: 2px 6px;
    font-size: 11px;
}}
QPushButton#title_btn_close:hover {{
    background-color: {PRIMARY_CONT};
    color: {ON_PRIMARY_CONT};
}}

QFrame#side_nav {{
    background-color: {SURFACE_LOWEST};
    border-right: 1px solid rgba(90,64,60,0.25);
}}

QPushButton[nav="true"] {{
    background-color: transparent;
    border: none;
    border-radius: 0;
    color: {ON_SEC_CONT};
    font-size: 13px;
    font-weight: 500;
    text-align: left;
    padding: 10px 16px;
}}
QPushButton[nav="true"]:hover {{
    background-color: {SURFACE_LOW};
    color: {PRIMARY};
}}
QPushButton[nav="true"][active="true"] {{
    background-color: {SURFACE_LOW};
    color: {PRIMARY};
    border-right: 3px solid {PRIMARY_CONT};
}}

QFrame.card {{
    background-color: {SURFACE_LOW};
    border: 1px solid rgba(90,64,60,0.2);
    border-radius: 2px;
}}

QFrame.card_critical {{
    background-color: {SURFACE_LOW};
    border: 1px solid rgba(139,0,0,0.3);
    border-left: 3px solid {PRIMARY_CONT};
    border-radius: 2px;
}}
"""


def default_app_font() -> QFont:
    return QFont("Segoe UI", 10)
