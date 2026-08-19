"""Production line page for scan-based box registration and live monitoring."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
import re

from PyQt5.QtCore import QDate, QRectF, QSize, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog, QPrinterInfo
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTabWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.chart_palette import get_chart_palette, resolve_chart_preset
from app.core.theme import (
    ON_PRIMARY_CONT,
    ON_SEC_CONT,
    ON_SURFACE,
    OUTLINE_VAR,
    PRIMARY,
    PRIMARY_CONT,
    SURFACE_HIGH,
    SURFACE_HIGHEST,
    SURFACE_LOW,
    SURFACE_LOWEST,
)
from app.services.erp_sql import (
    close_pallet as close_pallet_sql,
    deactivate_pallet,
    fetch_all_pallets,
    fetch_completed_pallets,
    fetch_current_pallet_rows,
    fetch_packing_label_by_id,
    fetch_pallet_label_data,
    persist_production_scan,
    reactivate_pallet,
    update_pallet_info,
)
from app.services.mock_data import production_employees, production_rows
from app.ui.widgets.themed_table import SortableTableItem, ThemedTable
from modules.pallets import assign_box_to_pallet

_PRESENTATION_ORDER = ("Jumbo", "Medium", "Small")
_TOKEN_BOX_KEYS = ("BOX", "BOXID", "BOX_ID", "CAJA", "CAJA_ID", "UNIQUE_BOX", "ID_CAJA")
_DEFAULT_LABEL_CLIENTS = (
    "Cliente Norte",
    "Cliente Export",
    "Retail Central",
    "Cliente no asignado",
)
_LABEL_VARIETY_OPTIONS = ("Sweet Globe", "Autumn Crisp", "Allison", "Scarlotta")
_LABEL_DESTINATION_OPTIONS = ("USA", "Canada", "UK", "UE")
_LABEL_SIZE_OPTIONS = (
    "4 x 2 pulgadas (102 x 51 mm)",
    "4 x 3 pulgadas (102 x 76 mm)",
    "4 x 4 pulgadas (102 x 102 mm)",
)
_PALLET_CAPACITY_DEFAULT = 90


def _presentation_colors_for_preset(preset_name: str | None = None) -> dict[str, QColor]:
    palette = get_chart_palette(preset_name)
    presentation_palette = dict(palette.get("presentations", {}))
    fallback = QColor(188, 194, 208)

    return {
        presentation: QColor(presentation_palette.get(presentation, fallback.name()))
        for presentation in _PRESENTATION_ORDER
    }


class DonutChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._segments: list[tuple[str, int, QColor]] = []
        self.setMinimumSize(132, 132)

    def set_segments(self, segments: list[tuple[str, int, QColor]]) -> None:
        self._segments = [(label, max(0, int(value)), color) for label, value, color in segments]
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(12, 12, -12, -12)
        side = min(rect.width(), rect.height())
        x = rect.x() + (rect.width() - side) / 2
        y = rect.y() + (rect.height() - side) / 2
        chart_rect = QRectF(x, y, side, side)

        track_pen = QPen(QColor(SURFACE_HIGH), 12)
        track_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(track_pen)
        painter.drawArc(chart_rect, 0, 360 * 16)

        total = sum(value for _, value, _ in self._segments)
        if total > 0:
            start = 90 * 16
            for _, value, color in self._segments:
                if value <= 0:
                    continue
                span = int((value / total) * 360 * 16)
                seg_pen = QPen(color, 12)
                seg_pen.setCapStyle(Qt.RoundCap)
                painter.setPen(seg_pen)
                painter.drawArc(chart_rect, start, -span)
                start -= span

        painter.setPen(QColor(ON_SURFACE))
        font = painter.font()
        font.setPointSize(12)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(chart_rect, Qt.AlignCenter, str(total))


class ProductionPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._chart_preset_name = resolve_chart_preset()
        self._presentation_colors = _presentation_colors_for_preset(self._chart_preset_name)

        self._rows: list[dict] = []
        self._label_rows: list[dict] = []
        self._employees = production_employees()
        self._employee_index = {
            self._normalize_employee_code(item.get("code", "")): item for item in self._employees
        }
        self._pending_employee_label: dict | None = None
        self._pending_description_label: dict | None = None
        self._label_selected_box: dict | None = None
        self._label_counter = 1
        self._label_quantity = 1
        self._label_orientation = "Horizontal"
        self._label_preview_zoom = 100

        self._pallet_capacity = _PALLET_CAPACITY_DEFAULT
        self._current_pallet_id = "PLT-21708"
        self._next_pallet_id = 21709
        self._pallet_presentation = "Jumbo"
        self._pallet_boxes: list[dict] = []
        self._completed_pallets: list[dict] = []
        self._pallet_activity_rows: list[str] = []
        self._pallet_error_slots: set[int] = set()

        # Pallet Manager state
        self._pallet_mgr_rows: list[dict] = []
        self._pallet_mgr_editing_code: str | None = None
        self._pallet_mgr_selected: dict | None = None
        self._pallet_label_copies = 1
        self._pallet_label_size = "4 x 6 pulgadas (102 x 152 mm)"
        self._pallet_label_orientation = "Horizontal"
        self._pallet_label_selected_data: dict | None = None

        self.setObjectName("production_page")
        self._apply_local_styles()

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(8)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("production_tabs")
        root.addWidget(self.tabs, 1)

        self.scan_tab = QWidget()
        self.labels_tab = QWidget()
        self.pallets_tab = QWidget()
        self.employees_tab = QWidget()

        self._build_scan_tab(self.scan_tab)
        self._build_labels_tab(self.labels_tab)
        self._build_pallets_tab(self.pallets_tab)
        self._build_employees_tab(self.employees_tab)

        self.tabs.addTab(self.scan_tab, "Escaneo")
        self.tabs.addTab(self.labels_tab, "Etiquetas")
        self.tabs.addTab(self.pallets_tab, "Pallets")
        self.tabs.addTab(self.employees_tab, "Empleados")

        # keep table height synced with right column performance card when tabs change
        try:
            self.tabs.currentChanged.connect(self._sync_table_height_with_perf)
        except Exception:
            pass

        self._load_rows()
        self._load_label_rows()
        self._load_pallet_data()
        self._refresh_ui()
        self._refresh_labeling_ui()

    def apply_chart_preset(self, preset_name: str | None = None) -> str:
        self._chart_preset_name = resolve_chart_preset(preset_name)
        self._presentation_colors = _presentation_colors_for_preset(self._chart_preset_name)
        self._refresh_presentation_legend_colors()

        if hasattr(self, "table"):
            self._render_table()
        if hasattr(self, "pallet_completed_table"):
            self._render_completed_pallets()
        if hasattr(self, "presentation_chart"):
            self._refresh_presentations()

        return self._chart_preset_name

    def _refresh_presentation_legend_colors(self) -> None:
        dot_labels = getattr(self, "legend_dot_labels", None)
        if not isinstance(dot_labels, dict):
            return

        for presentation in _PRESENTATION_ORDER:
            dot = dot_labels.get(presentation)
            if dot is None:
                continue
            color = self._presentation_colors.get(presentation, QColor(188, 194, 208)).name()
            dot.setStyleSheet(f"color: {color}; font-size: 12px;")

    def _build_scan_tab(self, tab: QWidget) -> None:
        root = QHBoxLayout(tab)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        main_col = QVBoxLayout()
        main_col.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)
        top_row.addWidget(self._build_scan_card(), 5)
        top_row.addWidget(self._build_state_card(), 5)

        main_col.addLayout(top_row)

        # Add title row for table
        title_row = QHBoxLayout()
        title_row.setSpacing(0)
        title_row.setContentsMargins(14, 6, 14, 0)
        title = QLabel("Registro de cajas en tiempo real")
        title.setObjectName("section_title")
        title_row.addWidget(title)
        main_col.addLayout(title_row, 0)

        main_col.addWidget(self._build_table_card(), 1)

        side_panel = QWidget()
        side_panel.setMinimumWidth(0)

        side_col = QVBoxLayout(side_panel)
        side_col.setSpacing(10)
        side_col.setContentsMargins(0, 0, 0, 0)
        side_col.addWidget(self._build_summary_card())
        side_col.addWidget(self._build_presentations_card())
        side_col.addWidget(self._build_employee_performance_card())
        side_col.addWidget(self._build_activity_card())
        side_col.addStretch(1)

        self.side_scroll = QScrollArea()
        self.side_scroll.setObjectName("production_side_scroll")
        self.side_scroll.setWidgetResizable(True)
        self.side_scroll.setFrameShape(QFrame.NoFrame)
        self.side_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.side_scroll.setWidget(side_panel)
        self.side_scroll.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.side_scroll.setMinimumWidth(0)

        root.addLayout(main_col, 4)
        root.addWidget(self.side_scroll, 2)

    def _build_labels_tab(self, tab: QWidget) -> None:
        root = QVBoxLayout(tab)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)
        top_row.addWidget(self._build_label_assignment_card(), 4)
        top_row.addWidget(self._build_label_preview_card(), 6)

        root.addLayout(top_row, 3)
        root.addWidget(self._build_label_history_card(), 2)

        self._bind_label_form_events()
        self._set_label_orientation("Horizontal")

    def _build_pallets_tab(self, tab: QWidget) -> None:
        root = QVBoxLayout(tab)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.pallet_inner_tabs = QTabWidget()
        self.pallet_inner_tabs.setObjectName("pallet_inner_tabs")

        self.pallet_registro_subtab = QWidget()
        self.pallet_registro_subtab = QWidget()
        self._build_pallet_registro_subtab(self.pallet_registro_subtab)

        self.pallet_gestor_subtab = QWidget()
        self._build_pallet_gestor_subtab(self.pallet_gestor_subtab)

        self.pallet_inner_tabs.addTab(self.pallet_registro_subtab, "Registro de Pallets")
        self.pallet_inner_tabs.addTab(self.pallet_gestor_subtab, "Gestor de Pallets")

        self.pallet_inner_tabs.currentChanged.connect(self._on_pallet_inner_tab_changed)

        root.addWidget(self.pallet_inner_tabs, 1)

    def _build_pallet_registro_subtab(self, tab: QWidget) -> None:
        root = QVBoxLayout(tab)
        root.setContentsMargins(0, 8, 0, 0)
        root.setSpacing(0)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)
        top_row.addWidget(self._build_pallet_current_card(), 4)
        top_row.addWidget(self._build_pallet_boxes_card(), 4)
        top_row.addWidget(self._build_completed_pallets_card(), 5)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)
        bottom_row.addWidget(self._build_pallet_map_card(), 7)

        right_col = QVBoxLayout()
        right_col.setSpacing(10)
        right_col.addWidget(self._build_pallet_summary_card())
        right_col.addWidget(self._build_pallet_activity_panel())
        right_col.addStretch(1)

        right_wrap = QWidget()
        right_wrap.setLayout(right_col)
        bottom_row.addWidget(right_wrap, 3)

        root.addLayout(top_row, 0)
        root.addLayout(bottom_row, 0)
        root.addStretch(1)

    def _build_pallet_gestor_subtab(self, tab: QWidget) -> None:
        root = QVBoxLayout(tab)
        root.setContentsMargins(0, 8, 0, 0)
        root.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)
        top_row.addWidget(self._build_pallet_mgr_catalog_card(), 7)
        top_row.addWidget(self._build_pallet_mgr_editor_card(), 3)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)
        bottom_row.addWidget(self._build_pallet_mgr_print_card(), 10)

        root.addLayout(top_row, 6)
        root.addLayout(bottom_row, 4)

    def _build_pallet_mgr_catalog_card(self) -> QFrame:
        card = self._card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 6, 14, 14)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Catalogo de Pallets (Gestor)")
        title.setObjectName("section_title")
        
        self.pallet_mgr_show_inactive_cb = QCheckBox("Mostrar inactivos")
        self.pallet_mgr_show_inactive_cb.setStyleSheet("color: #eaddd7; font-size: 12px;")
        self.pallet_mgr_show_inactive_cb.stateChanged.connect(self._refresh_pallet_mgr_catalog)

        refresh_btn = QPushButton("Actualizar")
        refresh_btn.setObjectName("btn_secondary")
        refresh_btn.clicked.connect(self._refresh_pallet_mgr_catalog)

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.pallet_mgr_show_inactive_cb)
        header.addWidget(refresh_btn)

        self.pallet_mgr_table = ThemedTable(
            [
                "ID",
                "Codigo",
                "Estado",
                "Presentacion",
                "Cajas",
                "Kilos",
                "Armado",
                "Mix",
                "Activo",
                "Acciones",
            ]
        )
        self.pallet_mgr_table.set_resize_modes(
            {
                0: QHeaderView.Fixed,
                1: QHeaderView.ResizeToContents,
                2: QHeaderView.Fixed,
                3: QHeaderView.Stretch,
                4: QHeaderView.Fixed,
                5: QHeaderView.Fixed,
                6: QHeaderView.ResizeToContents,
                7: QHeaderView.Fixed,
                8: QHeaderView.Fixed,
                9: QHeaderView.Fixed,
            },
            widths={0: 60, 2: 70, 4: 50, 5: 60, 7: 50, 8: 60, 9: 180},
        )

        layout.addLayout(header)
        layout.addWidget(self.pallet_mgr_table)
        return card

    def _build_pallet_mgr_editor_card(self) -> QFrame:
        card = self._card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("Edicion de Pallet")
        title.setObjectName("section_title")
        
        self.pallet_mgr_edit_code_lbl = QLabel("Seleccione un pallet...")
        self.pallet_mgr_edit_code_lbl.setObjectName("summary_value")
        self.pallet_mgr_edit_code_lbl.setStyleSheet("color: #a8d4ff; font-size: 16px;")

        form = QGridLayout()
        form.setSpacing(8)

        # Presentation Override
        pres_lbl = QLabel("Presentacion:")
        pres_lbl.setObjectName("field_label")
        self.pallet_mgr_pres_combo = QComboBox()
        self.pallet_mgr_pres_combo.addItems(["(Automatica)"] + list(_PRESENTATION_ORDER))
        
        # Variety
        var_lbl = QLabel("Variedad:")
        var_lbl.setObjectName("field_label")
        self.pallet_mgr_var_input = QLineEdit()
        
        # Lot
        lot_lbl = QLabel("Lote:")
        lot_lbl.setObjectName("field_label")
        self.pallet_mgr_lot_input = QLineEdit()
        
        # Notes
        notes_lbl = QLabel("Notas:")
        notes_lbl.setObjectName("field_label")
        self.pallet_mgr_notes_input = QLineEdit()

        form.addWidget(pres_lbl, 0, 0)
        form.addWidget(self.pallet_mgr_pres_combo, 0, 1)
        form.addWidget(var_lbl, 1, 0)
        form.addWidget(self.pallet_mgr_var_input, 1, 1)
        form.addWidget(lot_lbl, 2, 0)
        form.addWidget(self.pallet_mgr_lot_input, 2, 1)
        form.addWidget(notes_lbl, 3, 0)
        form.addWidget(self.pallet_mgr_notes_input, 3, 1)

        self.pallet_mgr_save_btn = QPushButton("Guardar Cambios")
        self.pallet_mgr_save_btn.setObjectName("btn_primary")
        self.pallet_mgr_save_btn.setEnabled(False)
        self.pallet_mgr_save_btn.clicked.connect(self._handle_pallet_mgr_save)

        layout.addWidget(title)
        layout.addWidget(self.pallet_mgr_edit_code_lbl)
        layout.addLayout(form)
        layout.addStretch()
        layout.addWidget(self.pallet_mgr_save_btn)
        return card

    def _build_pallet_mgr_print_card(self) -> QFrame:
        card = self._card_frame()
        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(20)

        left_col = QVBoxLayout()
        title = QLabel("Impresion de Etiqueta (Label)")
        title.setObjectName("section_title")
        
        self.pallet_mgr_print_target_lbl = QLabel("Ningun pallet seleccionado")
        self.pallet_mgr_print_target_lbl.setStyleSheet("color: #eaddd7; font-size: 14px; font-weight: 600;")
        
        form = QGridLayout()
        form.setSpacing(10)
        
        lbl_size = QLabel("Formato:")
        lbl_size.setObjectName("field_label")
        self.pallet_mgr_print_size_cb = QComboBox()
        self.pallet_mgr_print_size_cb.addItems(["4 x 6 pulgadas (102 x 152 mm)", "A4 (Completo)"])
        self.pallet_mgr_print_size_cb.currentTextChanged.connect(self._handle_pallet_mgr_print_config_changed)
        
        lbl_orient = QLabel("Orientacion:")
        lbl_orient.setObjectName("field_label")
        self.pallet_mgr_print_orient_cb = QComboBox()
        self.pallet_mgr_print_orient_cb.addItems(["Horizontal", "Vertical"])
        self.pallet_mgr_print_orient_cb.currentTextChanged.connect(self._handle_pallet_mgr_print_config_changed)
        
        lbl_copies = QLabel("Copias:")
        lbl_copies.setObjectName("field_label")
        self.pallet_mgr_print_copies_sb = QSpinBox()
        self.pallet_mgr_print_copies_sb.setRange(1, 10)
        self.pallet_mgr_print_copies_sb.valueChanged.connect(self._handle_pallet_mgr_print_config_changed)
        
        form.addWidget(lbl_size, 0, 0)
        form.addWidget(self.pallet_mgr_print_size_cb, 0, 1)
        form.addWidget(lbl_orient, 1, 0)
        form.addWidget(self.pallet_mgr_print_orient_cb, 1, 1)
        form.addWidget(lbl_copies, 2, 0)
        form.addWidget(self.pallet_mgr_print_copies_sb, 2, 1)
        
        btn_row = QHBoxLayout()
        
        self.pallet_mgr_print_exec_btn = QPushButton("IMPRIMIR ETIQUETA")
        self.pallet_mgr_print_exec_btn.setObjectName("btn_primary")
        self.pallet_mgr_print_exec_btn.setMinimumHeight(40)
        self.pallet_mgr_print_exec_btn.setEnabled(False)
        self.pallet_mgr_print_exec_btn.clicked.connect(self._handle_pallet_mgr_print_exec)
        
        btn_row.addWidget(self.pallet_mgr_print_exec_btn)
        
        left_col.addWidget(title)
        left_col.addWidget(self.pallet_mgr_print_target_lbl)
        left_col.addLayout(form)
        left_col.addStretch()
        left_col.addLayout(btn_row)
        
        right_col = QVBoxLayout()
        right_col.setAlignment(Qt.AlignCenter)
        
        preview_title = QLabel("Vista Previa")
        preview_title.setObjectName("field_label")
        preview_title.setAlignment(Qt.AlignCenter)
        
        self.pallet_mgr_preview_frame = QFrame()
        self.pallet_mgr_preview_frame.setObjectName("pallet_label_preview_frame")
        self.pallet_mgr_preview_frame.setFixedSize(300, 200)
        
        preview_layout = QVBoxLayout(self.pallet_mgr_preview_frame)
        preview_layout.setContentsMargins(15, 15, 15, 15)
        
        # Elements for preview
        self.prev_lbl_company = QLabel("AGRICOLA S.A.")
        self.prev_lbl_company.setObjectName("pallet_label_company")
        self.prev_lbl_company.setAlignment(Qt.AlignCenter)
        
        self.prev_lbl_code = QLabel("PLT-00000")
        self.prev_lbl_code.setObjectName("pallet_label_code")
        self.prev_lbl_code.setAlignment(Qt.AlignCenter)
        
        self.prev_lbl_mix = QLabel("MIXED")
        self.prev_lbl_mix.setObjectName("pallet_label_mixed_badge")
        self.prev_lbl_mix.setVisible(False)
        
        header_prev = QHBoxLayout()
        header_prev.addWidget(self.prev_lbl_company)
        header_prev.addStretch()
        header_prev.addWidget(self.prev_lbl_mix)
        
        info_prev = QGridLayout()
        self.prev_lbl_pres = QLabel("N/D")
        self.prev_lbl_pres.setObjectName("pallet_label_field_val")
        self.prev_lbl_boxes = QLabel("0 Cajas")
        self.prev_lbl_boxes.setObjectName("pallet_label_field_val")
        self.prev_lbl_weight = QLabel("0.0 KG")
        self.prev_lbl_weight.setObjectName("pallet_label_field_val")
        self.prev_lbl_lot = QLabel("-")
        self.prev_lbl_lot.setObjectName("pallet_label_field_val")
        
        k_pres = QLabel("PRES:")
        k_pres.setObjectName("pallet_label_field_key")
        k_box = QLabel("CAJAS:")
        k_box.setObjectName("pallet_label_field_key")
        k_kg = QLabel("PESO:")
        k_kg.setObjectName("pallet_label_field_key")
        k_lot = QLabel("LOTE:")
        k_lot.setObjectName("pallet_label_field_key")
        
        info_prev.addWidget(k_pres, 0, 0)
        info_prev.addWidget(self.prev_lbl_pres, 0, 1)
        info_prev.addWidget(k_box, 1, 0)
        info_prev.addWidget(self.prev_lbl_boxes, 1, 1)
        info_prev.addWidget(k_kg, 0, 2)
        info_prev.addWidget(self.prev_lbl_weight, 0, 3)
        info_prev.addWidget(k_lot, 1, 2)
        info_prev.addWidget(self.prev_lbl_lot, 1, 3)
        
        self.prev_lbl_bar = QLabel("|| | |||| || ||| || |||")
        self.prev_lbl_bar.setObjectName("pallet_label_barcode")
        self.prev_lbl_bar.setAlignment(Qt.AlignCenter)
        
        preview_layout.addLayout(header_prev)
        preview_layout.addWidget(self.prev_lbl_code)
        preview_layout.addLayout(info_prev)
        preview_layout.addStretch()
        preview_layout.addWidget(self.prev_lbl_bar)
        
        right_col.addWidget(preview_title)
        right_col.addWidget(self.pallet_mgr_preview_frame)
        right_col.addStretch()
        
        layout.addLayout(left_col, 4)
        layout.addLayout(right_col, 6)
        return card


    def _build_pallet_current_card(self) -> QFrame:
        card = self._card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(9)

        title = QLabel("1. PALLET ACTUAL (en armado)")
        title.setObjectName("label_block_title")

        pallet_id_lbl = QLabel("ID del pallet")
        pallet_id_lbl.setObjectName("field_label")

        id_row = QHBoxLayout()
        id_row.setSpacing(8)

        self.current_pallet_id_edit = QLineEdit(self._current_pallet_id)
        self.current_pallet_id_edit.setObjectName("pallet_id_input")

        change_pallet_btn = QPushButton("Cambiar pallet")
        change_pallet_btn.clicked.connect(self._change_current_pallet)

        id_row.addWidget(self.current_pallet_id_edit, 1)
        id_row.addWidget(change_pallet_btn)

        scan_lbl = QLabel("Escanear caja (agregar al pallet)")
        scan_lbl.setObjectName("field_label")

        self.pallet_scan_input = QLineEdit()
        self.pallet_scan_input.setObjectName("pallet_scan_input")
        self.pallet_scan_input.setPlaceholderText("Escanear codigo de caja...")
        self.pallet_scan_input.returnPressed.connect(self._scan_pallet_box)

        progress_title_row = QHBoxLayout()
        progress_title_row.setSpacing(8)

        progress_title = QLabel("Progreso del pallet")
        progress_title.setObjectName("field_label")

        self.pallet_progress_text_lbl = QLabel("0 / 90 cajas")
        self.pallet_progress_text_lbl.setObjectName("field_label")
        self.pallet_progress_text_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        progress_title_row.addWidget(progress_title)
        progress_title_row.addStretch(1)
        progress_title_row.addWidget(self.pallet_progress_text_lbl)

        progress_row = QHBoxLayout()
        progress_row.setSpacing(8)

        self.pallet_progress_bar = QProgressBar()
        self.pallet_progress_bar.setObjectName("pallet_progress_bar")
        self.pallet_progress_bar.setMaximum(self._pallet_capacity)
        self.pallet_progress_bar.setValue(0)
        self.pallet_progress_bar.setTextVisible(False)

        self.pallet_progress_pct_lbl = QLabel("0%")
        self.pallet_progress_pct_lbl.setObjectName("field_label")
        self.pallet_progress_pct_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        progress_row.addWidget(self.pallet_progress_bar, 1)
        progress_row.addWidget(self.pallet_progress_pct_lbl)

        info_wrap = QFrame()
        info_wrap.setObjectName("pallet_info_wrap")
        info_grid = QGridLayout(info_wrap)
        info_grid.setContentsMargins(10, 10, 10, 10)
        info_grid.setHorizontalSpacing(18)
        info_grid.setVerticalSpacing(4)

        info_grid.addWidget(self._preview_key_label("Presentacion"), 0, 0)
        info_grid.addWidget(self._preview_key_label("Capacidad"), 0, 1)
        info_grid.addWidget(self._preview_key_label("Cajas agregadas"), 0, 2)

        self.pallet_presentation_value_lbl = QLabel("Jumbo")
        self.pallet_presentation_value_lbl.setObjectName("pallet_info_value")

        self.pallet_capacity_value_lbl = QLabel(str(self._pallet_capacity))
        self.pallet_capacity_value_lbl.setObjectName("pallet_info_value")

        self.pallet_boxes_added_value_lbl = QLabel("0")
        self.pallet_boxes_added_value_lbl.setObjectName("pallet_info_value")

        info_grid.addWidget(self.pallet_presentation_value_lbl, 1, 0)
        info_grid.addWidget(self.pallet_capacity_value_lbl, 1, 1)
        info_grid.addWidget(self.pallet_boxes_added_value_lbl, 1, 2)

        close_btn = QPushButton("Cerrar pallet")
        close_btn.setObjectName("pallet_close_btn")
        close_btn.clicked.connect(self._close_current_pallet)

        self.pallet_feedback_lbl = QLabel("")
        self.pallet_feedback_lbl.setObjectName("section_hint")
        self.pallet_feedback_lbl.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(pallet_id_lbl)
        layout.addLayout(id_row)
        layout.addWidget(scan_lbl)
        layout.addWidget(self.pallet_scan_input)
        layout.addLayout(progress_title_row)
        layout.addLayout(progress_row)
        layout.addWidget(info_wrap)
        layout.addWidget(close_btn)
        layout.addWidget(self.pallet_feedback_lbl)
        return card

    def _build_pallet_boxes_card(self) -> QFrame:
        card = self._card_frame()
        card.setMaximumHeight(300)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(9)

        title = QLabel("2. CAJAS DEL PALLET ACTUAL")
        title.setObjectName("label_block_title")

        self.pallet_boxes_hint_lbl = QLabel("Cajas escaneadas en el pallet activo.")
        self.pallet_boxes_hint_lbl.setObjectName("section_hint")

        self.pallet_boxes_table = ThemedTable(["#", "Caja ID", "Hora", "Accion"])
        self.pallet_boxes_table.setSortingEnabled(False)
        self.pallet_boxes_table.set_resize_modes(
            {
                0: QHeaderView.Fixed,
                1: QHeaderView.Stretch,
                2: QHeaderView.Fixed,
                3: QHeaderView.Fixed,
            },
            widths={0: 50, 2: 88, 3: 76},
        )
        self.pallet_boxes_table.cellDoubleClicked.connect(self._remove_pallet_box_by_table_row)

        clear_btn = QPushButton("Limpiar lista")
        clear_btn.clicked.connect(self._clear_current_pallet_boxes)

        layout.addWidget(title)
        layout.addWidget(self.pallet_boxes_hint_lbl)
        layout.addWidget(self.pallet_boxes_table, 1)
        layout.addWidget(clear_btn)
        return card

    def _build_completed_pallets_card(self) -> QFrame:
        card = self._card_frame()
        card.setMaximumHeight(300)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(3)

        title = QLabel("3. PALLETS COMPLETADOS (hoy)")
        title.setObjectName("label_block_title")

        subtitle = QLabel("Pallets cerrados durante el turno actual.")
        subtitle.setObjectName("section_hint")

        self.pallet_completed_table = ThemedTable(["Pallet ID", "Presentacion", "Cajas", "Hora cierre", "Acciones"])
        self.pallet_completed_table.setSortingEnabled(False)
        self.pallet_completed_table.set_resize_modes(
            {
                0: QHeaderView.Stretch,
                1: QHeaderView.ResizeToContents,
                2: QHeaderView.Fixed,
                3: QHeaderView.Fixed,
                4: QHeaderView.Fixed,
            },
            widths={2: 66, 3: 92, 4: 82},
        )

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.pallet_completed_table, 1)
        return card

    def _build_pallet_map_card(self) -> QFrame:
        card = self._card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        title = QLabel("4. MAPA DEL PALLET (vista grafica)")
        title.setObjectName("label_block_title")
        title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        title.setMaximumHeight(14)

        subtitle = QLabel("Distribucion de cajas en el pallet actual.")
        subtitle.setObjectName("section_hint")
        subtitle.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        subtitle.setMaximumHeight(10)

        map_wrap = QWidget()
        map_grid = QGridLayout(map_wrap)
        map_grid.setContentsMargins(0, 0, 0, 0)
        map_grid.setHorizontalSpacing(2)
        map_grid.setVerticalSpacing(2)

        self.pallet_map_cells: list[QLabel] = []
        for position in range(1, self._pallet_capacity + 1):
            row = (position - 1) // 10
            col = (position - 1) % 10

            cell = QLabel(str(position))
            cell.setObjectName("pallet_map_cell")
            cell.setAlignment(Qt.AlignCenter)
            cell.setMinimumSize(38, 20)
            map_grid.addWidget(cell, row, col)
            self.pallet_map_cells.append(cell)

        legend = QHBoxLayout()
        legend.setContentsMargins(0, 0, 0, 0)
        legend.setSpacing(0)
        legend.addWidget(self._pallet_legend_item("#2f8c49", "Caja agregada"))
        legend.addWidget(self._pallet_legend_item("#3d4048", "Espacio disponible"))
        legend.addWidget(self._pallet_legend_item("#8b1e1e", "Error / Duplicada"))
        legend.addStretch(1)

        hint = QLabel("La numeracion representa la posicion de las cajas en el pallet.")
        hint.setObjectName("section_hint")
        hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        hint.setMaximumHeight(10)

        layout.addWidget(title, 0)
        layout.addWidget(subtitle, 0)
        layout.addWidget(map_wrap, 0)
        layout.addLayout(legend)
        layout.addWidget(hint, 0)
        return card

    def _build_pallet_summary_card(self) -> QFrame:
        card = self._card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(7)

        title = QLabel("Resumen del dia")
        title.setObjectName("section_title")

        created_row, self.pallet_created_value_lbl = self._summary_row("Pallets creados", "neutral")
        completed_row, self.pallet_completed_value_lbl = self._summary_row("Pallets completados", "neutral")
        boxed_row, self.pallet_boxes_total_value_lbl = self._summary_row("Cajas en pallets", "neutral")
        pending_row, self.pallet_pending_value_lbl = self._summary_row("Cajas pendientes", "neutral")

        layout.addWidget(title)
        layout.addWidget(created_row)
        layout.addWidget(completed_row)
        layout.addWidget(boxed_row)
        layout.addWidget(pending_row)
        return card

    def _build_pallet_activity_panel(self) -> QFrame:
        card = self._card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(7)

        title = QLabel("Actividad reciente")
        title.setObjectName("section_title")

        self.pallet_activity_list = QListWidget()
        self.pallet_activity_list.setObjectName("pallet_activity_list")
        self.pallet_activity_list.setWordWrap(True)
        self.pallet_activity_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        layout.addWidget(title)
        layout.addWidget(self.pallet_activity_list)
        return card

    def _pallet_legend_item(self, color: str, text: str) -> QWidget:
        wrap = QWidget()
        row = QHBoxLayout(wrap)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        chip = QLabel()
        chip.setFixedSize(14, 14)
        chip.setStyleSheet(f"background-color: {color}; border-radius: 2px;")

        label = QLabel(text)
        label.setObjectName("section_hint")

        row.addWidget(chip)
        row.addWidget(label)
        return wrap

    def _build_label_assignment_card(self) -> QFrame:
        card = self._card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(9)

        title = QLabel("INFORMACION DE LA ETIQUETA")
        title.setObjectName("label_block_title")

        self.label_source_hint = QLabel("Caja activa: sin registros en Escaneo")
        self.label_source_hint.setObjectName("section_hint")

        self.label_line_combo = QComboBox()
        self.label_line_combo.setObjectName("label_form_combo")
        line_options = sorted(
            {
                str(item.get("line", "")).strip().upper()
                for item in self._employees
                if str(item.get("line", "")).strip()
            }
        )
        self.label_line_combo.addItems(line_options or ["L07"])

        self.label_date_edit = QDateEdit(QDate.currentDate())
        self.label_date_edit.setObjectName("label_form_date")
        self.label_date_edit.setDisplayFormat("dd/MM/yyyy")
        self.label_date_edit.setCalendarPopup(True)

        self.label_variety_combo = QComboBox()
        self.label_variety_combo.setObjectName("label_form_combo")
        self.label_variety_combo.addItems(list(_LABEL_VARIETY_OPTIONS))

        self.label_presentation_combo = QComboBox()
        self.label_presentation_combo.setObjectName("label_form_combo")
        self.label_presentation_combo.addItems(list(_PRESENTATION_ORDER))

        self.label_client_combo = QComboBox()
        self.label_client_combo.setObjectName("label_form_combo")
        self.label_client_combo.setEditable(True)
        self.label_client_combo.addItems(("Walmart", "Costco", "HEB", "Target") + _DEFAULT_LABEL_CLIENTS)

        self.label_destination_combo = QComboBox()
        self.label_destination_combo.setObjectName("label_form_combo")
        self.label_destination_combo.setEditable(True)
        self.label_destination_combo.addItems(list(_LABEL_DESTINATION_OPTIONS))

        self.label_weight_lb_edit = QLineEdit("11.00")
        self.label_weight_lb_edit.setObjectName("label_form_input")

        self.label_units_edit = QLineEdit("24")
        self.label_units_edit.setObjectName("label_form_input")

        self.label_lot_edit = QLineEdit("9011")
        self.label_lot_edit.setObjectName("label_form_input")

        self.label_pick_code_edit = QLineEdit("A7K39X")
        self.label_pick_code_edit.setObjectName("label_form_input")

        self.label_box_id_edit = QLineEdit("-")
        self.label_box_id_edit.setObjectName("label_form_input")
        self.label_box_id_edit.setReadOnly(True)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        self._add_form_field(grid, 0, 0, "Linea de produccion", self.label_line_combo)
        self._add_form_field(grid, 0, 1, "Fecha", self.label_date_edit)
        self._add_form_field(grid, 1, 0, "Variedad", self.label_variety_combo)
        self._add_form_field(grid, 1, 1, "Presentacion", self.label_presentation_combo)
        self._add_form_field(grid, 2, 0, "Cliente", self.label_client_combo)
        self._add_form_field(grid, 2, 1, "Destino", self.label_destination_combo)
        self._add_form_field(grid, 3, 0, "Peso (lb)", self.label_weight_lb_edit)
        self._add_form_field(grid, 3, 1, "Unidades por caja", self.label_units_edit)
        self._add_form_field(grid, 4, 0, "Lote", self.label_lot_edit)
        self._add_form_field(grid, 4, 1, "VOIS Pick Code", self.label_pick_code_edit)
        self._add_form_field(grid, 5, 0, "Caja ID (secuencial)", self.label_box_id_edit, col_span=2)

        qty_label = QLabel("Cantidad a imprimir")
        qty_label.setObjectName("field_label")

        qty_row = QHBoxLayout()
        qty_row.setSpacing(4)
        self.qty_dec_btn = QPushButton("-")
        self.qty_dec_btn.setObjectName("qty_btn")
        self.qty_dec_btn.clicked.connect(lambda: self._change_label_quantity(-1))

        self.label_qty_value_edit = QLineEdit("1")
        self.label_qty_value_edit.setObjectName("qty_value")
        self.label_qty_value_edit.setReadOnly(True)
        self.label_qty_value_edit.setAlignment(Qt.AlignCenter)

        self.qty_inc_btn = QPushButton("+")
        self.qty_inc_btn.setObjectName("qty_btn")
        self.qty_inc_btn.clicked.connect(lambda: self._change_label_quantity(1))

        qty_row.addWidget(self.qty_dec_btn)
        qty_row.addWidget(self.label_qty_value_edit)
        qty_row.addWidget(self.qty_inc_btn)
        qty_row.addStretch(1)

        self.assign_label_btn = QPushButton("Imprimir Etiqueta")
        self.assign_label_btn.setObjectName("btn_primary")
        self.assign_label_btn.clicked.connect(self._assign_label)

        self.label_feedback_lbl = QLabel("")
        self.label_feedback_lbl.setObjectName("section_hint")
        self.label_feedback_lbl.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(self.label_source_hint)
        layout.addLayout(grid)
        layout.addWidget(qty_label)
        layout.addLayout(qty_row)
        layout.addWidget(self.assign_label_btn)
        layout.addWidget(self.label_feedback_lbl)

        self._clear_label_form()
        return card

    def _build_label_preview_card(self) -> QFrame:
        card = self._card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(9)

        title = QLabel("VISTA PREVIA DE ETIQUETA")
        title.setObjectName("label_block_title")

        controls = QHBoxLayout()
        controls.setSpacing(8)

        size_label = QLabel("Tamano de etiqueta")
        size_label.setObjectName("field_label")

        self.label_size_combo = QComboBox()
        self.label_size_combo.setObjectName("label_form_combo")
        self.label_size_combo.addItems(list(_LABEL_SIZE_OPTIONS))

        orientation_label = QLabel("Orientacion")
        orientation_label.setObjectName("field_label")

        self.orientation_horizontal_btn = QPushButton("Horizontal")
        self.orientation_horizontal_btn.setObjectName("orientation_btn")
        self.orientation_horizontal_btn.setCheckable(True)
        self.orientation_horizontal_btn.clicked.connect(lambda: self._set_label_orientation("Horizontal"))

        self.orientation_vertical_btn = QPushButton("Vertical")
        self.orientation_vertical_btn.setObjectName("orientation_btn")
        self.orientation_vertical_btn.setCheckable(True)
        self.orientation_vertical_btn.clicked.connect(lambda: self._set_label_orientation("Vertical"))

        controls.addWidget(size_label)
        controls.addWidget(self.label_size_combo)
        controls.addStretch(1)
        controls.addWidget(orientation_label)
        controls.addWidget(self.orientation_horizontal_btn)
        controls.addWidget(self.orientation_vertical_btn)

        preview_sheet = QFrame()
        preview_sheet.setObjectName("label_preview_sheet")

        sheet_layout = QVBoxLayout(preview_sheet)
        sheet_layout.setContentsMargins(16, 14, 16, 14)
        sheet_layout.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(8)

        company_wrap = QVBoxLayout()
        company_wrap.setSpacing(0)
        self.preview_company_lbl = QLabel("EMPACADORA XYZ")
        self.preview_company_lbl.setObjectName("preview_company")
        self.preview_product_lbl = QLabel("ESPARRAGO VERDE")
        self.preview_product_lbl.setObjectName("preview_product")

        company_wrap.addWidget(self.preview_company_lbl)
        company_wrap.addWidget(self.preview_product_lbl)

        self.preview_country_badge_lbl = QLabel("PRODUCTO DE\nMEXICO")
        self.preview_country_badge_lbl.setObjectName("preview_country_badge")
        self.preview_country_badge_lbl.setAlignment(Qt.AlignCenter)

        header.addLayout(company_wrap)
        header.addStretch(1)
        header.addWidget(self.preview_country_badge_lbl)

        separator_top = QFrame()
        separator_top.setObjectName("preview_separator")
        separator_top.setFrameShape(QFrame.HLine)

        details_grid = QGridLayout()
        details_grid.setHorizontalSpacing(18)
        details_grid.setVerticalSpacing(2)

        details_grid.addWidget(self._preview_key_label("Variedad:"), 0, 0)
        self.preview_variety_lbl = self._preview_value_label("-")
        details_grid.addWidget(self.preview_variety_lbl, 0, 1)

        details_grid.addWidget(self._preview_key_label("Presentacion:"), 1, 0)
        self.preview_presentation_lbl = self._preview_value_label("-")
        details_grid.addWidget(self.preview_presentation_lbl, 1, 1)

        details_grid.addWidget(self._preview_key_label("Peso:"), 2, 0)
        self.preview_weight_lbl = self._preview_value_label("-")
        details_grid.addWidget(self.preview_weight_lbl, 2, 1)

        details_grid.addWidget(self._preview_key_label("Lote:"), 0, 2)
        self.preview_lot_lbl = self._preview_value_label("-")
        details_grid.addWidget(self.preview_lot_lbl, 0, 3)

        details_grid.addWidget(self._preview_key_label("Fecha:"), 1, 2)
        self.preview_date_lbl = self._preview_value_label("-")
        details_grid.addWidget(self.preview_date_lbl, 1, 3)

        details_grid.addWidget(self._preview_key_label("Cliente:"), 2, 2)
        self.preview_client_lbl = self._preview_value_label("-")
        details_grid.addWidget(self.preview_client_lbl, 2, 3)

        details_grid.addWidget(self._preview_key_label("Destino:"), 3, 2)
        self.preview_destination_lbl = self._preview_value_label("-")
        details_grid.addWidget(self.preview_destination_lbl, 3, 3)

        separator_mid = QFrame()
        separator_mid.setObjectName("preview_separator")
        separator_mid.setFrameShape(QFrame.HLine)

        footer = QHBoxLayout()
        footer.setSpacing(14)

        pick_wrap = QFrame()
        pick_wrap.setObjectName("preview_pick_wrap")
        pick_layout = QVBoxLayout(pick_wrap)
        pick_layout.setContentsMargins(8, 8, 8, 8)
        pick_layout.setSpacing(5)

        pick_title = QLabel("VOIS PICK CODE")
        pick_title.setObjectName("preview_pick_title")

        self.preview_pick_code_lbl = QLabel("-")
        self.preview_pick_code_lbl.setObjectName("preview_pick_code")
        self.preview_pick_code_lbl.setAlignment(Qt.AlignCenter)

        pick_layout.addWidget(pick_title)
        pick_layout.addWidget(self.preview_pick_code_lbl)

        box_wrap = QVBoxLayout()
        box_wrap.setSpacing(2)

        self.preview_box_title_lbl = QLabel("Caja ID")
        self.preview_box_title_lbl.setObjectName("preview_box_title")
        self.preview_box_title_lbl.setAlignment(Qt.AlignCenter)

        self.preview_box_id_lbl = QLabel("-")
        self.preview_box_id_lbl.setObjectName("preview_box_id")
        self.preview_box_id_lbl.setAlignment(Qt.AlignCenter)

        self.preview_barcode_lbl = QLabel("|")
        self.preview_barcode_lbl.setObjectName("preview_barcode")
        self.preview_barcode_lbl.setAlignment(Qt.AlignCenter)

        self.preview_barcode_text_lbl = QLabel("-")
        self.preview_barcode_text_lbl.setObjectName("preview_barcode_text")
        self.preview_barcode_text_lbl.setAlignment(Qt.AlignCenter)

        self.preview_orientation_lbl = QLabel("Orientacion: Horizontal")
        self.preview_orientation_lbl.setObjectName("preview_orientation")
        self.preview_orientation_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        box_wrap.addWidget(self.preview_box_title_lbl)
        box_wrap.addWidget(self.preview_box_id_lbl)
        box_wrap.addWidget(self.preview_barcode_lbl)
        box_wrap.addWidget(self.preview_barcode_text_lbl)
        box_wrap.addWidget(self.preview_orientation_lbl)

        footer.addWidget(pick_wrap)
        footer.addLayout(box_wrap, 1)

        bottom_controls = QHBoxLayout()
        bottom_controls.setSpacing(6)

        refresh_preview_btn = QPushButton("Actualizar vista previa")
        refresh_preview_btn.clicked.connect(self._update_label_preview)

        zoom_out_btn = QPushButton("-")
        zoom_out_btn.setObjectName("qty_btn")
        zoom_out_btn.clicked.connect(lambda: self._change_preview_zoom(-10))

        self.preview_zoom_lbl = QLabel("100%")
        self.preview_zoom_lbl.setObjectName("section_hint")
        self.preview_zoom_lbl.setAlignment(Qt.AlignCenter)

        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setObjectName("qty_btn")
        zoom_in_btn.clicked.connect(lambda: self._change_preview_zoom(10))

        bottom_controls.addWidget(refresh_preview_btn)
        bottom_controls.addStretch(1)
        bottom_controls.addWidget(zoom_out_btn)
        bottom_controls.addWidget(self.preview_zoom_lbl)
        bottom_controls.addWidget(zoom_in_btn)

        sheet_layout.addLayout(header)
        sheet_layout.addWidget(separator_top)
        sheet_layout.addLayout(details_grid)
        sheet_layout.addWidget(separator_mid)
        sheet_layout.addLayout(footer)

        layout.addWidget(title)
        layout.addLayout(controls)
        layout.addWidget(preview_sheet, 1)
        layout.addLayout(bottom_controls)
        return card

    def _build_label_history_card(self) -> QFrame:
        card = self._card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(8)

        title = QLabel("HISTORIAL DE ETIQUETAS GENERADAS")
        title.setObjectName("label_block_title")

        history_btn = QPushButton("Ver historial completo")

        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(history_btn)

        self.labels_history_table = ThemedTable(
            [
                "Fecha",
                "Hora",
                "Caja ID",
                "Variedad",
                "Presentacion",
                "Peso (lb)",
                "Lote",
                "Cliente",
                "VOIS Pick Code",
                "Usuario",
                "Cantidad",
                "Acciones",
            ]
        )
        self.labels_history_table.setSortingEnabled(False)
        self.labels_history_table.set_resize_modes(
            {
                0: QHeaderView.Fixed,
                1: QHeaderView.Fixed,
                2: QHeaderView.Stretch,
                3: QHeaderView.ResizeToContents,
                4: QHeaderView.ResizeToContents,
                5: QHeaderView.Fixed,
                6: QHeaderView.Fixed,
                7: QHeaderView.ResizeToContents,
                8: QHeaderView.ResizeToContents,
                9: QHeaderView.Fixed,
                10: QHeaderView.Fixed,
                11: QHeaderView.ResizeToContents,
            },
            widths={0: 92, 1: 84, 5: 90, 6: 84, 9: 78, 10: 74},
        )

        layout.addLayout(header)
        layout.addWidget(self.labels_history_table)
        return card

    def _add_form_field(
        self,
        grid: QGridLayout,
        row: int,
        col: int,
        title: str,
        field: QWidget,
        col_span: int = 1,
    ) -> None:
        grid.addWidget(self._labeled_field(title, field), row, col, 1, col_span)

    def _labeled_field(self, title: str, field: QWidget) -> QWidget:
        wrap = QWidget()
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        label = QLabel(title)
        label.setObjectName("field_label")

        layout.addWidget(label)
        layout.addWidget(field)
        return wrap

    def _bind_label_form_events(self) -> None:
        self.label_size_combo.currentTextChanged.connect(self._update_label_preview)
        self.label_line_combo.currentTextChanged.connect(self._update_label_preview)
        self.label_variety_combo.currentTextChanged.connect(self._update_label_preview)
        self.label_presentation_combo.currentTextChanged.connect(self._update_label_preview)
        self.label_client_combo.currentTextChanged.connect(self._update_label_preview)
        self.label_destination_combo.currentTextChanged.connect(self._update_label_preview)
        self.label_date_edit.dateChanged.connect(lambda _: self._update_label_preview())

        self.label_weight_lb_edit.textChanged.connect(self._update_label_preview)
        self.label_units_edit.textChanged.connect(self._update_label_preview)
        self.label_lot_edit.textChanged.connect(self._update_label_preview)
        self.label_pick_code_edit.textChanged.connect(self._update_label_preview)
        self.label_box_id_edit.textChanged.connect(self._update_label_preview)

    @staticmethod
    def _preview_key_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("preview_key")
        return label

    @staticmethod
    def _preview_value_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("preview_value")
        return label

    def _apply_local_styles(self) -> None:
        self.setStyleSheet(
            f"""
            QFrame#prod_card {{
                background-color: {SURFACE_LOW};
                border: 1px solid rgba(90,64,60,0.28);
                border-radius: 3px;
            }}
            QTabWidget#production_tabs::pane {{
                border: 1px solid rgba(90,64,60,0.2);
                background-color: {SURFACE_LOW};
                top: -1px;
            }}
            QTabWidget#production_tabs QTabBar::tab {{
                background-color: {SURFACE_HIGHEST};
                color: {ON_SEC_CONT};
                border: 1px solid rgba(90,64,60,0.28);
                padding: 8px 16px;
                min-width: 116px;
            }}
            QTabWidget#production_tabs QTabBar::tab:selected {{
                color: {PRIMARY};
                border-bottom: 2px solid {PRIMARY};
            }}
            QTabWidget#production_tabs QTabBar::tab:hover {{
                color: {PRIMARY};
            }}
            QLabel#section_title {{
                color: {ON_SURFACE};
                font-size: 14px;
                font-weight: 700;
                letter-spacing: 0.3px;
            }}
            QLabel#section_hint {{
                color: {ON_SEC_CONT};
                font-size: 11px;
            }}
            QLabel#field_label {{
                color: {ON_SEC_CONT};
                font-size: 11px;
                font-weight: 600;
            }}
            QLineEdit#scan_input {{
                background-color: {SURFACE_LOWEST};
                border: 1px solid rgba(90,64,60,0.45);
                border-radius: 3px;
                font-size: 32px;
                font-weight: 300;
                padding: 14px 12px;
            }}
            QLineEdit#scan_input:focus {{
                border: 1px solid {PRIMARY};
            }}
            QFrame#label_info_wrap {{
                background-color: {SURFACE_LOWEST};
                border: 1px solid rgba(90,64,60,0.32);
                border-radius: 3px;
            }}
            QLineEdit#label_info_value {{
                background-color: {SURFACE_LOW};
                border: 1px solid rgba(90,64,60,0.3);
                border-radius: 2px;
                padding: 7px 10px;
                font-size: 13px;
                color: {ON_SURFACE};
            }}
            QLineEdit#label_status_value[status_state="created"] {{
                color: #d9a24e;
                font-weight: 700;
            }}
            QLineEdit#label_status_value[status_state="printed"] {{
                color: #7bcf9e;
                font-weight: 700;
            }}
            QFrame#state_tile {{
                background-color: {SURFACE_LOWEST};
                border-radius: 3px;
                border: 1px solid rgba(90,64,60,0.32);
            }}
            QFrame#state_tile[variant="primary"] {{
                border-left: 3px solid {PRIMARY_CONT};
            }}
            QFrame#state_tile[variant="neutral"] {{
                border-left: 3px solid {OUTLINE_VAR};
            }}
            QLabel#tile_label {{
                color: {ON_SEC_CONT};
                font-size: 11px;
            }}
            QLabel#tile_value {{
                color: {ON_SURFACE};
                font-size: 34px;
                font-weight: 300;
            }}
            QLabel#tile_sub {{
                color: {ON_SURFACE};
                font-size: 15px;
                font-weight: 600;
            }}
            QFrame#summary_row {{
                border-radius: 3px;
                border: 1px solid rgba(90,64,60,0.28);
                background-color: {SURFACE_LOWEST};
            }}
            QFrame#summary_row[variant="primary"] {{
                border-left: 3px solid {PRIMARY_CONT};
            }}
            QFrame#summary_row[variant="neutral"] {{
                border-left: 3px solid {OUTLINE_VAR};
            }}
            QFrame#summary_row[variant="warning"] {{
                border-left: 3px solid #a47938;
            }}
            QFrame#summary_row[variant="success"] {{
                border-left: 3px solid #2f9e5c;
            }}
            QLabel#summary_title {{
                color: {ON_SURFACE};
                font-size: 13px;
                font-weight: 600;
            }}
            QLabel#summary_value {{
                color: {ON_SURFACE};
                font-size: 24px;
                font-weight: 300;
            }}
            QListWidget#activity_list {{
                border: 1px solid rgba(90,64,60,0.25);
                border-radius: 3px;
                background-color: {SURFACE_LOWEST};
                padding: 4px;
                min-height: 90px;
                max-height: 140px;
            }}
            QListWidget#activity_list::item {{
                border-bottom: 1px solid rgba(90,64,60,0.2);
                padding: 6px 6px;
                color: {ON_SURFACE};
            }}
            QListWidget#activity_list::item:selected {{
                background-color: rgba(139,0,0,0.35);
                color: {ON_SURFACE};
            }}
            QListWidget#employee_perf_list {{
                border: 1px solid rgba(90,64,60,0.25);
                border-radius: 3px;
                background-color: {SURFACE_LOWEST};
                padding: 4px;
                min-height: 96px;
                max-height: 150px;
            }}
            QListWidget#employee_perf_list::item {{
                border-bottom: 1px solid rgba(90,64,60,0.2);
                padding: 6px 6px;
                color: {ON_SURFACE};
            }}
            QLabel#label_block_title {{
                color: {PRIMARY};
                font-size: 14px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }}
            QLineEdit#label_form_input,
            QDateEdit#label_form_date,
            QComboBox#label_form_combo {{
                background-color: {SURFACE_LOWEST};
                border: 1px solid rgba(90,64,60,0.3);
                border-radius: 2px;
                padding: 7px 10px;
                font-size: 13px;
                color: {ON_SURFACE};
            }}
            QLineEdit#label_form_input:focus,
            QDateEdit#label_form_date:focus,
            QComboBox#label_form_combo:focus {{
                border: 1px solid {PRIMARY};
            }}
            QPushButton#qty_btn {{
                min-width: 24px;
                max-width: 24px;
                min-height: 24px;
                max-height: 24px;
                padding: 0;
                font-size: 14px;
                font-weight: 700;
            }}
            QLineEdit#qty_value {{
                min-width: 46px;
                max-width: 46px;
                background-color: {SURFACE_LOWEST};
                border: 1px solid rgba(90,64,60,0.3);
                border-radius: 2px;
                padding: 4px 4px;
                font-size: 13px;
                color: {ON_SURFACE};
            }}
            QPushButton#orientation_btn {{
                min-width: 86px;
                padding: 6px 10px;
                border: 1px solid rgba(90,64,60,0.35);
                background-color: {SURFACE_HIGHEST};
                color: {ON_SURFACE};
            }}
            QPushButton#orientation_btn:checked {{
                border: 1px solid {PRIMARY};
                background-color: rgba(139,0,0,0.32);
                color: {ON_PRIMARY_CONT};
            }}
            QFrame#label_preview_sheet {{
                background-color: #f4f4f4;
                border: 1px solid #d0d0d0;
                border-radius: 18px;
            }}
            QFrame#preview_pick_wrap {{
                background-color: #eef6ee;
                border: 1px solid #95c19f;
                border-radius: 6px;
            }}
            QFrame#preview_separator {{
                color: #5ea66c;
                border: 0;
                border-top: 1px solid #5ea66c;
            }}
            QLabel#preview_company {{
                color: #111111;
                font-size: 30px;
                font-weight: 800;
                letter-spacing: 0.2px;
            }}
            QLabel#preview_product {{
                color: #1d1d1d;
                font-size: 18px;
                font-weight: 700;
            }}
            QLabel#preview_country_badge {{
                background-color: #4e9d58;
                color: #ffffff;
                border-radius: 6px;
                padding: 8px 10px;
                font-size: 11px;
                font-weight: 700;
            }}
            QLabel#preview_key {{
                color: #1f1f1f;
                font-size: 13px;
                font-weight: 700;
            }}
            QLabel#preview_value {{
                color: #121212;
                font-size: 13px;
                font-weight: 600;
            }}
            QLabel#preview_pick_title {{
                color: #2f8c49;
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 0.4px;
            }}
            QLabel#preview_pick_code {{
                color: #2f8c49;
                font-size: 34px;
                font-weight: 800;
                border: 1px solid #75bc88;
                border-radius: 4px;
                padding: 3px 8px;
                background-color: #f7fff7;
            }}
            QLabel#preview_box_title {{
                color: #2f8c49;
                font-size: 12px;
                font-weight: 700;
            }}
            QLabel#preview_box_id {{
                color: #101010;
                font-size: 42px;
                font-weight: 800;
            }}
            QLabel#preview_barcode {{
                color: #0f0f0f;
                font-family: "Consolas";
                font-size: 15px;
                font-weight: 700;
                letter-spacing: 1px;
            }}
            QLabel#preview_barcode_text {{
                color: #2b2b2b;
                font-size: 13px;
                font-weight: 600;
            }}
            QLabel#preview_orientation {{
                color: #3d3d3d;
                font-size: 11px;
                font-weight: 600;
            }}
            QLineEdit#pallet_id_input,
            QLineEdit#pallet_scan_input {{
                background-color: {SURFACE_LOWEST};
                border: 1px solid rgba(90,64,60,0.3);
                border-radius: 2px;
                padding: 8px 10px;
                font-size: 13px;
                color: {ON_SURFACE};
            }}
            QLineEdit#pallet_id_input:focus,
            QLineEdit#pallet_scan_input:focus {{
                border: 1px solid {PRIMARY};
            }}
            QProgressBar#pallet_progress_bar {{
                background-color: {SURFACE_HIGHEST};
                border: 1px solid rgba(90,64,60,0.3);
                border-radius: 4px;
                min-height: 10px;
                max-height: 10px;
            }}
            QProgressBar#pallet_progress_bar::chunk {{
                background-color: #2f8c49;
                border-radius: 3px;
            }}
            QFrame#pallet_info_wrap {{
                background-color: rgba(14,14,14,0.85);
                border: 1px solid rgba(90,64,60,0.24);
                border-radius: 3px;
            }}
            QLabel#pallet_info_value {{
                color: {ON_SURFACE};
                font-size: 16px;
                font-weight: 700;
            }}
            QPushButton#pallet_close_btn {{
                background-color: #2f4f86;
                color: #dce8ff;
                border: 1px solid #567ac0;
                font-weight: 600;
            }}
            QPushButton#pallet_close_btn:hover {{
                background-color: #3b61a4;
            }}
            QLabel#pallet_map_cell {{
                background-color: #3d4048;
                border: 1px solid rgba(90,64,60,0.28);
                border-radius: 2px;
                color: {ON_SURFACE};
                font-size: 12px;
                font-weight: 600;
            }}
            QListWidget#pallet_activity_list {{
                border: 1px solid rgba(90,64,60,0.25);
                border-radius: 3px;
                background-color: {SURFACE_LOWEST};
                padding: 4px;
                min-height: 140px;
                max-height: 210px;
            }}
            QListWidget#pallet_activity_list::item {{
                border-bottom: 1px solid rgba(90,64,60,0.2);
                padding: 6px 6px;
                color: {ON_SURFACE};
            }}
            QTabWidget#emp_inner_tabs::pane {{
                border: 1px solid rgba(90,64,60,0.18);
                background-color: {SURFACE_LOW};
                top: -1px;
            }}
            QTabWidget#emp_inner_tabs QTabBar::tab {{
                background-color: {SURFACE_HIGHEST};
                color: {ON_SEC_CONT};
                border: 1px solid rgba(90,64,60,0.22);
                padding: 6px 18px;
                min-width: 160px;
                font-size: 12px;
            }}
            QTabWidget#emp_inner_tabs QTabBar::tab:selected {{
                color: {PRIMARY};
                border-bottom: 2px solid {PRIMARY};
            }}
            QTabWidget#emp_inner_tabs QTabBar::tab:hover {{
                color: {PRIMARY};
            }}
            QFrame#badge_preview_frame {{
                background-color: #f5f5f5;
                border: 1px solid #d0c8c0;
                border-radius: 8px;
            }}
            QLabel#badge_company {{
                color: #8b0000;
                font-size: 22px;
                font-weight: 800;
                letter-spacing: 1px;
            }}
            QLabel#badge_id {{
                color: #1a1a1a;
                font-size: 54px;
                font-weight: 800;
            }}
            QLabel#badge_name {{
                color: #333333;
                font-size: 15px;
                font-weight: 600;
            }}
            QLabel#badge_barcode {{
                color: #000000;
                font-family: "Consolas";
                font-size: 18px;
                font-weight: 800;
                letter-spacing: 2px;
            }}
            QLabel#badge_barcode_text {{
                color: #444444;
                font-size: 11px;
                font-family: "Consolas";
                letter-spacing: 1px;
            }}
            QFrame#badge_separator {{
                border: none;
                border-top: 1px solid #c8b8b0;
                margin: 0 20px;
            }}
            QFrame#print_separator {{
                border: none;
                border-top: 1px solid rgba(90,64,60,0.22);
                margin: 4px 0;
            }}
            QPushButton#print_secondary_btn {{
                background-color: {SURFACE_HIGHEST};
                color: {ON_SURFACE};
                border: 1px solid rgba(90,64,60,0.35);
                border-radius: 3px;
                padding: 6px 10px;
                font-size: 12px;
            }}
            QPushButton#print_secondary_btn:hover {{
                border-color: {PRIMARY};
                color: {PRIMARY};
            }}
            QPushButton#print_icon_btn {{
                background-color: {SURFACE_HIGHEST};
                color: {ON_SURFACE};
                border: 1px solid rgba(90,64,60,0.35);
                border-radius: 3px;
                font-size: 16px;
                font-weight: 700;
            }}
            QPushButton#print_icon_btn:hover {{
                border-color: {PRIMARY};
                color: {PRIMARY};
            }}
            QListWidget#print_emp_list {{
                border: 1px solid rgba(90,64,60,0.25);
                border-radius: 3px;
                background-color: {SURFACE_LOWEST};
                padding: 4px;
            }}
            QListWidget#print_emp_list::item {{
                border-bottom: 1px solid rgba(90,64,60,0.15);
                padding: 7px 8px;
                color: {ON_SURFACE};
                font-size: 12px;
            }}
            QListWidget#print_emp_list::item:selected {{
                background-color: rgba(139,0,0,0.28);
                color: {ON_SURFACE};
            }}
            QListWidget#print_emp_list::item:hover {{
                background-color: rgba(139,0,0,0.14);
            }}

            QTabWidget#emp_inner_tabs::pane {{
                border: 1px solid rgba(90,64,60,0.2);
                background-color: transparent;
                top: -1px;
            }}
            QTabWidget#emp_inner_tabs QTabBar::tab {{
                background-color: transparent;
                color: #eaddd7;
                border: 1px solid transparent;
                border-bottom: 1px solid rgba(90,64,60,0.28);
                padding: 6px 14px;
                min-width: 100px;
            }}
            QTabWidget#emp_inner_tabs QTabBar::tab:selected {{
                color: #ffb4a1;
                border: 1px solid rgba(90,64,60,0.28);
                border-bottom: 1px solid #201a18;
                background-color: #201a18;
            }}
            QTabWidget#emp_inner_tabs QTabBar::tab:hover {{
                color: #ffb4a1;
            }}
            QPushButton#print_icon_btn {{
                background-color: #201a18;
                border: 1px solid rgba(90,64,60,0.3);
                border-radius: 3px;
                color: #eaddd7;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton#print_icon_btn:hover {{
                background-color: rgba(90,64,60,0.1);
                border: 1px solid #ffb4a1;
            }}
            QPushButton#print_secondary_btn {{
                background-color: #201a18;
                border: 1px solid rgba(90,64,60,0.3);
                border-radius: 3px;
                color: #eaddd7;
                padding: 6px 12px;
                font-weight: 600;
            }}
            QPushButton#print_secondary_btn:hover {{
                background-color: rgba(90,64,60,0.1);
                border: 1px solid #ffb4a1;
            }}
            QFrame#print_separator {{
                color: rgba(90,64,60,0.2);
            }}
            QPushButton#qty_btn {{
                background-color: #201a18;
                border: 1px solid rgba(90,64,60,0.3);
                border-radius: 3px;
                color: #eaddd7;
                font-size: 16px;
                font-weight: bold;
                width: 30px;
                height: 30px;
            }}
            QPushButton#qty_btn:hover {{
                border: 1px solid #ffb4a1;
            }}
            QLineEdit#qty_value {{
                background-color: #140f0d;
                border: 1px solid rgba(90,64,60,0.3);
                border-radius: 3px;
                color: #eaddd7;
                font-size: 14px;
                font-weight: 600;
                width: 40px;
                height: 30px;
            }}
            QTabWidget#pallet_inner_tabs::pane {{
                border: 1px solid rgba(90,64,60,0.2);
                background-color: transparent;
                top: -1px;
            }}
            QTabWidget#pallet_inner_tabs QTabBar::tab {{
                background-color: transparent;
                color: #eaddd7;
                border: 1px solid transparent;
                border-bottom: 1px solid rgba(90,64,60,0.28);
                padding: 6px 14px;
                min-width: 140px;
            }}
            QTabWidget#pallet_inner_tabs QTabBar::tab:selected {{
                color: #ffb4a1;
                border: 1px solid rgba(90,64,60,0.28);
                border-bottom: 1px solid #201a18;
                background-color: #201a18;
            }}
            QTabWidget#pallet_inner_tabs QTabBar::tab:hover {{
                color: #ffb4a1;
            }}
            QPushButton#pallet_mgr_edit_btn {{
                background-color: #1a3a5c;
                color: #a8d4ff;
                border: 1px solid #2a5a8c;
                border-radius: 3px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton#pallet_mgr_edit_btn:hover {{
                background-color: #245080;
                border-color: #5090c0;
            }}
            QPushButton#pallet_mgr_deact_btn {{
                background-color: #3a1a1a;
                color: #ff9090;
                border: 1px solid #6a2a2a;
                border-radius: 3px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton#pallet_mgr_deact_btn:hover {{
                background-color: #5a2020;
                border-color: #903030;
            }}
            QPushButton#pallet_mgr_react_btn {{
                background-color: #1a3a1a;
                color: #90d090;
                border: 1px solid #2a6a2a;
                border-radius: 3px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton#pallet_mgr_react_btn:hover {{
                background-color: #205a20;
                border-color: #309030;
            }}
            QPushButton#pallet_mgr_print_btn {{
                background-color: #2a2a3a;
                color: #b0b0d0;
                border: 1px solid #4a4a7a;
                border-radius: 3px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton#pallet_mgr_print_btn:hover {{
                background-color: #3a3a5a;
                border-color: #7070a0;
            }}
            QPushButton#pallet_mgr_mix_btn {{
                background-color: #2a1a3a;
                color: #c0a0e0;
                border: 1px solid #5a3a7a;
                border-radius: 3px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton#pallet_mgr_mix_btn:hover {{
                background-color: #3a1a5a;
                border-color: #7a4aa0;
            }}
            QFrame#pallet_label_preview_frame {{
                background-color: #f5f5f5;
                border: 1px solid #d0c8c0;
                border-radius: 8px;
            }}
            QLabel#pallet_label_company {{
                color: #8b0000;
                font-size: 18px;
                font-weight: 800;
                letter-spacing: 1px;
            }}
            QLabel#pallet_label_code {{
                color: #1a1a1a;
                font-size: 26px;
                font-weight: 800;
            }}
            QLabel#pallet_label_field_key {{
                color: #444444;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 0.4px;
            }}
            QLabel#pallet_label_field_val {{
                color: #111111;
                font-size: 12px;
                font-weight: 600;
            }}
            QLabel#pallet_label_barcode {{
                color: #0f0f0f;
                font-family: "Consolas";
                font-size: 13px;
                font-weight: 700;
                letter-spacing: 1px;
            }}
            QLabel#pallet_label_mixed_badge {{
                background-color: #6a3a9a;
                color: #ffffff;
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 10px;
                font-weight: 700;
            }}
            """
        )

    def _card_frame(self) -> QFrame:
        """Create a styled card frame for UI sections."""
        card = QFrame()
        card.setObjectName("prod_card")
        return card

    def _state_tile(self, title: str, value: str, hint: str, variant: str) -> tuple[QFrame, QLabel, QLabel]:

        tile = QFrame()
        tile.setObjectName("state_tile")
        tile.setProperty("variant", variant)
        layout = QVBoxLayout(tile)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(6)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("tile_label")

        value_lbl = QLabel(value)
        value_lbl.setObjectName("tile_value")

        hint_lbl = QLabel(hint)
        hint_lbl.setObjectName("tile_sub")

        layout.addWidget(title_lbl)
        layout.addWidget(value_lbl)
        layout.addStretch()
        layout.addWidget(hint_lbl)
        return tile, value_lbl, hint_lbl

    def _summary_row(self, title: str, variant: str) -> tuple[QFrame, QLabel]:
        row = QFrame()
        row.setObjectName("summary_row")
        row.setProperty("variant", variant)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("summary_title")

        value_lbl = QLabel("—")
        value_lbl.setObjectName("summary_value")
        value_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        layout.addWidget(title_lbl)
        layout.addStretch()
        layout.addWidget(value_lbl)
        return row, value_lbl

    def _load_rows(self) -> None:
        self._rows = production_rows()

    def _load_label_rows(self) -> None:
        self._label_rows = []

    def _load_pallet_data(self) -> None:
        self._completed_pallets = fetch_completed_pallets(limit=60) if hasattr(self, '_completed_pallets') else []

    def _refresh_pallets_ui(self) -> None:
        self._render_pallet_box_table()
        self._render_completed_pallets()
        self._refresh_pallet_map()
        self._refresh_pallet_summary()
        self._refresh_pallet_activity()

    def _render_pallet_box_table(self) -> None:
        self.pallet_boxes_table.setSortingEnabled(False)
        self.pallet_boxes_table.setRowCount(0)
        for row_payload in self._pallet_boxes:
            row = self.pallet_boxes_table.rowCount()
            self.pallet_boxes_table.insertRow(row)
            self.pallet_boxes_table.setRowHeight(row, 34)

            seq = int(row_payload.get("seq", row + 1) or row + 1)
            seq_item = SortableTableItem(str(seq), seq)
            seq_item.setTextAlignment(Qt.AlignCenter)
            self.pallet_boxes_table.setItem(row, 0, seq_item)

            self.pallet_boxes_table.setItem(row, 1, QTableWidgetItem(str(row_payload.get("box_id", ""))))

            time_text = str(row_payload.get("time", "")).strip()
            time_item = SortableTableItem(time_text, self._time_to_seconds(time_text))
            time_item.setTextAlignment(Qt.AlignCenter)
            self.pallet_boxes_table.setItem(row, 2, time_item)

            action_item = QTableWidgetItem(str(row_payload.get("action", "Quitar")))
            action_item.setTextAlignment(Qt.AlignCenter)
            action_item.setForeground(QColor(255, 120, 120))
            self.pallet_boxes_table.setItem(row, 3, action_item)

        current_boxes = len(self._pallet_boxes)
        self.pallet_progress_bar.setValue(current_boxes)
        self.pallet_progress_text_lbl.setText(f"{current_boxes} / {self._pallet_capacity} cajas")
        pct = int(current_boxes / self._pallet_capacity * 100) if self._pallet_capacity else 0
        self.pallet_progress_pct_lbl.setText(f"{pct}%")
        self.pallet_boxes_added_value_lbl.setText(str(current_boxes))
        self.pallet_presentation_value_lbl.setText(self._pallet_presentation)

    def _refresh_pallet_map(self) -> None:
        """Update visual map cells for the current pallet state."""
        filled = len(self._pallet_boxes)

        for position, cell in enumerate(self.pallet_map_cells, start=1):
            if position in self._pallet_error_slots:
                background = "#8b1e1e"
                border = "#b74747"
            elif position <= filled:
                background = "#2f8c49"
                border = "#4ea46a"
            else:
                background = "#3d4048"
                border = "rgba(90,64,60,0.28)"

            cell.setStyleSheet(
                "QLabel {"
                f"background-color: {background};"
                f"border: 1px solid {border};"
                "border-radius: 2px;"
                f"color: {ON_SURFACE};"
                "font-size: 12px;"
                "font-weight: 600;"
                "}"
            )

    def _refresh_pallet_summary(self) -> None:
        pallets_completed = len(getattr(self, '_completed_pallets', []))
        pallets_created = pallets_completed + 1
        boxes_total = sum(int(item.get('boxes', 0) or 0) for item in getattr(self, '_completed_pallets', [])) + len(getattr(self, '_pallet_boxes', []))
        pending = max(0, getattr(self, '_pallet_capacity', 0) - len(getattr(self, '_pallet_boxes', [])))

        try:
            self.pallet_created_value_lbl.setText(str(pallets_created))
            self.pallet_completed_value_lbl.setText(str(pallets_completed))
            self.pallet_boxes_total_value_lbl.setText(str(boxes_total))
            self.pallet_pending_value_lbl.setText(str(pending))
        except Exception:
            pass

    def _refresh_pallet_activity(self) -> None:
        self.pallet_activity_list.clear()

        if not self._pallet_activity_rows:
            self.pallet_activity_list.addItem(QListWidgetItem("Sin actividad en pallets."))
            return

        for line in self._pallet_activity_rows[:12]:
            self.pallet_activity_list.addItem(QListWidgetItem(f"o  {line}"))

    def _build_summary_card(self) -> QFrame:
        card = self._card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        title = QLabel("Resumen del dia")
        title.setObjectName("section_title")
        layout.addWidget(title)

        pairs = [
            ("Cajas registradas", "summary_title"),
            ("Empleados activos", "summary_title"),
            ("Presentaciones", "summary_title"),
            ("Peso total (kg)", "summary_title"),
        ]

        row_widgets = []
        for text, _ in pairs:
            row = QFrame()
            row.setObjectName("summary_row")
            row.setProperty("variant", "neutral")
            row.setStyleSheet("")
            r_layout = QHBoxLayout(row)
            r_layout.setContentsMargins(10, 10, 10, 10)
            r_layout.setSpacing(8)

            lbl = QLabel(text)
            lbl.setObjectName("summary_title")

            val = QLabel("—")
            val.setObjectName("summary_value")
            val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            r_layout.addWidget(lbl)
            r_layout.addStretch()
            r_layout.addWidget(val)
            layout.addWidget(row)
            row_widgets.append(val)

        self.day_boxes_lbl = row_widgets[0]
        self.day_active_employees_lbl = row_widgets[1]
        self.day_presentations_lbl = row_widgets[2]
        self.day_total_weight_lbl = row_widgets[3]

        # Indicador "Total cajas en linea" removido por petición del usuario.
        # Conservamos la propiedad `self.total_boxes_lbl` (no añadida al layout)
        # para que las actualizaciones de texto posteriores no fallen.
        self.total_boxes_lbl = QLabel("0")
        self.total_boxes_lbl.setObjectName("summary_value")
        self.total_boxes_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addStretch()
        return card

    def _build_presentations_card(self) -> QFrame:
        card = self._card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        title = QLabel("Presentaciones")
        title.setObjectName("section_title")
        layout.addWidget(title)

        chart_wrap = QHBoxLayout()
        chart_wrap.setSpacing(12)

        self.presentation_chart = DonutChartWidget()
        chart_wrap.addWidget(self.presentation_chart)

        legend = QVBoxLayout()
        legend.setSpacing(4)
        self.legend_value_labels: dict[str, QLabel] = {}
        for name in _PRESENTATION_ORDER:
            row = QHBoxLayout()
            row.setSpacing(6)
            color = self._presentation_colors.get(name, QColor(188, 194, 208))
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color.name()}; font-size: 12px;")

            lbl = QLabel(f"{name}: 0 (0%)")
            lbl.setObjectName("section_hint")
            self.legend_value_labels[name] = lbl
            row.addWidget(dot)
            row.addWidget(lbl)
            legend.addLayout(row)

        chart_wrap.addLayout(legend)
        chart_wrap.addStretch()
        layout.addLayout(chart_wrap)
        return card

    def _build_employee_performance_card(self) -> QFrame:
        card = self._card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        title = QLabel("Rendimiento por empleado")
        title.setObjectName("section_title")
        layout.addWidget(title)

        self.employee_perf_list = QListWidget()
        self.employee_perf_list.setObjectName("employee_perf_list")
        self.employee_perf_list.setWordWrap(True)
        self.employee_perf_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        layout.addWidget(self.employee_perf_list)
        return card

    def _build_activity_card(self) -> QFrame:
        card = self._card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        title = QLabel("Actividad reciente")
        title.setObjectName("section_title")
        layout.addWidget(title)

        self.activity_list = QListWidget()
        self.activity_list.setObjectName("activity_list")
        self.activity_list.setWordWrap(True)
        self.activity_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        layout.addWidget(self.activity_list)
        return card

    def _build_scan_card(self) -> QFrame:
        card = self._card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(9)

        title = QLabel("Escanear etiquetas (operador + caja)")
        title.setObjectName("section_title")

        self.scan_input = QLineEdit()
        self.scan_input.setObjectName("scan_input")
        self.scan_input.setPlaceholderText("Escanear codigo...")
        self.scan_input.setMinimumWidth(0)
        self.scan_input.returnPressed.connect(self._handle_scan)

        controls = QHBoxLayout()
        controls.setSpacing(8)

        register_btn = QPushButton("Registrar")
        register_btn.setObjectName("btn_primary")
        register_btn.clicked.connect(self._handle_scan)

        self.scan_feedback_lbl = QLabel(
            "Escanea: 1) empleado+caja, 2) label_id de packing_labels para cargar los datos."
        )
        self.scan_feedback_lbl.setObjectName("section_hint")
        self.scan_feedback_lbl.setWordWrap(True)

        controls.addWidget(register_btn)
        controls.addStretch()

        layout.addWidget(title)
        layout.addWidget(self.scan_input)
        layout.addLayout(controls)
        layout.addWidget(self.scan_feedback_lbl)
        return card

    def _build_state_card(self) -> QFrame:
        card = self._card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("Estado actual")
        title.setObjectName("section_title")

        tiles_row = QHBoxLayout()
        tiles_row.setSpacing(8)

        employee_tile, self.employee_code_lbl, self.employee_name_lbl = self._state_tile(
            "Etiqueta empleado/caja", "-", "Sin escanear", "primary"
        )

        arrow = QLabel("->")
        arrow.setAlignment(Qt.AlignCenter)
        arrow.setStyleSheet(f"color: {{ON_SEC_CONT}}; font-size: 18px; font-weight: 600;")
        arrow.setFixedWidth(28)

        waiting_tile, self.waiting_value_lbl, self.waiting_hint_lbl = self._state_tile(
            "Etiqueta packing", "-", "Sin escanear", "neutral"
        )

        tiles_row.addWidget(employee_tile, 1)
        tiles_row.addWidget(arrow)
        tiles_row.addWidget(waiting_tile, 1)

        self.last_activity_lbl = QLabel("Ultima actividad: sin registros.")
        self.last_activity_lbl.setObjectName("section_hint")

        layout.addWidget(title)
        layout.addLayout(tiles_row)
        layout.addWidget(self.last_activity_lbl)
        return card

    def _build_table_card(self) -> QFrame:
        card = self._card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 6, 14, 10)
        layout.setSpacing(10)

        self.table = ThemedTable(
            [
                "#",
                "Hora",
                "CajaID",
                "Empleado",
                "Linea",
                "Producto",
                "Presentacion",
                "Lote",
                "Peso (kg)",
                "Estado",
            ]
        )
        self.table.setSortingEnabled(False)
        self.table.set_resize_modes(
            {
                0: QHeaderView.Fixed,
                1: QHeaderView.Fixed,
                2: QHeaderView.Fixed,
                3: QHeaderView.Fixed,
                4: QHeaderView.Fixed,
                5: QHeaderView.Stretch,
                6: QHeaderView.Fixed,
                7: QHeaderView.Fixed,
                8: QHeaderView.Fixed,
                9: QHeaderView.Fixed,
            },
            widths={0: 42, 1: 92, 2: 128, 3: 132, 4: 62, 6: 116, 7: 108, 8: 92, 9: 112},
        )

        footer = QHBoxLayout()
        footer.setSpacing(8)
        footer.setContentsMargins(0, 10, 0, 10)

        clear_btn = QPushButton("Limpiar lista")
        clear_btn.clicked.connect(self._clear_rows)

        self.table_total_lbl = QLabel("Total cajas: 0")
        self.table_total_lbl.setObjectName("summary_title")
        self.table_total_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        footer.addWidget(clear_btn)
        footer.addStretch(1)
        footer.addWidget(self.table_total_lbl)

        layout.addWidget(self.table, 1)
        layout.addLayout(footer)
        
        return card

    def _sync_table_height_with_perf(self, *_) -> None:
        # Allow the table to expand naturally with the layout
        # Removing the hard max height constraint to allow dynamic resizing
        try:
            table_widget = getattr(self, "table", None)
            if table_widget is None:
                return
            
            # Remove any maximum height constraint to allow expansion
            table_widget.setMaximumHeight(16777215)  # Max possible QT height
        except Exception:
            return

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        try:
            self._sync_table_height_with_perf()
        except Exception:
            pass

    def _render_completed_pallets(self) -> None:
        self.pallet_completed_table.setSortingEnabled(False)
        self.pallet_completed_table.setRowCount(0)

        for row_payload in self._completed_pallets[:40]:
            row = self.pallet_completed_table.rowCount()
            self.pallet_completed_table.insertRow(row)
            self.pallet_completed_table.setRowHeight(row, 35)

            self.pallet_completed_table.setItem(row, 0, QTableWidgetItem(str(row_payload.get("pallet_id", ""))))

            presentation_item = QTableWidgetItem(str(row_payload.get("presentation", "")))
            self.pallet_completed_table.setItem(row, 1, presentation_item)

            boxes = int(row_payload.get("boxes", 0) or 0)
            boxes_item = SortableTableItem(str(boxes), boxes)
            boxes_item.setTextAlignment(Qt.AlignCenter)
            self.pallet_completed_table.setItem(row, 2, boxes_item)

            closed_at = str(row_payload.get("closed_at", "")).strip()
            closed_item = SortableTableItem(closed_at, self._time_to_seconds(f"{closed_at}:00"))
            closed_item.setTextAlignment(Qt.AlignCenter)
            self.pallet_completed_table.setItem(row, 3, closed_item)

            action_item = QTableWidgetItem(str(row_payload.get("actions", "Ver")))
            action_item.setTextAlignment(Qt.AlignCenter)
            action_item.setForeground(QColor(128, 168, 245))
            self.pallet_completed_table.setItem(row, 4, action_item)

    def _set_pallet_feedback(self, text: str, error: bool = False) -> None:
        color = PRIMARY if error else "#7bcf9e"
        self.pallet_feedback_lbl.setStyleSheet(f"color: {color}; font-size: 11px;")
        self.pallet_feedback_lbl.setText(text)

    def _register_pallet_activity(self, text: str) -> None:
        line = str(text).strip()
        if not line:
            return

        self._pallet_activity_rows.insert(0, line)
        self._pallet_activity_rows = self._pallet_activity_rows[:40]

    def _next_pallet_identifier(self) -> str:
        next_id = f"PLT-{self._next_pallet_id:04d}"
        self._next_pallet_id += 1
        return next_id

    def _normalize_pallet_scan(self, raw_value: str) -> str:
        token = str(raw_value).strip().upper()
        if not token:
            return ""

        if token.count("-") >= 2:
            return token

        if self._rows:
            employee_code = str(self._rows[0].get("employee_code", "123")).strip() or "123"
            line = str(self._rows[0].get("line", "L07")).strip().upper() or "L07"
        else:
            employee_code = "123"
            line = "L07"

        return self._normalize_box_id(token, employee_code, line)

    def _append_box_to_current_pallet(self, box_id: str, time_text: str = "") -> None:
        if not box_id:
            return

        if len(self._pallet_boxes) >= self._pallet_capacity:
            return

        key = self._box_compare_key(box_id)
        if any(self._box_compare_key(item.get("box_id", "")) == key for item in self._pallet_boxes):
            return

        seq = len(self._pallet_boxes) + 1
        if not time_text:
            time_text = datetime.now().strftime("%H:%M:%S")

        self._pallet_boxes.append(
            {
                "seq": seq,
                "box_id": str(box_id).strip().upper(),
                "time": time_text,
                "action": "Quitar",
            }
        )

        if seq in self._pallet_error_slots:
            self._pallet_error_slots.discard(seq)

        self._register_pallet_activity(
            f"{time_text}    Caja {str(box_id).strip().upper()} agregada al pallet {self._current_pallet_id}"
        )

    def _scan_pallet_box(self) -> None:
        raw = self.pallet_scan_input.text().strip()
        if not raw:
            self._set_pallet_feedback("Escanea una caja para agregar al pallet.", error=True)
            return

        self.pallet_scan_input.clear()

        if len(self._pallet_boxes) >= self._pallet_capacity:
            self._set_pallet_feedback("El pallet actual ya esta completo. Cierra el pallet para continuar.", error=True)
            return

        box_id = self._normalize_pallet_scan(raw)
        key = self._box_compare_key(box_id)
        now_text = datetime.now().strftime("%H:%M:%S")

        if any(self._box_compare_key(item.get("box_id", "")) == key for item in self._pallet_boxes):
            next_slot = min(len(self._pallet_boxes) + 1, self._pallet_capacity)
            if next_slot > 0:
                self._pallet_error_slots.add(next_slot)

            self._set_pallet_feedback(f"Caja duplicada detectada: {box_id}", error=True)
            self._register_pallet_activity(f"{now_text}    Error: caja duplicada {box_id}")
            self._refresh_pallets_ui()
            return

        employee_code = ""
        if self._rows:
            employee_code = str(self._rows[0].get("employee_code", "")).strip()

        try:
            assign_box_to_pallet(
                pallet_code=self._current_pallet_id,
                box_code=box_id,
                position_index=len(self._pallet_boxes) + 1,
                assembled_by_employee_code=employee_code or None,
            )
        except ValueError as exc:
            message = str(exc)
            if "already assigned to pallet" not in message:
                self._set_pallet_feedback(f"No se pudo registrar en SQL Server: {message}", error=True)
                return

        self._append_box_to_current_pallet(box_id, now_text)
        self._set_pallet_feedback(f"Caja {box_id} agregada al pallet {self._current_pallet_id}.", error=False)
        self._refresh_pallets_ui()

    def _remove_pallet_box_by_table_row(self, row: int, column: int) -> None:
        if column != 3:
            return

        box_item = self.pallet_boxes_table.item(row, 1)
        if box_item is None:
            return

        box_id = box_item.text().strip().upper()
        key = self._box_compare_key(box_id)
        before = len(self._pallet_boxes)

        self._pallet_boxes = [item for item in self._pallet_boxes if self._box_compare_key(item.get("box_id", "")) != key]
        if len(self._pallet_boxes) == before:
            return

        for seq, payload in enumerate(self._pallet_boxes, start=1):
            payload["seq"] = seq

        now_text = datetime.now().strftime("%H:%M:%S")
        self._register_pallet_activity(f"{now_text}    Caja {box_id} retirada del pallet {self._current_pallet_id}")
        self._set_pallet_feedback(f"Caja {box_id} retirada del pallet activo.", error=False)
        self._refresh_pallets_ui()

    def _clear_current_pallet_boxes(self) -> None:
        if not self._pallet_boxes:
            self._set_pallet_feedback("No hay cajas para limpiar en el pallet activo.", error=True)
            return

        total = len(self._pallet_boxes)
        self._pallet_boxes.clear()
        self._pallet_error_slots.clear()

        now_text = datetime.now().strftime("%H:%M:%S")
        self._register_pallet_activity(f"{now_text}    Lista del pallet {self._current_pallet_id} limpiada ({total} cajas)")
        self._set_pallet_feedback("Lista de cajas limpiada.", error=False)
        self._refresh_pallets_ui()

    def _change_current_pallet(self) -> None:
        typed = self.current_pallet_id_edit.text().strip().upper()
        if not re.match(r"^PLT-\d{4,}$", typed):
            typed = self._next_pallet_identifier()

        self._current_pallet_id = typed
        self.current_pallet_id_edit.setText(typed)

        now_text = datetime.now().strftime("%H:%M:%S")
        self._register_pallet_activity(f"{now_text}    Pallet activo cambiado a {typed}")
        self._set_pallet_feedback(f"Pallet activo: {typed}", error=False)
        self._refresh_pallets_ui()

    def _close_current_pallet(self) -> None:
        if not self._pallet_boxes:
            self._set_pallet_feedback("No hay cajas para cerrar el pallet actual.", error=True)
            return

        now_dt = datetime.now()
        boxes_count = len(self._pallet_boxes)

        close_error: str | None = None
        try:
            close_pallet_sql(self._current_pallet_id)
            self._completed_pallets = fetch_completed_pallets(limit=60)
        except Exception as exc:
            close_error = str(exc)

        if close_error:
            self._completed_pallets.insert(
                0,
                {
                    "pallet_id": self._current_pallet_id,
                    "presentation": self._pallet_presentation,
                    "boxes": boxes_count,
                    "closed_at": now_dt.strftime("%H:%M"),
                    "actions": "Ver",
                },
            )
            self._completed_pallets = self._completed_pallets[:60]

        self._register_pallet_activity(
            f"{now_dt.strftime('%H:%M:%S')}    Pallet {self._current_pallet_id} cerrado ({boxes_count} cajas)"
        )

        previous_id = self._current_pallet_id
        self._current_pallet_id = self._next_pallet_identifier()
        self._pallet_boxes.clear()
        self._pallet_error_slots.clear()

        if close_error:
            self._set_pallet_feedback(
                (
                    f"Pallet {previous_id} cerrado localmente. "
                    f"No se pudo actualizar SQL Server: {close_error}"
                ),
                error=True,
            )
        else:
            self._set_pallet_feedback(
                f"Pallet {previous_id} cerrado en SQL Server. Nuevo pallet activo: {self._current_pallet_id}",
                error=False,
            )
        self._refresh_pallets_ui()

    # -----------------------------------------------------------------------
    # Pallet Manager Logic
    # -----------------------------------------------------------------------

    def _on_pallet_inner_tab_changed(self, index: int) -> None:
        if index == 1:
            self._refresh_pallet_mgr_catalog()

    def _refresh_pallet_mgr_catalog(self) -> None:
        if not hasattr(self, "pallet_mgr_table"):
            return
        include_inactive = self.pallet_mgr_show_inactive_cb.isChecked()
        try:
            self._pallet_mgr_rows = fetch_all_pallets(include_inactive)
        except Exception as e:
            self._set_pallet_feedback(f"Error cargando catalogo de pallets: {e}", error=True)
            self._pallet_mgr_rows = []

        self.pallet_mgr_table.setRowCount(len(self._pallet_mgr_rows))
        for row_idx, row_data in enumerate(self._pallet_mgr_rows):
            code = row_data["pallet_code"]
            is_active = row_data["is_active"]
            
            id_item = SortableTableItem(str(row_data["pallet_id"]))
            id_item.setTextAlignment(Qt.AlignCenter)
            self.pallet_mgr_table.setItem(row_idx, 0, id_item)
            
            code_item = QTableWidgetItem(code)
            code_item.setTextAlignment(Qt.AlignCenter)
            if not is_active:
                code_item.setForeground(QColor("#777777"))
                font = code_item.font()
                font.setStrikeOut(True)
                code_item.setFont(font)
            self.pallet_mgr_table.setItem(row_idx, 1, code_item)
            
            status_item = QTableWidgetItem(row_data["status"])
            status_item.setTextAlignment(Qt.AlignCenter)
            self.pallet_mgr_table.setItem(row_idx, 2, status_item)
            
            pres_item = QTableWidgetItem(row_data["detected_presentation"])
            self.pallet_mgr_table.setItem(row_idx, 3, pres_item)
            
            boxes_item = SortableTableItem(str(row_data["boxes_count"]))
            boxes_item.setTextAlignment(Qt.AlignCenter)
            self.pallet_mgr_table.setItem(row_idx, 4, boxes_item)
            
            weight_item = SortableTableItem(f"{row_data['total_weight_kg']:.1f}")
            weight_item.setTextAlignment(Qt.AlignCenter)
            self.pallet_mgr_table.setItem(row_idx, 5, weight_item)
            
            built_item = QTableWidgetItem(row_data["built_at"])
            self.pallet_mgr_table.setItem(row_idx, 6, built_item)
            
            mix_item = QTableWidgetItem("Si" if row_data["is_mixed"] else "No")
            mix_item.setTextAlignment(Qt.AlignCenter)
            self.pallet_mgr_table.setItem(row_idx, 7, mix_item)
            
            act_item = QTableWidgetItem("Si" if is_active else "No")
            act_item.setTextAlignment(Qt.AlignCenter)
            self.pallet_mgr_table.setItem(row_idx, 8, act_item)
            
            actions_w = QWidget()
            actions_l = QHBoxLayout(actions_w)
            actions_l.setContentsMargins(4, 2, 4, 2)
            actions_l.setSpacing(4)
            
            edit_btn = QPushButton("Editar")
            edit_btn.setObjectName("pallet_mgr_edit_btn")
            edit_btn.clicked.connect(lambda _, c=code: self._on_pallet_mgr_action("edit", c))
            
            print_btn = QPushButton("Imp")
            print_btn.setObjectName("pallet_mgr_print_btn")
            print_btn.clicked.connect(lambda _, c=code: self._on_pallet_mgr_action("print", c))
            
            actions_l.addWidget(edit_btn)
            actions_l.addWidget(print_btn)
            
            if is_active:
                deact_btn = QPushButton("Inactivar")
                deact_btn.setObjectName("pallet_mgr_deact_btn")
                deact_btn.clicked.connect(lambda _, c=code: self._on_pallet_mgr_action("deactivate", c))
                actions_l.addWidget(deact_btn)
            else:
                react_btn = QPushButton("Activar")
                react_btn.setObjectName("pallet_mgr_react_btn")
                react_btn.clicked.connect(lambda _, c=code: self._on_pallet_mgr_action("reactivate", c))
                actions_l.addWidget(react_btn)

            self.pallet_mgr_table.setCellWidget(row_idx, 9, actions_w)

    def _on_pallet_mgr_action(self, action: str, code: str) -> None:
        if action == "edit":
            row_data = next((r for r in self._pallet_mgr_rows if r["pallet_code"] == code), None)
            if not row_data:
                return
            self._pallet_mgr_editing_code = code
            self.pallet_mgr_edit_code_lbl.setText(f"Pallet: {code}")
            
            pres = row_data["presentation_override"]
            idx = self.pallet_mgr_pres_combo.findText(pres if pres else "(Automatica)")
            self.pallet_mgr_pres_combo.setCurrentIndex(max(0, idx))
            
            self.pallet_mgr_var_input.setText(row_data["variety"] or "")
            self.pallet_mgr_lot_input.setText(row_data["lot_code"] or "")
            self.pallet_mgr_notes_input.setText(row_data["notes"] or "")
            self.pallet_mgr_save_btn.setEnabled(True)
            
        elif action == "print":
            try:
                data = fetch_pallet_label_data(code)
                if data:
                    self._pallet_label_selected_data = data
                    self.pallet_mgr_print_target_lbl.setText(f"Pallet: {code}")
                    self.pallet_mgr_print_exec_btn.setEnabled(True)
                    self._handle_pallet_mgr_print_config_changed()
            except Exception as e:
                self._set_pallet_feedback(f"Error cargando datos de impresion: {e}", error=True)
                
        elif action == "deactivate":
            try:
                deactivate_pallet(code)
                self._refresh_pallet_mgr_catalog()
            except Exception as e:
                self._set_pallet_feedback(f"Error inactivando pallet: {e}", error=True)
                
        elif action == "reactivate":
            try:
                reactivate_pallet(code)
                self._refresh_pallet_mgr_catalog()
            except Exception as e:
                self._set_pallet_feedback(f"Error activando pallet: {e}", error=True)

    def _handle_pallet_mgr_save(self) -> None:
        if not self._pallet_mgr_editing_code:
            return
        
        pres_text = self.pallet_mgr_pres_combo.currentText()
        pres_override = None if pres_text == "(Automatica)" else pres_text
        
        try:
            update_pallet_info(
                self._pallet_mgr_editing_code,
                variety=self.pallet_mgr_var_input.text(),
                lot_code=self.pallet_mgr_lot_input.text(),
                presentation_override=pres_override,
                notes=self.pallet_mgr_notes_input.text()
            )
            self._set_pallet_feedback(f"Pallet {self._pallet_mgr_editing_code} guardado con exito.")
            self._refresh_pallet_mgr_catalog()
            
            # Reset editor
            self._pallet_mgr_editing_code = None
            self.pallet_mgr_edit_code_lbl.setText("Seleccione un pallet...")
            self.pallet_mgr_var_input.clear()
            self.pallet_mgr_lot_input.clear()
            self.pallet_mgr_notes_input.clear()
            self.pallet_mgr_pres_combo.setCurrentIndex(0)
            self.pallet_mgr_save_btn.setEnabled(False)
        except Exception as e:
            self._set_pallet_feedback(f"Error guardando pallet: {e}", error=True)

    def _handle_pallet_mgr_print_config_changed(self) -> None:
        self._pallet_label_size = self.pallet_mgr_print_size_cb.currentText()
        self._pallet_label_orientation = self.pallet_mgr_print_orient_cb.currentText()
        self._pallet_label_copies = self.pallet_mgr_print_copies_sb.value()
        
        # Update preview
        data = self._pallet_label_selected_data
        if not data:
            return
            
        self.prev_lbl_code.setText(data["pallet_code"])
        self.prev_lbl_pres.setText(data["presentation"])
        self.prev_lbl_boxes.setText(f"{data['boxes_count']} Cajas")
        self.prev_lbl_weight.setText(f"{data['total_weight_kg']:.1f} KG")
        self.prev_lbl_lot.setText(data["lot_code"] or "-")
        self.prev_lbl_mix.setVisible(data["is_mixed"])
        
        if self._pallet_label_orientation == "Vertical":
            self.pallet_mgr_preview_frame.setFixedSize(200, 300)
        else:
            self.pallet_mgr_preview_frame.setFixedSize(300, 200)

    def _handle_pallet_mgr_print_exec(self) -> None:
        data = self._pallet_label_selected_data
        if not data:
            return
            
        try:
            printer = QPrinter(QPrinter.HighResolution)
            if hasattr(self, "print_printer_combo"):
                printer_name = self.print_printer_combo.currentData()
                if printer_name:
                    printer.setPrinterName(printer_name)
                    
            if self._pallet_label_orientation == "Vertical":
                printer.setPageOrientation(QPrinter.Portrait)
            else:
                printer.setPageOrientation(QPrinter.Landscape)
                
            # Basic drawing logic for pallet label based on _print_draw_badge
            painter = QPainter()
            if not painter.begin(printer):
                self._set_pallet_feedback("Fallo al iniciar QPainter para impresion", error=True)
                return
                
            for i in range(self._pallet_label_copies):
                if i > 0:
                    printer.newPage()
                    
                painter.setRenderHint(QPainter.Antialiasing)
                page_rect = printer.pageRect(QPrinter.DevicePixel)
                w = page_rect.width()
                h = page_rect.height()
                
                # Draw border
                pen = QPen(Qt.black, 4)
                painter.setPen(pen)
                painter.drawRect(page_rect.adjusted(10, 10, -10, -10))
                
                # Title
                font = QFont("Arial", 40, QFont.Bold)
                painter.setFont(font)
                painter.drawText(QRectF(0, 50, w, 150), Qt.AlignCenter, "AGRICOLA S.A.")
                
                # Code
                font.setPointSize(80)
                painter.setFont(font)
                painter.drawText(QRectF(0, 200, w, 200), Qt.AlignCenter, data["pallet_code"])
                
                # Info
                font.setPointSize(24)
                font.setBold(False)
                painter.setFont(font)
                info_text = (
                    f"Presentacion: {data['presentation']}\n"
                    f"Cajas: {data['boxes_count']}\n"
                    f"Peso: {data['total_weight_kg']:.1f} kg\n"
                    f"Lote: {data['lot_code'] or '-'}\n"
                    f"Fecha: {data['built_at']}"
                )
                painter.drawText(QRectF(50, 450, w - 100, 300), Qt.AlignLeft | Qt.AlignTop, info_text)
                
                if data["is_mixed"]:
                    font.setPointSize(30)
                    font.setBold(True)
                    painter.setFont(font)
                    painter.drawText(QRectF(50, h - 200, w - 100, 100), Qt.AlignRight, "MIXED PALLET")
                    
            painter.end()
            self._set_pallet_feedback(f"Imprimiendo {self._pallet_label_copies} copias de {data['pallet_code']}...")
            
        except Exception as e:
            self._set_pallet_feedback(f"Error de impresion: {e}", error=True)

    def _normalize_row(self, payload: dict) -> dict:
        time_text = str(payload.get("time", "")).strip() or datetime.now().strftime("%H:%M:%S")

        employee_code = self._normalize_employee_code(str(payload.get("employee_code", "")).strip())
        employee = self._employee_index.get(employee_code, {}) if employee_code else {}
        employee_name = str(payload.get("employee_name", "")).strip() or str(employee.get("name", "")).strip()

        line = str(payload.get("line", "")).strip().upper() or str(employee.get("line", "L07")).strip().upper() or "L07"
        box_id = str(payload.get("box_id", "")).strip().upper()
        if box_id:
            box_id = self._normalize_box_id(box_id, employee_code or "000", line)

        product = str(payload.get("product", "N/D")).strip() or "N/D"
        variety = str(payload.get("variety", "N/D")).strip() or "N/D"
        lot = str(payload.get("lot", "Sin lote")).strip() or "Sin lote"
        status = str(payload.get("status", "Registrada")).strip() or "Registrada"

        weight_kg = self._parse_float_token(str(payload.get("weight_kg", "0")))

        presentation = self._normalize_presentation(str(payload.get("presentation", "")))
        if not presentation:
            presentation = self._presentation_for_box(box_id) if box_id else "Medium"

        return {
            "time": time_text,
            "box_id": box_id,
            "employee_code": employee_code,
            "employee_name": employee_name,
            "line": line,
            "product": product,
            "variety": variety,
            "presentation": presentation,
            "lot": lot,
            "weight_kg": weight_kg,
            "status": status,
            "description_raw": str(payload.get("description_raw", "")).strip(),
        }

    def _refresh_ui(self) -> None:
        self._render_table()
        self._refresh_summary_panels()
        self._refresh_presentations()
        self._refresh_employee_performance()
        self._refresh_activity()
        self._refresh_state()
        self._refresh_labeling_ui()
        self._refresh_pallets_ui()

    def _render_table(self) -> None:
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)

        for index, row_data in enumerate(self._rows, start=1):
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setRowHeight(row, 40)

            seq_item = SortableTableItem(str(index), index)
            seq_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, seq_item)

            time_item = SortableTableItem(row_data["time"], self._time_to_seconds(row_data["time"]))
            time_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, time_item)

            self.table.setItem(row, 2, QTableWidgetItem(row_data["box_id"]))

            employee_item = QTableWidgetItem(f"{row_data['employee_code']} - {row_data['employee_name']}")
            self.table.setItem(row, 3, employee_item)

            line_item = QTableWidgetItem(row_data["line"])
            line_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, line_item)

            product_item = QTableWidgetItem(row_data["product"])
            self.table.setItem(row, 5, product_item)

            presentation_item = QTableWidgetItem(row_data["presentation"])
            self.table.setItem(row, 6, presentation_item)

            lot_item = QTableWidgetItem(row_data["lot"])
            if row_data["lot"] in {"Sin lote", "Sin lote asignado"}:
                lot_item.setForeground(QColor(225, 188, 107))
            self.table.setItem(row, 7, lot_item)

            weight_kg = float(row_data.get("weight_kg", 0.0) or 0.0)
            weight_item = SortableTableItem(f"{weight_kg:.2f}", weight_kg)
            weight_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 8, weight_item)

            status_item = QTableWidgetItem(row_data["status"])
            status_item.setForeground(QColor(100, 205, 140))
            status_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 9, status_item)

    def _refresh_summary_panels(self) -> None:
        total_boxes = len(self._rows)
        active_employees = len({row["employee_code"] for row in self._rows if row["employee_code"]})
        presentation_counts = Counter(row["presentation"] for row in self._rows)
        active_presentations = sum(1 for name in _PRESENTATION_ORDER if presentation_counts.get(name, 0) > 0)
        total_weight_kg = sum(float(row.get("weight_kg", 0.0) or 0.0) for row in self._rows)

        self.day_boxes_lbl.setText(str(total_boxes))
        self.day_active_employees_lbl.setText(str(active_employees))
        self.day_presentations_lbl.setText(str(active_presentations))
        self.day_total_weight_lbl.setText(f"{total_weight_kg:,.1f}")
        self.total_boxes_lbl.setText(str(total_boxes))
        if hasattr(self, "table_total_lbl"):
            self.table_total_lbl.setText(f"Total cajas: {total_boxes}")

    def _refresh_presentations(self) -> None:
        counts = Counter(row["presentation"] for row in self._rows)
        total = sum(counts.values())

        segments = [
            (name, counts.get(name, 0), self._presentation_colors[name])
            for name in _PRESENTATION_ORDER
        ]
        self.presentation_chart.set_segments(segments)

        for name in _PRESENTATION_ORDER:
            count = counts.get(name, 0)
            pct = (count / total * 100.0) if total else 0.0
            pct_text = f"{pct:.1f}%"
            self.legend_value_labels[name].setText(f"{count} ({pct_text})")

    def _refresh_employee_performance(self) -> None:
        self.employee_perf_list.clear()
        if not self._rows:
            self.employee_perf_list.addItem(QListWidgetItem("Sin registros de produccion."))
            return

        stats: dict[tuple[str, str], dict[str, float]] = {}
        for row in self._rows:
            code = str(row.get("employee_code", "")).strip() or "N/D"
            name = str(row.get("employee_name", "")).strip() or "Sin nombre"
            key = (code, name)
            if key not in stats:
                stats[key] = {"boxes": 0.0, "weight_kg": 0.0}

            stats[key]["boxes"] += 1.0
            stats[key]["weight_kg"] += float(row.get("weight_kg", 0.0) or 0.0)

        ranking = sorted(
            stats.items(),
            key=lambda item: (item[1]["boxes"], item[1]["weight_kg"]),
            reverse=True,
        )

        for index, ((code, name), values) in enumerate(ranking[:8], start=1):
            line = f"{index}. {code} - {name} | {int(values['boxes'])} cajas | {values['weight_kg']:.1f} kg"
            self.employee_perf_list.addItem(QListWidgetItem(line))

    def _refresh_activity(self) -> None:
        self.activity_list.clear()
        for row in self._rows[:8]:
            text = (
                f"{row['time']} | Caja {row['box_id']} | "
                f"{row['employee_code']} - {row['employee_name']}"
            )
            self.activity_list.addItem(QListWidgetItem(text))

        if self._rows:
            top = self._rows[0]
            self.last_activity_lbl.setText(
                f"Ultima actividad: {top['time']}    Caja {top['box_id']} registrada"
            )
        else:
            self.last_activity_lbl.setText("Ultima actividad: sin registros.")

    def _refresh_state(self) -> None:
        pending_emp = self._pending_employee_label
        pending_desc = self._pending_description_label

        if pending_emp:
            code = str(pending_emp.get("employee_code", "-")).strip() or "-"
            box_id = str(pending_emp.get("box_id", "")).strip() or "Caja pendiente"
            self.employee_code_lbl.setText(code)
            self.employee_name_lbl.setText(box_id)
        else:
            self.employee_code_lbl.setText("-")
            self.employee_name_lbl.setText("Sin escanear")

        if pending_desc:
            label_id = str(pending_desc.get("label_id", "")).strip() or "Label listo"
            pres = str(pending_desc.get("presentation", "")).strip() or "Descripcion lista"
            lot = str(pending_desc.get("lot", "Sin lote")).strip() or "Sin lote"
            self.waiting_value_lbl.setText(label_id)
            hint_parts = [pres]
            if lot:
                hint_parts.append(f"Lote: {lot}")
            self.waiting_hint_lbl.setText(" | ".join(hint_parts))
        else:
            self.waiting_value_lbl.setText("-")
            self.waiting_hint_lbl.setText("Sin escanear")

    def _refresh_labeling_ui(self) -> None:
        if not hasattr(self, "labels_history_table"):
            return

        self._sync_label_selected_box()
        if self._label_selected_box is None:
            self._clear_label_form()
            self._set_label_feedback("No hay cajas registradas en Escaneo para etiquetar.", error=True)
        else:
            self._populate_label_form(self._label_selected_box)
            self._set_label_feedback("", error=False)

        self._render_label_history()
        self._update_label_preview()

    def _render_label_history(self) -> None:
        self.labels_history_table.setSortingEnabled(False)
        self.labels_history_table.setRowCount(0)

        for row_payload in self._label_rows[:80]:
            row = self.labels_history_table.rowCount()
            self.labels_history_table.insertRow(row)
            self.labels_history_table.setRowHeight(row, 38)

            self.labels_history_table.setItem(row, 0, QTableWidgetItem(row_payload.get("date", "")))

            time_item = SortableTableItem(row_payload.get("time", ""), self._time_to_seconds(row_payload.get("time", "")))
            time_item.setTextAlignment(Qt.AlignCenter)
            self.labels_history_table.setItem(row, 1, time_item)

            self.labels_history_table.setItem(row, 2, QTableWidgetItem(row_payload.get("box_id", "")))
            self.labels_history_table.setItem(row, 3, QTableWidgetItem(row_payload.get("variety", "")))

            presentation_item = QTableWidgetItem(row_payload.get("presentation", ""))
            self.labels_history_table.setItem(row, 4, presentation_item)

            weight_lb = float(row_payload.get("weight_lb", 0.0) or 0.0)
            weight_item = SortableTableItem(f"{weight_lb:.2f}", weight_lb)
            weight_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.labels_history_table.setItem(row, 5, weight_item)

            self.labels_history_table.setItem(row, 6, QTableWidgetItem(row_payload.get("lot", "")))
            self.labels_history_table.setItem(row, 7, QTableWidgetItem(row_payload.get("client", "")))
            self.labels_history_table.setItem(row, 8, QTableWidgetItem(row_payload.get("pick_code", "")))

            user_item = QTableWidgetItem(row_payload.get("user", ""))
            user_item.setTextAlignment(Qt.AlignCenter)
            self.labels_history_table.setItem(row, 9, user_item)

            quantity = int(row_payload.get("quantity", 1) or 1)
            qty_item = SortableTableItem(str(quantity), quantity)
            qty_item.setTextAlignment(Qt.AlignCenter)
            self.labels_history_table.setItem(row, 10, qty_item)

            actions_item = QTableWidgetItem(row_payload.get("actions", "Reimprimir | Ver"))
            actions_item.setForeground(QColor(176, 181, 196))
            actions_item.setTextAlignment(Qt.AlignCenter)
            self.labels_history_table.setItem(row, 11, actions_item)

    def _set_label_feedback(self, text: str, error: bool = False) -> None:
        if not text:
            color = ON_SEC_CONT
        else:
            color = PRIMARY if error else "#7bcf9e"
        self.label_feedback_lbl.setStyleSheet(f"color: {color}; font-size: 11px;")
        self.label_feedback_lbl.setText(text)

    def _clear_label_form(self) -> None:
        self.label_box_id_edit.setText("-")

        if self.label_line_combo.count() > 0:
            self.label_line_combo.setCurrentIndex(0)

        self.label_date_edit.setDate(QDate.currentDate())
        self._set_combo_text(self.label_variety_combo, _LABEL_VARIETY_OPTIONS[0])
        self._set_combo_text(self.label_presentation_combo, "Jumbo")
        self._set_combo_text(self.label_client_combo, "Walmart")
        self._set_combo_text(self.label_destination_combo, "USA")

        self.label_weight_lb_edit.setText("11.00")
        self.label_units_edit.setText("24")
        self.label_lot_edit.setText("9011")
        self.label_pick_code_edit.setText("A7K39X")
        self.label_source_hint.setText("Caja activa: sin registros en Escaneo")
        self._set_label_quantity(1)
        self.assign_label_btn.setEnabled(False)
        self._update_label_preview()

    def _resolve_row_by_box(self, raw_box: str) -> dict | None:
        key = self._box_compare_key(raw_box)
        if not key:
            return None

        for row in self._rows:
            row_key = self._box_compare_key(row.get("box_id", ""))
            if row_key and row_key == key:
                return row
        return None

    def _label_history_by_box(self, box_id: str) -> dict | None:
        box_key = self._box_compare_key(box_id)
        if not box_key:
            return None

        return next(
            (
                item
                for item in self._label_rows
                if self._box_compare_key(item.get("box_id", "")) == box_key
            ),
            None,
        )

    def _sync_label_selected_box(self) -> None:
        if not self._rows:
            self._label_selected_box = None
            return

        payload = self._label_payload_from_row(self._rows[0])

        existing = self._label_history_by_box(payload["box_id"])
        if existing is not None:
            payload["client"] = str(existing.get("client", payload["client"])).strip() or payload["client"]
            payload["destination"] = str(existing.get("destination", payload["destination"])).strip() or payload["destination"]
            payload["lot"] = str(existing.get("lot", payload["lot"])).strip() or payload["lot"]
            payload["pick_code"] = str(existing.get("pick_code", payload["pick_code"])).strip() or payload["pick_code"]
            payload["quantity"] = int(existing.get("quantity", 1) or 1)

        self._label_selected_box = payload

    def _label_payload_from_row(self, row: dict) -> dict:
        box_id = str(row.get("box_id", "")).strip().upper() or "-"
        presentation = str(row.get("presentation", "")).strip() or "Jumbo"
        if presentation not in _PRESENTATION_ORDER:
            presentation = "Jumbo"

        weight_kg = float(row.get("weight_kg", 0.0) or 0.0)
        weight_lb = weight_kg * 2.20462 if weight_kg > 0 else self._default_weight_lb_for_presentation(presentation)

        line = str(row.get("line", "L07")).strip().upper() or "L07"
        lot = str(row.get("lot", "")).strip()
        if not lot or lot in {"Sin lote", "Sin lote asignado"}:
            lot = self._default_lot_for_line(line)

        variety = str(row.get("variety", "")).strip()
        if not variety or variety == "N/D":
            variety = _LABEL_VARIETY_OPTIONS[0]

        destination = str(row.get("destination", "")).strip() or _LABEL_DESTINATION_OPTIONS[0]
        client = str(row.get("client", "")).strip() or "Walmart"
        pick_code = self._pick_code_from_box(box_id)

        return {
            "box_id": box_id,
            "line": line,
            "date": datetime.now().strftime("%d/%m/%Y"),
            "variety": variety,
            "presentation": presentation,
            "weight_lb": weight_lb,
            "units": self._default_units_for_presentation(presentation),
            "lot": lot,
            "client": client,
            "destination": destination,
            "pick_code": pick_code,
            "product": str(row.get("product", "Esparrago verde")).strip() or "Esparrago verde",
            "quantity": 1,
        }

    def _populate_label_form(self, payload: dict) -> None:
        box_id = str(payload.get("box_id", "-")).strip().upper() or "-"
        existing = self._label_history_by_box(box_id)

        line = payload.get("line", "L07")
        date_text = payload.get("date", datetime.now().strftime("%d/%m/%Y"))
        variety = payload.get("variety", _LABEL_VARIETY_OPTIONS[0])
        presentation = payload.get("presentation", "Jumbo")
        client = payload.get("client", "Walmart")
        destination = payload.get("destination", _LABEL_DESTINATION_OPTIONS[0])
        weight_lb = float(payload.get("weight_lb", 0.0) or 0.0)
        units = int(payload.get("units", self._default_units_for_presentation(presentation)) or 1)
        lot = payload.get("lot", self._default_lot_for_line(line))
        pick_code = payload.get("pick_code", self._pick_code_from_box(box_id))
        quantity = int(payload.get("quantity", 1) or 1)

        if existing is not None:
            client = existing.get("client", client)
            destination = existing.get("destination", destination)
            lot = existing.get("lot", lot)
            pick_code = existing.get("pick_code", pick_code)
            quantity = int(existing.get("quantity", quantity) or 1)

        self.label_box_id_edit.setText(box_id)
        self._set_combo_text(self.label_line_combo, line)
        self._set_combo_text(self.label_variety_combo, variety)
        self._set_combo_text(self.label_presentation_combo, presentation)
        self._set_combo_text(self.label_client_combo, client)
        self._set_combo_text(self.label_destination_combo, destination)

        parsed_date = QDate.fromString(str(date_text), "dd/MM/yyyy")
        self.label_date_edit.setDate(parsed_date if parsed_date.isValid() else QDate.currentDate())

        self.label_weight_lb_edit.setText(f"{weight_lb:.2f}")
        self.label_units_edit.setText(str(units))
        self.label_lot_edit.setText(str(lot))
        self.label_pick_code_edit.setText(str(pick_code))

        self._set_label_quantity(quantity)
        self.label_source_hint.setText(f"Caja activa desde Escaneo: {box_id}")
        self.assign_label_btn.setEnabled(box_id != "-")
        self._update_label_preview()

    def _assign_label(self) -> None:
        if self._label_selected_box is None:
            self._set_label_feedback("No hay caja activa para etiquetar.", error=True)
            return

        payload = self._collect_label_form_payload()
        box_id = payload["box_id"]
        if not box_id or box_id == "-":
            self._set_label_feedback("No hay un ID de caja valido para etiquetar.", error=True)
            return

        sequence, label_code = self._next_label_code(box_id)

        row_payload = {
            "date": payload["date"],
            "time": datetime.now().strftime("%H:%M:%S"),
            "box_id": box_id,
            "variety": payload["variety"],
            "presentation": payload["presentation"],
            "weight_lb": payload["weight_lb"],
            "lot": payload["lot"],
            "client": payload["client"],
            "destination": payload["destination"],
            "pick_code": payload["pick_code"],
            "user": "Admin",
            "quantity": payload["quantity"],
            "label_seq": sequence,
            "label_code": label_code,
            "status": "Impresa",
            "actions": "Reimprimir | Ver",
        }

        existing_index = next(
            (
                index
                for index, item in enumerate(self._label_rows)
                if self._box_compare_key(item.get("box_id", "")) == self._box_compare_key(box_id)
            ),
            None,
        )

        if existing_index is not None:
            del self._label_rows[existing_index]

        self._label_rows.insert(0, row_payload)
        self._label_selected_box = {
            "box_id": box_id,
            "line": payload["line"],
            "date": payload["date"],
            "variety": payload["variety"],
            "presentation": payload["presentation"],
            "weight_lb": payload["weight_lb"],
            "units": payload["units"],
            "lot": payload["lot"],
            "client": payload["client"],
            "destination": payload["destination"],
            "pick_code": payload["pick_code"],
            "product": payload["product"],
            "quantity": payload["quantity"],
        }

        self._render_label_history()
        self._update_label_preview()
        self._set_label_feedback(f"Etiqueta {label_code} asignada e impresa para caja {box_id}.", error=False)

    @staticmethod
    def _set_combo_text(combo: QComboBox, value: str) -> None:
        text = str(value or "").strip()
        if not text:
            return

        index = combo.findText(text, Qt.MatchFixedString)
        if index >= 0:
            combo.setCurrentIndex(index)
            return

        if combo.isEditable():
            combo.setEditText(text)
            return

        combo.addItem(text)
        combo.setCurrentIndex(combo.count() - 1)

    @staticmethod
    def _combo_text(combo: QComboBox, fallback: str) -> str:
        text = combo.currentText().strip()
        return text or fallback

    def _change_label_quantity(self, delta: int) -> None:
        self._set_label_quantity(self._label_quantity + delta)
        self._update_label_preview()

    def _set_label_quantity(self, value: int) -> None:
        safe_value = max(1, min(999, int(value)))
        self._label_quantity = safe_value
        self.label_qty_value_edit.setText(str(safe_value))

    def _change_preview_zoom(self, delta: int) -> None:
        self._label_preview_zoom = max(70, min(130, self._label_preview_zoom + delta))
        self.preview_zoom_lbl.setText(f"{self._label_preview_zoom}%")

    def _set_label_orientation(self, orientation: str) -> None:
        normalized = "Vertical" if str(orientation).lower().startswith("v") else "Horizontal"
        self._label_orientation = normalized
        self.orientation_horizontal_btn.setChecked(normalized == "Horizontal")
        self.orientation_vertical_btn.setChecked(normalized == "Vertical")
        self._update_label_preview()

    def _collect_label_form_payload(self) -> dict:
        box_id = self.label_box_id_edit.text().strip().upper() or "-"
        line = self._combo_text(self.label_line_combo, "L07")
        date = self.label_date_edit.date().toString("dd/MM/yyyy")
        variety = self._combo_text(self.label_variety_combo, _LABEL_VARIETY_OPTIONS[0])
        presentation = self._combo_text(self.label_presentation_combo, "Jumbo")
        client = self._combo_text(self.label_client_combo, "Walmart")
        destination = self._combo_text(self.label_destination_combo, _LABEL_DESTINATION_OPTIONS[0])
        weight_lb = self._parse_float_token(self.label_weight_lb_edit.text())

        units = int(round(self._parse_float_token(self.label_units_edit.text())))
        if units <= 0:
            units = self._default_units_for_presentation(presentation)

        lot = self.label_lot_edit.text().strip() or self._default_lot_for_line(line)
        pick_code = self.label_pick_code_edit.text().strip().upper() or self._pick_code_from_box(box_id)

        product = "Esparrago verde"
        if self._label_selected_box is not None:
            product = str(self._label_selected_box.get("product", product)).strip() or product

        return {
            "box_id": box_id,
            "line": line,
            "date": date,
            "variety": variety,
            "presentation": presentation,
            "client": client,
            "destination": destination,
            "weight_lb": max(0.0, weight_lb),
            "units": max(1, units),
            "lot": lot,
            "pick_code": pick_code,
            "product": product,
            "quantity": self._label_quantity,
        }

    def _update_label_preview(self) -> None:
        if not hasattr(self, "preview_box_id_lbl"):
            return

        payload = self._collect_label_form_payload()

        self.preview_company_lbl.setText("EMPACADORA XYZ")
        self.preview_product_lbl.setText(payload["product"].upper())
        self.preview_variety_lbl.setText(payload["variety"])
        self.preview_presentation_lbl.setText(payload["presentation"])

        rounded_weight = round(payload["weight_lb"], 2)
        if abs(rounded_weight - round(rounded_weight)) < 0.01:
            weight_text = f"{int(round(rounded_weight))} lb"
        else:
            weight_text = f"{rounded_weight:.2f} lb"
        self.preview_weight_lbl.setText(weight_text)

        self.preview_lot_lbl.setText(payload["lot"])
        self.preview_date_lbl.setText(payload["date"])
        self.preview_client_lbl.setText(payload["client"])
        self.preview_destination_lbl.setText(payload["destination"])
        self.preview_pick_code_lbl.setText(payload["pick_code"])
        self.preview_box_id_lbl.setText(payload["box_id"])
        self.preview_barcode_text_lbl.setText(payload["box_id"])
        self.preview_barcode_lbl.setText(self._barcode_pattern(payload["box_id"]))
        self.preview_orientation_lbl.setText(
            f"Orientacion: {self._label_orientation} | {payload['quantity']} etiqueta(s)"
        )

    @staticmethod
    def _barcode_pattern(box_id: str) -> str:
        token = "".join(char for char in str(box_id).upper() if char.isalnum())
        if not token:
            return "|"

        bars = []
        for char in token:
            width = (ord(char) % 4) + 1
            bars.append("|" * width)

        return " ".join(bars)[:100]

    @staticmethod
    def _default_units_for_presentation(presentation: str) -> int:
        mapping = {"Jumbo": 24, "Medium": 28, "Small": 32}
        return mapping.get(str(presentation), 24)

    @staticmethod
    def _default_weight_lb_for_presentation(presentation: str) -> float:
        mapping = {"Jumbo": 11.0, "Medium": 9.0, "Small": 7.0}
        return mapping.get(str(presentation), 11.0)

    @staticmethod
    def _default_lot_for_line(line: str) -> str:
        digits = "".join(char for char in str(line) if char.isdigit())
        line_no = int(digits or "7")
        return f"{9000 + line_no + 4}"

    def _pick_code_from_box(self, box_id: str) -> str:
        key = str(box_id).upper()
        if "00045" in key:
            return "A7K39X"

        sequence = self._label_sequence_from_box(key)
        if sequence <= 0:
            sequence = sum(ord(char) for char in key)

        letters = "ABCDEFGHJKLMNPQRSTUVWXYZ"
        return (
            f"{letters[sequence % len(letters)]}"
            f"{sequence % 10}"
            f"{letters[(sequence * 3 + 5) % len(letters)]}"
            f"{(sequence // 10) % 10}"
            f"{letters[(sequence * 7 + 11) % len(letters)]}"
            f"{(sequence // 100) % 10}"
        )

    def _label_sequence_from_box(self, box_id: str) -> int:
        key = self._box_compare_key(box_id)
        digits = "".join(char for char in key if char.isdigit())
        if not digits:
            return 0
        try:
            return int(digits[-5:])
        except ValueError:
            return 0

    def _next_label_code(self, box_id: str) -> tuple[int, str]:
        sequence = self._label_sequence_from_box(box_id)
        if sequence <= 0:
            sequence = self._label_counter

        if sequence >= self._label_counter:
            self._label_counter = sequence + 1

        return sequence, f"ETQ-{sequence:05d}"

    def _handle_scan(self) -> None:
        raw = self.scan_input.text().strip()
        if not raw:
            self._set_scan_feedback("Escanea una etiqueta para registrar.", error=True)
            return

        self.scan_input.clear()

        description_payload = self._parse_description_label(raw)

        has_employee_indicator = any(
            tok in raw.upper()
            for tok in ("EMP", "EMPLEADO", "OPERADOR", "EMP_ID", "EMPLOYEE", "ID_EMPLEADO")
        ) or ("-" in raw)

        if not description_payload or has_employee_indicator:
            employee_payload = self._parse_employee_box_label(raw)
        else:
            employee_payload = None

        if employee_payload:
            self._pending_employee_label = employee_payload

        if description_payload:
            self._pending_description_label = description_payload

        if not employee_payload and not description_payload:
            if self._pending_employee_label is not None:
                self._set_scan_feedback(
                    "No se encontro un packing label valido para ese label_id. Vuelve a escanear el codigo.",
                    error=True,
                )
                self._refresh_state()
                return

            employee = self._resolve_employee(raw)
            if employee is None:
                self._set_scan_feedback(
                    "Etiqueta no reconocida. Usa formato EMP/BOX para operador y un label_id valido para packing_labels.",
                    error=True,
                )
                self._refresh_state()
                return

            code = str(employee.get("code", "")).strip()
            line = str(employee.get("line", "L07")).strip().upper() or "L07"
            self._pending_employee_label = {
                "employee_code": code,
                "employee_name": str(employee.get("name", "")).strip(),
                "line": line,
                "box_id": "",
            }
            self._set_scan_feedback(
                f"Empleado {code} identificado. Escanea un label_id de packing_labels para cargar la etiqueta.",
                error=False,
            )
            self._refresh_state()
            return

        if employee_payload and description_payload:
            self._set_scan_feedback("Packing label detectado. Procesando registro...", error=False)
        elif employee_payload:
            box_hint = str(employee_payload.get("box_id", "")).strip() or "sin caja"
            self._set_scan_feedback(
                f"Etiqueta operador detectada ({box_hint}). Falta el label_id de packing_labels.",
                error=False,
            )
        else:
            label_id = str(description_payload.get("label_id", "")).strip() or "sin label_id"
            self._set_scan_feedback(f"Packing label detectado ({label_id}). Falta etiqueta empleado/caja.", error=False)

        if self._try_register_pending_pair():
            return

        self._refresh_state()

    def _try_register_pending_pair(self) -> bool:
        if not self._pending_employee_label or not self._pending_description_label:
            return False

        employee_payload = self._pending_employee_label
        description_payload = self._pending_description_label

        if not self._labels_match(employee_payload.get("box_id", ""), description_payload.get("box_id", "")):
            self._set_scan_feedback("Las 2 etiquetas no corresponden a la misma caja.", error=True)
            return False

        row_payload = self._build_row_from_pending(employee_payload, description_payload)
        if row_payload is None:
            self._set_scan_feedback("No se pudo determinar un ID de caja valido para registrar.", error=True)
            return False

        try:
            persist_result = persist_production_scan(
                row_payload=row_payload,
            )
        except Exception as exc:
            self._set_scan_feedback(f"Error al registrar en SQL Server: {exc}", error=True)
            return False

        self._rows.insert(0, row_payload)
        self._pending_employee_label = None
        self._pending_description_label = None

        db_status = "creada" if persist_result.get("created", False) else "actualizada"
        self._set_scan_feedback(
            (
                f"Caja {row_payload['box_id']} registrada para "
                f"{row_payload['employee_code']} - {row_payload['employee_name']} "
                f"(SQL: {db_status})."
            ),
            error=False,
        )
        self._refresh_ui()
        return True

    def _build_row_from_pending(self, employee_payload: dict, description_payload: dict) -> dict | None:
        employee_code = self._normalize_employee_code(employee_payload.get("employee_code", ""))
        if not employee_code:
            return None

        employee = self._employee_index.get(employee_code, {})
        employee_name = str(employee_payload.get("employee_name", "")).strip() or str(employee.get("name", "")).strip() or f"Empleado {employee_code}"
        line = str(employee_payload.get("line", "")).strip().upper() or str(employee.get("line", "L07")).strip().upper() or "L07"

        emp_box = str(employee_payload.get("box_id", "")).strip().upper()
        desc_box = str(description_payload.get("box_id", "")).strip().upper()

        if emp_box:
            box_id = self._normalize_box_id(emp_box, employee_code, line)
        elif desc_box:
            box_id = self._normalize_box_id(desc_box, employee_code, line)
        else:
            return None

        presentation = self._normalize_presentation(str(description_payload.get("presentation", "")))
        if not presentation:
            presentation = self._presentation_for_box(box_id)

        lot = str(description_payload.get("lot", "Sin lote")).strip() or "Sin lote"
        product = str(description_payload.get("product", "N/D")).strip() or "N/D"
        variety = str(description_payload.get("variety", "N/D")).strip() or "N/D"
        weight_kg = float(description_payload.get("weight_kg", 0.0) or 0.0)
        client = str(description_payload.get("client", "Walmart")).strip() or "Walmart"
        packed_date = str(description_payload.get("packed_date", "")).strip() or datetime.now().strftime("%d/%m/%Y")

        return {
            "date": packed_date,
            "time": datetime.now().strftime("%H:%M:%S"),
            "box_id": box_id,
            "employee_code": employee_code,
            "employee_name": employee_name,
            "line": line,
            "product": product,
            "variety": variety,
            "presentation": presentation,
            "lot": lot,
            "client": client,
            "weight_kg": weight_kg,
            "status": "Registrada",
            "packing_label_id": str(description_payload.get("label_id", "")).strip(),
            "description_raw": str(description_payload.get("raw", "")).strip(),
        }

    def _parse_employee_box_label(self, raw: str) -> dict | None:
        tokens = self._tokens_from_scan(raw)

        employee_value = self._first_token(
            tokens,
            ("EMP", "EMP_ID", "EMPLOYEE", "EMPLEADO", "ID_EMPLEADO", "OPERADOR"),
        )
        box_value = self._first_token(tokens, _TOKEN_BOX_KEYS)
        line_value = self._first_token(tokens, ("LINE", "LINEA", "LN"))

        if employee_value:
            employee_code = self._normalize_employee_code(employee_value)
            if employee_code:
                employee = self._employee_index.get(employee_code, {})
                line = str(line_value or employee.get("line", "L07")).strip().upper() or "L07"
                box_id = ""
                if box_value:
                    box_id = self._normalize_box_id(box_value, employee_code, line)

                return {
                    "employee_code": employee_code,
                    "employee_name": str(employee.get("name", "")).strip() or f"Empleado {employee_code}",
                    "line": line,
                    "box_id": box_id,
                }

        compact = raw.strip().upper()
        match = re.match(r"^(?P<emp>\d{2,6})-(?P<box>[A-Z0-9]{3,})-(?P<line>L\d{2})$", compact)
        if match:
            employee_code = self._normalize_employee_code(match.group("emp"))
            employee = self._employee_index.get(employee_code, {})
            line = match.group("line")
            return {
                "employee_code": employee_code,
                "employee_name": str(employee.get("name", "")).strip() or f"Empleado {employee_code}",
                "line": line,
                "box_id": self._normalize_box_id(compact, employee_code, line),
            }

        employee = self._resolve_employee(raw)
        if employee is None:
            return None

        employee_code = str(employee.get("code", "")).strip()
        line = str(employee.get("line", "L07")).strip().upper() or "L07"
        return {
            "employee_code": employee_code,
            "employee_name": str(employee.get("name", "")).strip(),
            "line": line,
            "box_id": "",
        }

    def _parse_description_label(self, raw: str) -> dict | None:
        tokens = self._tokens_from_scan(raw)
        label_id = self._first_token(tokens, ("LABEL_ID", "LABEL", "PACKING_LABEL", "PACKING_LABEL_ID"))
        if not label_id:
            label_id = str(raw).strip()

        if not label_id:
            return None

        if not label_id.isdigit():
            return None

        label_payload = fetch_packing_label_by_id(label_id)
        if label_payload is None:
            return None

        packed_date = label_payload.get("packed_date") or label_payload.get("created_at")
        if hasattr(packed_date, "strftime"):
            packed_date_text = packed_date.strftime("%d/%m/%Y")
        else:
            packed_date_text = str(packed_date or "").strip()

        weight_lb = self._parse_float_token(label_payload.get("packed_weight_lb", 0.0))
        weight_kg = round(weight_lb / 2.20462, 3) if weight_lb > 0 else 0.0

        return {
            "label_id": str(label_payload.get("label_id", label_id)).strip(),
            "presentation": self._normalize_presentation(str(label_payload.get("presentation", ""))),
            "product": str(label_payload.get("product_name", "")).strip() or "N/D",
            "lot": str(label_payload.get("lot_code", "")).strip() or "Sin lote",
            "variety": str(label_payload.get("variety_name", "")).strip() or "N/D",
            "client": str(label_payload.get("client_name", "")).strip() or "Walmart",
            "packed_date": packed_date_text,
            "created_at": label_payload.get("created_at"),
            "weight_lb": weight_lb,
            "weight_kg": weight_kg,
            "raw": raw,
        }

    # --- Panel lateral: KPIs globales ---

    def _build_employees_kpi_card(self) -> QFrame:
        card = self._card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        title = QLabel("Resumen del turno")
        title.setObjectName("section_title")
        layout.addWidget(title)

        kpi_grid = QGridLayout()
        kpi_grid.setHorizontalSpacing(10)
        kpi_grid.setVerticalSpacing(6)

        def kpi_cell(label: str) -> tuple[QLabel, QLabel]:
            wrap = QFrame()
            wrap.setObjectName("pallet_info_wrap")
            inner = QVBoxLayout(wrap)
            inner.setContentsMargins(8, 8, 8, 8)
            inner.setSpacing(2)
            val_lbl = QLabel("—")
            val_lbl.setObjectName("pallet_info_value")
            sub_lbl = QLabel(label)
            sub_lbl.setObjectName("section_hint")
            inner.addWidget(val_lbl)
            inner.addWidget(sub_lbl)
            return wrap, val_lbl

        total_wrap, self.emp_kpi_total = kpi_cell("Empleados activos")
        lines_wrap, self.emp_kpi_lines = kpi_cell("Lineas activas")
        boxes_wrap, self.emp_kpi_boxes = kpi_cell("Total cajas hoy")
        avg_wrap, self.emp_kpi_avg = kpi_cell("Promedio cajas/empleado")

        kpi_grid.addWidget(total_wrap, 0, 0)
        kpi_grid.addWidget(lines_wrap, 0, 1)
        kpi_grid.addWidget(boxes_wrap, 1, 0)
        kpi_grid.addWidget(avg_wrap, 1, 1)
        layout.addLayout(kpi_grid)
        return card

    # --- Panel lateral: Performance por empleado ---

    def _build_employees_performance_card(self) -> QFrame:
        card = self._card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        title = QLabel("Desempeno por empleado")
        title.setObjectName("section_title")
        layout.addWidget(title)

        self.emp_perf_scroll_area = QScrollArea()
        self.emp_perf_scroll_area.setWidgetResizable(True)
        self.emp_perf_scroll_area.setFrameShape(QFrame.NoFrame)
        self.emp_perf_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.emp_perf_container = QWidget()
        self.emp_perf_layout = QVBoxLayout(self.emp_perf_container)
        self.emp_perf_layout.setSpacing(6)
        self.emp_perf_layout.setContentsMargins(0, 0, 0, 0)
        self.emp_perf_layout.addStretch()

        self.emp_perf_scroll_area.setWidget(self.emp_perf_container)
        layout.addWidget(self.emp_perf_scroll_area, 1)
        return card

    # ------------------------------------------------------------------ #
    #  Logica de empleados                                                  #
    # ------------------------------------------------------------------ #

    def _emp_boxes_for(self, code: str) -> int:
        """Cuenta cajas registradas hoy para el codigo de empleado dado."""
        normalized = self._normalize_employee_code(code)
        return sum(
            1
            for row in self._rows
            if self._normalize_employee_code(str(row.get("employee_code", ""))) == normalized
        )

    def _emp_filtered_list(self) -> list[dict]:
        line_filter = getattr(self, "emp_line_filter", None)
        search_edit = getattr(self, "emp_search_edit", None)

        selected_line = line_filter.currentText() if line_filter else "Todas"
        search_text = search_edit.text().strip().lower() if search_edit else ""

        result = []
        for emp in self._employees:
            line = str(emp.get("line", "")).strip().upper()
            name = str(emp.get("name", "")).strip().lower()
            code = str(emp.get("code", "")).strip().lower()

            if selected_line not in ("Todas", "") and line != selected_line:
                continue
            if search_text and search_text not in name and search_text not in code:
                continue
            result.append(emp)
        return result

    def _emp_refresh_table(self) -> None:
        table = getattr(self, "emp_table", None)
        if table is None:
            return

        employees = self._emp_filtered_list()
        table.setRowCount(0)

        for emp in employees:
            code = str(emp.get("code", ""))
            name = str(emp.get("name", ""))
            line = str(emp.get("line", ""))
            boxes = self._emp_boxes_for(code)
            goal = int(emp.get("goal", 200))
            pct = min(100, int(boxes / goal * 100)) if goal > 0 else 0

            row = table.rowCount()
            table.insertRow(row)

            table.setItem(row, 0, QTableWidgetItem(code))
            table.setItem(row, 1, QTableWidgetItem(name))
            table.setItem(row, 2, QTableWidgetItem(line))

            boxes_item = SortableTableItem(str(boxes), boxes)
            table.setItem(row, 3, boxes_item)

            # Estado con barra de progreso
            status_widget = QWidget()
            status_layout = QVBoxLayout(status_widget)
            status_layout.setContentsMargins(6, 4, 6, 4)
            status_layout.setSpacing(2)

            bar = QProgressBar()
            bar.setMaximum(100)
            bar.setValue(pct)
            bar.setTextVisible(False)
            bar.setFixedHeight(8)
            if pct >= 80:
                bar.setStyleSheet("QProgressBar::chunk { background: #2f8c49; border-radius: 4px; }")
            elif pct >= 40:
                bar.setStyleSheet("QProgressBar::chunk { background: #b88a1e; border-radius: 4px; }")
            else:
                bar.setStyleSheet("QProgressBar::chunk { background: #8b1e1e; border-radius: 4px; }")

            pct_lbl = QLabel(f"{pct}%")
            pct_lbl.setObjectName("section_hint")
            pct_lbl.setAlignment(Qt.AlignRight)

            status_layout.addWidget(bar)
            status_layout.addWidget(pct_lbl)
            table.setCellWidget(row, 4, status_widget)

            # Botones de accion
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(4)

            edit_btn = QPushButton("✏")
            edit_btn.setFixedSize(30, 24)
            edit_btn.setToolTip("Editar empleado")
            edit_btn.setStyleSheet(
                "QPushButton { background: rgba(80,120,200,0.18); border: 1px solid rgba(80,120,200,0.5);"
                " border-radius: 3px; color: #8ab4f8; font-size: 12px; }"
                "QPushButton:hover { background: rgba(80,120,200,0.35); }"
            )
            edit_btn.clicked.connect(lambda _, c=code: self._emp_start_edit(c))

            del_btn = QPushButton("✕")
            del_btn.setFixedSize(30, 24)
            del_btn.setToolTip("Eliminar empleado")
            del_btn.setStyleSheet(
                "QPushButton { background: rgba(180,30,30,0.18); border: 1px solid rgba(180,30,30,0.5);"
                " border-radius: 3px; color: #f28b82; font-size: 12px; }"
                "QPushButton:hover { background: rgba(180,30,30,0.35); }"
            )
            del_btn.clicked.connect(lambda _, c=code: self._emp_delete(c))

            action_layout.addWidget(edit_btn)
            action_layout.addWidget(del_btn)
            table.setCellWidget(row, 5, action_widget)

        self._emp_refresh_kpis()
        self._emp_refresh_performance()

    def _emp_refresh_kpis(self) -> None:
        if not hasattr(self, "emp_kpi_total"):
            return

        employees = self._employees
        lines = {str(e.get("line", "")).strip().upper() for e in employees if e.get("line")}
        total_boxes = sum(self._emp_boxes_for(str(e.get("code", ""))) for e in employees)
        avg = round(total_boxes / len(employees), 1) if employees else 0

        self.emp_kpi_total.setText(str(len(employees)))
        self.emp_kpi_lines.setText(str(len(lines)))
        self.emp_kpi_boxes.setText(str(total_boxes))
        self.emp_kpi_avg.setText(str(avg))

    def _emp_refresh_performance(self) -> None:
        if not hasattr(self, "emp_perf_layout"):
            return

        # Limpiar widgets anteriores (excepto el stretch final)
        while self.emp_perf_layout.count() > 1:
            item = self.emp_perf_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        employees = sorted(
            self._employees,
            key=lambda e: self._emp_boxes_for(str(e.get("code", ""))),
            reverse=True,
        )

        for emp in employees:
            code = str(emp.get("code", ""))
            name = str(emp.get("name", ""))
            line = str(emp.get("line", ""))
            boxes = self._emp_boxes_for(code)
            goal = int(emp.get("goal", 200))
            pct = min(100, int(boxes / goal * 100)) if goal > 0 else 0

            row_wrap = QFrame()
            row_wrap.setObjectName("pallet_info_wrap")
            row_layout = QVBoxLayout(row_wrap)
            row_layout.setContentsMargins(8, 8, 8, 8)
            row_layout.setSpacing(4)

            header_row = QHBoxLayout()
            name_lbl = QLabel(name)
            name_lbl.setObjectName("field_label")
            line_badge = QLabel(line)
            line_badge.setStyleSheet(
                "background: rgba(80,100,180,0.25); color: #8ab4f8;"
                " border-radius: 3px; padding: 1px 6px; font-size: 10px;"
            )
            boxes_lbl = QLabel(f"{boxes} cajas")
            boxes_lbl.setObjectName("section_hint")
            boxes_lbl.setAlignment(Qt.AlignRight)

            header_row.addWidget(name_lbl)
            header_row.addWidget(line_badge)
            header_row.addStretch()
            header_row.addWidget(boxes_lbl)

            perf_bar = QProgressBar()
            perf_bar.setMaximum(100)
            perf_bar.setValue(pct)
            perf_bar.setTextVisible(False)
            perf_bar.setFixedHeight(6)
            if pct >= 80:
                bar_color = "#2f8c49"
            elif pct >= 40:
                bar_color = "#b88a1e"
            else:
                bar_color = "#8b1e1e"
            perf_bar.setStyleSheet(
                f"QProgressBar {{ background: rgba(255,255,255,0.08); border-radius: 3px; }}"
                f"QProgressBar::chunk {{ background: {bar_color}; border-radius: 3px; }}"
            )

            pct_row = QHBoxLayout()
            pct_row.addWidget(perf_bar, 1)
            pct_lbl = QLabel(f"{pct}%")
            pct_lbl.setObjectName("section_hint")
            pct_lbl.setFixedWidth(32)
            pct_lbl.setAlignment(Qt.AlignRight)
            pct_row.addWidget(pct_lbl)

            row_layout.addLayout(header_row)
            row_layout.addLayout(pct_row)

            self.emp_perf_layout.insertWidget(self.emp_perf_layout.count() - 1, row_wrap)

    # --- CRUD ---

    def _emp_save(self) -> None:
        code = self.emp_form_code.text().strip()
        name = self.emp_form_name.text().strip()
        line = self.emp_form_line.text().strip().upper()
        goal = self.emp_form_goal.value()

        if not code or not name or not line:
            self.emp_form_feedback.setStyleSheet(f"color: {PRIMARY}; font-size: 11px;")
            self.emp_form_feedback.setText("Completa todos los campos obligatorios.")
            return

        normalized = self._normalize_employee_code(code)

        if self._emp_editing_code is not None:
            # Edicion: buscar y actualizar
            for emp in self._employees:
                if self._normalize_employee_code(str(emp.get("code", ""))) == self._normalize_employee_code(self._emp_editing_code):
                    emp["code"] = code
                    emp["name"] = name
                    emp["line"] = line
                    emp["goal"] = goal
                    break
            # Reconstruir indice
            self._employee_index = {
                self._normalize_employee_code(e.get("code", "")): e for e in self._employees
            }
            self.emp_form_feedback.setStyleSheet("color: #5c9a70; font-size: 11px;")
            self.emp_form_feedback.setText(f"Empleado '{name}' actualizado correctamente.")
            self._emp_cancel_edit()
        else:
            # Alta: verificar duplicado
            if normalized in self._employee_index:
                self.emp_form_feedback.setStyleSheet(f"color: {PRIMARY}; font-size: 11px;")
                self.emp_form_feedback.setText(f"Ya existe un empleado con el codigo '{code}'.")
                return

            new_emp = {"code": code, "name": name, "line": line, "goal": goal}
            self._employees.append(new_emp)
            self._employee_index[normalized] = new_emp
            self.emp_form_feedback.setStyleSheet("color: #5c9a70; font-size: 11px;")
            self.emp_form_feedback.setText(f"Empleado '{name}' agregado correctamente.")
            self.emp_form_code.clear()
            self.emp_form_name.clear()
            self.emp_form_line.clear()
            self.emp_form_goal.setValue(200)

        self._emp_refresh_table()

        # Actualizar combo de lineas en etiquetas
        if hasattr(self, "label_line_combo"):
            current_text = self.label_line_combo.currentText()
            lines = sorted(
                {str(e.get("line", "")).strip().upper() for e in self._employees if e.get("line")}
            )
            self.label_line_combo.blockSignals(True)
            self.label_line_combo.clear()
            self.label_line_combo.addItems(lines)
            idx = self.label_line_combo.findText(current_text)
            if idx >= 0:
                self.label_line_combo.setCurrentIndex(idx)
            self.label_line_combo.blockSignals(False)

    def _emp_start_edit(self, code: str) -> None:
        emp = self._employee_index.get(self._normalize_employee_code(code))
        if emp is None:
            return

        self.emp_form_code.setText(str(emp.get("code", "")))
        self.emp_form_name.setText(str(emp.get("name", "")))
        self.emp_form_line.setText(str(emp.get("line", "")))
        self.emp_form_goal.setValue(int(emp.get("goal", 200)))
        self._emp_editing_code = code
        self.emp_form_title.setText("EDITAR EMPLEADO")
        self.emp_cancel_btn.setVisible(True)
        self.emp_save_btn.setText("Actualizar")
        self.emp_form_feedback.setText("")

        # Ir al tab de empleados y hacer scroll al formulario
        self.tabs.setCurrentWidget(self.employees_tab)

    def _emp_cancel_edit(self) -> None:
        self._emp_editing_code = None
        self.emp_form_title.setText("AGREGAR EMPLEADO")
        self.emp_cancel_btn.setVisible(False)
        self.emp_save_btn.setText("Guardar")
        self.emp_form_code.clear()
        self.emp_form_name.clear()
        self.emp_form_line.clear()
        self.emp_form_goal.setValue(200)
        self.emp_form_feedback.setText("")

    def _emp_delete(self, code: str) -> None:
        normalized = self._normalize_employee_code(code)
        before = len(self._employees)
        self._employees = [e for e in self._employees if self._normalize_employee_code(str(e.get("code", ""))) != normalized]
        self._employee_index = {
            self._normalize_employee_code(e.get("code", "")): e for e in self._employees
        }
        if len(self._employees) < before:
            self.emp_form_feedback.setStyleSheet("color: #5c9a70; font-size: 11px;")
            self.emp_form_feedback.setText(f"Empleado con codigo '{code}' eliminado.")
        self._emp_refresh_table()

    def _emp_on_selection_changed(self) -> None:
        """Seleccionar una fila pre-rellena el formulario para edicion rapida."""
        table = getattr(self, "emp_table", None)
        if table is None:
            return
        selected = table.selectedItems()
        if not selected:
            return
        row = table.currentRow()
        code_item = table.item(row, 0)
        if code_item:
            self._emp_start_edit(code_item.text())

    def _tokens_from_scan(self, raw: str) -> list[str]:
        text = str(raw).strip().upper()
        return [part.strip() for part in re.split(r'[,\|]', text) if part.strip()]

    def _first_token(self, tokens: list[str], keys: tuple[str, ...]) -> str | None:
        for token in tokens:
            if ":" in token:
                key, value = token.split(":", 1)
                if key.strip() in keys:
                    return value.strip()
            elif "=" in token:
                key, value = token.split("=", 1)
                if key.strip() in keys:
                    return value.strip()
        return None

    def _parse_float_token(self, raw: str | float) -> float:
        if isinstance(raw, (int, float)):
            return float(raw)
        text = str(raw).strip()
        numeric_str = "".join(char for char in text if char.isdigit() or char == ".")
        try:
            return float(numeric_str)
        except ValueError:
            return 0.0

    def _normalize_presentation(self, raw: str) -> str:
        text = str(raw).strip().upper()
        for presentation in _PRESENTATION_ORDER:
            if presentation.upper() in text:
                return presentation
        return "Jumbo"

    def _box_compare_key(self, raw: str) -> str:
        text = str(raw).strip().upper()
        parts = text.split("-")
        if len(parts) >= 3:
            middle = "".join(char for char in parts[1] if char.isalnum())
            if middle:
                return middle.lstrip("0") or "0"
        digits = "".join(char for char in text if char.isdigit())
        if digits:
            return digits.lstrip("0") or "0"
        return "".join(char for char in text if char.isalnum())

    def _labels_match(self, employee_box: str, description_box: str) -> bool:
        emp_key = self._box_compare_key(employee_box)
        desc_key = self._box_compare_key(description_box)
        if emp_key and desc_key:
            return emp_key == desc_key
        return True

    # ------------------------------------------------------------------ #
    #  PESTAÑA EMPLEADOS                                                   #
    # ------------------------------------------------------------------ #

    def _build_employees_tab(self, tab: QWidget) -> None:
        root = QVBoxLayout(tab)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.emp_inner_tabs = QTabWidget()
        self.emp_inner_tabs.setObjectName("emp_inner_tabs")

        self.emp_production_subtab = QWidget()
        self._build_emp_production_subtab(self.emp_production_subtab)

        self.emp_printing_subtab = QWidget()
        self._build_emp_printing_subtab(self.emp_printing_subtab)

        self.emp_inner_tabs.addTab(self.emp_production_subtab, "Empleados de Produccion")
        self.emp_inner_tabs.addTab(self.emp_printing_subtab, "Empleados Impresion")

        root.addWidget(self.emp_inner_tabs, 1)

    def _build_emp_production_subtab(self, tab: QWidget) -> None:
        root = QHBoxLayout(tab)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        left_col = QVBoxLayout()
        left_col.setSpacing(10)
        left_col.addWidget(self._build_employees_filter_card())
        left_col.addWidget(self._build_employees_table_card(), 1)
        left_col.addWidget(self._build_employee_form_card())

        right_col = QVBoxLayout()
        right_col.setSpacing(10)
        right_col.addWidget(self._build_employees_kpi_card())
        right_col.addWidget(self._build_employees_performance_card(), 1)
        right_col.addStretch()

        right_wrap = QWidget()
        right_wrap.setLayout(right_col)
        right_wrap.setFixedWidth(310)

        root.addLayout(left_col, 1)
        root.addWidget(right_wrap)

        self._emp_refresh_table()
        self._emp_refresh_kpis()

    def _build_employees_filter_card(self) -> QFrame:
        card = self._card_frame()
        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        title = QLabel("EMPLEADOS DE PRODUCCION")
        title.setObjectName("label_block_title")

        line_lbl = QLabel("Linea:")
        line_lbl.setObjectName("field_label")

        self.emp_line_filter = QComboBox()
        self.emp_line_filter.setObjectName("label_form_combo")
        lines = sorted(
            {
                str(e.get("line", "")).strip().upper()
                for e in self._employees
                if str(e.get("line", "")).strip()
            }
        )
        self.emp_line_filter.addItems(["Todas"] + lines)
        self.emp_line_filter.currentIndexChanged.connect(self._emp_refresh_table)

        search_lbl = QLabel("Buscar:")
        search_lbl.setObjectName("field_label")

        self.emp_search_edit = QLineEdit()
        self.emp_search_edit.setObjectName("label_form_input")
        self.emp_search_edit.setPlaceholderText("Nombre o codigo...")
        self.emp_search_edit.textChanged.connect(self._emp_refresh_table)

        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(line_lbl)
        layout.addWidget(self.emp_line_filter)
        layout.addWidget(search_lbl)
        layout.addWidget(self.emp_search_edit)
        return card

    def _build_employees_table_card(self) -> QFrame:
        card = self._card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        title = QLabel("Listado de empleados")
        title.setObjectName("section_title")

        self.emp_table = ThemedTable(
            ["Codigo", "Nombre", "Linea", "Cajas hoy", "Estado", "Acciones"]
        )
        self.emp_table.setSortingEnabled(True)
        self.emp_table.set_resize_modes(
            {
                0: QHeaderView.Fixed,
                1: QHeaderView.Stretch,
                2: QHeaderView.Fixed,
                3: QHeaderView.Fixed,
                4: QHeaderView.ResizeToContents,
                5: QHeaderView.Fixed,
            },
            widths={0: 72, 2: 64, 3: 80, 5: 90},
        )
        self.emp_table.itemSelectionChanged.connect(self._emp_on_selection_changed)

        layout.addWidget(title)
        layout.addWidget(self.emp_table, 1)
        return card

    def _build_employee_form_card(self) -> QFrame:
        card = self._card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        self.emp_form_title = QLabel("AGREGAR EMPLEADO")
        self.emp_form_title.setObjectName("label_block_title")

        form_grid = QGridLayout()
        form_grid.setContentsMargins(0, 0, 0, 0)
        form_grid.setHorizontalSpacing(12)
        form_grid.setVerticalSpacing(8)

        code_lbl = QLabel("Codigo")
        code_lbl.setObjectName("field_label")
        self.emp_form_code = QLineEdit()
        self.emp_form_code.setObjectName("label_form_input")
        self.emp_form_code.setPlaceholderText("Ej. 130")
        form_grid.addWidget(code_lbl, 0, 0)
        form_grid.addWidget(self.emp_form_code, 1, 0)

        name_lbl = QLabel("Nombre completo")
        name_lbl.setObjectName("field_label")
        self.emp_form_name = QLineEdit()
        self.emp_form_name.setObjectName("label_form_input")
        self.emp_form_name.setPlaceholderText("Nombre y apellido")
        form_grid.addWidget(name_lbl, 0, 1)
        form_grid.addWidget(self.emp_form_name, 1, 1)

        line_lbl = QLabel("Linea")
        line_lbl.setObjectName("field_label")
        self.emp_form_line = QLineEdit()
        self.emp_form_line.setObjectName("label_form_input")
        self.emp_form_line.setPlaceholderText("Ej. L07")
        form_grid.addWidget(line_lbl, 0, 2)
        form_grid.addWidget(self.emp_form_line, 1, 2)

        goal_lbl = QLabel("Meta (cajas/dia)")
        goal_lbl.setObjectName("field_label")
        self.emp_form_goal = QSpinBox()
        self.emp_form_goal.setObjectName("label_form_input")
        self.emp_form_goal.setRange(1, 9999)
        self.emp_form_goal.setValue(200)
        form_grid.addWidget(goal_lbl, 0, 3)
        form_grid.addWidget(self.emp_form_goal, 1, 3)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.emp_save_btn = QPushButton("Guardar")
        self.emp_save_btn.setObjectName("btn_primary")
        self.emp_save_btn.clicked.connect(self._emp_save)

        self.emp_cancel_btn = QPushButton("Cancelar")
        self.emp_cancel_btn.clicked.connect(self._emp_cancel_edit)
        self.emp_cancel_btn.setVisible(False)

        btn_row.addWidget(self.emp_save_btn)
        btn_row.addWidget(self.emp_cancel_btn)
        btn_row.addStretch()

        self.emp_form_feedback = QLabel("")
        self.emp_form_feedback.setObjectName("section_hint")
        self.emp_form_feedback.setWordWrap(True)

        layout.addWidget(self.emp_form_title)
        layout.addLayout(form_grid)
        layout.addLayout(btn_row)
        layout.addWidget(self.emp_form_feedback)
        self._emp_editing_code = None
        return card

    def _build_emp_printing_subtab(self, tab: QWidget) -> None:
        root = QHBoxLayout(tab)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        left_card = self._card_frame()
        left_card.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        left_card.setFixedWidth(280)
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.setSpacing(12)

        printer_title = QLabel("CONFIGURACION DE IMPRESORA")
        printer_title.setObjectName("label_block_title")
        left_layout.addWidget(printer_title)

        printer_lbl = QLabel("Impresora activa")
        printer_lbl.setObjectName("field_label")
        left_layout.addWidget(printer_lbl)

        printer_row = QHBoxLayout()
        printer_row.setSpacing(6)
        self.print_printer_combo = QComboBox()
        self.print_printer_combo.setObjectName("label_form_combo")
        self.print_printer_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.print_printer_combo.currentIndexChanged.connect(self._print_on_printer_changed)

        refresh_btn = QPushButton("↺")
        refresh_btn.setObjectName("print_icon_btn")
        refresh_btn.setToolTip("Recargar lista de impresoras")
        refresh_btn.setFixedSize(34, 34)
        refresh_btn.clicked.connect(self._print_refresh_printers)
        printer_row.addWidget(self.print_printer_combo, 1)
        printer_row.addWidget(refresh_btn)
        left_layout.addLayout(printer_row)

        self.print_printer_status = QLabel("— sin impresora seleccionada —")
        self.print_printer_status.setObjectName("section_hint")
        self.print_printer_status.setWordWrap(True)
        left_layout.addWidget(self.print_printer_status)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        sep1.setObjectName("print_separator")
        left_layout.addWidget(sep1)

        test_lbl = QLabel("Verificacion")
        test_lbl.setObjectName("field_label")
        left_layout.addWidget(test_lbl)

        test_btn = QPushButton("🖨  Imprimir pagina de prueba")
        test_btn.setObjectName("print_secondary_btn")
        test_btn.clicked.connect(self._print_test_page)
        left_layout.addWidget(test_btn)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setObjectName("print_separator")
        left_layout.addWidget(sep2)

        copies_lbl = QLabel("Numero de copias")
        copies_lbl.setObjectName("field_label")
        left_layout.addWidget(copies_lbl)

        copies_row = QHBoxLayout()
        copies_row.setSpacing(8)
        minus_btn = QPushButton("−")
        minus_btn.setObjectName("qty_btn")
        minus_btn.clicked.connect(lambda: self._print_change_copies(-1))
        self.print_copies_edit = QLineEdit("1")
        self.print_copies_edit.setObjectName("qty_value")
        self.print_copies_edit.setAlignment(Qt.AlignCenter)
        self.print_copies_edit.setReadOnly(True)
        plus_btn = QPushButton("+")
        plus_btn.setObjectName("qty_btn")
        plus_btn.clicked.connect(lambda: self._print_change_copies(1))
        copies_row.addWidget(minus_btn)
        copies_row.addWidget(self.print_copies_edit)
        copies_row.addWidget(plus_btn)
        copies_row.addStretch()
        left_layout.addLayout(copies_row)

        left_layout.addStretch()

        self.print_badge_btn = QPushButton("🖨   Imprimir Badge")
        self.print_badge_btn.setObjectName("btn_primary")
        self.print_badge_btn.setMinimumHeight(42)
        self.print_badge_btn.clicked.connect(self._print_employee_badge)
        left_layout.addWidget(self.print_badge_btn)

        self.print_feedback_lbl = QLabel("")
        self.print_feedback_lbl.setObjectName("section_hint")
        self.print_feedback_lbl.setWordWrap(True)
        left_layout.addWidget(self.print_feedback_lbl)

        center_col = QVBoxLayout()
        center_col.setSpacing(10)

        sel_card = self._card_frame()
        sel_layout = QVBoxLayout(sel_card)
        sel_layout.setContentsMargins(14, 14, 14, 14)
        sel_layout.setSpacing(10)

        sel_title = QLabel("SELECCION DE EMPLEADO")
        sel_title.setObjectName("label_block_title")
        sel_layout.addWidget(sel_title)

        id_row = QHBoxLayout()
        id_row.setSpacing(8)
        id_lbl = QLabel("ID / Codigo:")
        id_lbl.setObjectName("field_label")
        id_lbl.setFixedWidth(90)
        self.print_id_edit = QLineEdit()
        self.print_id_edit.setObjectName("label_form_input")
        self.print_id_edit.setPlaceholderText("Ej. 130")
        self.print_id_edit.textChanged.connect(self._print_on_id_changed)
        search_emp_btn = QPushButton("Buscar")
        search_emp_btn.setObjectName("print_secondary_btn")
        search_emp_btn.setFixedWidth(72)
        search_emp_btn.clicked.connect(self._print_search_by_id)
        id_row.addWidget(id_lbl)
        id_row.addWidget(self.print_id_edit, 1)
        id_row.addWidget(search_emp_btn)
        sel_layout.addLayout(id_row)

        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        name_lbl = QLabel("Nombre:")
        name_lbl.setObjectName("field_label")
        name_lbl.setFixedWidth(90)
        self.print_name_display = QLineEdit()
        self.print_name_display.setObjectName("label_form_input")
        self.print_name_display.setPlaceholderText("Se completa al seleccionar")
        self.print_name_display.setReadOnly(True)
        name_row.addWidget(name_lbl)
        name_row.addWidget(self.print_name_display, 1)
        sel_layout.addLayout(name_row)

        center_col.addWidget(sel_card)

        preview_card = self._card_frame()
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(14, 14, 14, 14)
        preview_layout.setSpacing(8)

        preview_title = QLabel("Vista previa del badge")
        preview_title.setObjectName("section_title")
        preview_layout.addWidget(preview_title)

        self.print_badge_preview = QFrame()
        self.print_badge_preview.setObjectName("badge_preview_frame")
        self.print_badge_preview.setMinimumHeight(190)
        badge_preview_layout = QVBoxLayout(self.print_badge_preview)
        badge_preview_layout.setContentsMargins(20, 16, 20, 16)
        badge_preview_layout.setSpacing(4)
        badge_preview_layout.setAlignment(Qt.AlignCenter)

        self.badge_company_lbl = QLabel("BlackERP")
        self.badge_company_lbl.setObjectName("badge_company")
        self.badge_company_lbl.setAlignment(Qt.AlignCenter)

        badge_sep = QFrame()
        badge_sep.setFrameShape(QFrame.HLine)
        badge_sep.setObjectName("badge_separator")

        self.badge_id_lbl = QLabel("—")
        self.badge_id_lbl.setObjectName("badge_id")
        self.badge_id_lbl.setAlignment(Qt.AlignCenter)

        self.badge_name_lbl = QLabel("Selecciona un empleado")
        self.badge_name_lbl.setObjectName("badge_name")
        self.badge_name_lbl.setAlignment(Qt.AlignCenter)

        self.badge_barcode_lbl = QLabel("|||  ||| |||| || |||||")
        self.badge_barcode_lbl.setObjectName("badge_barcode")
        self.badge_barcode_lbl.setAlignment(Qt.AlignCenter)

        self.badge_barcode_text = QLabel("")
        self.badge_barcode_text.setObjectName("badge_barcode_text")
        self.badge_barcode_text.setAlignment(Qt.AlignCenter)

        badge_preview_layout.addWidget(self.badge_company_lbl)
        badge_preview_layout.addWidget(badge_sep)
        badge_preview_layout.addStretch()
        badge_preview_layout.addWidget(self.badge_id_lbl)
        badge_preview_layout.addWidget(self.badge_name_lbl)
        badge_preview_layout.addStretch()
        badge_preview_layout.addWidget(self.badge_barcode_lbl)
        badge_preview_layout.addWidget(self.badge_barcode_text)
        preview_layout.addWidget(self.print_badge_preview, 1)
        center_col.addWidget(preview_card, 1)
        center_col.setSpacing(10)

        right_card = self._card_frame()
        right_card.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        right_card.setFixedWidth(320)
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.setSpacing(8)

        list_title = QLabel("LISTA DE EMPLEADOS")
        list_title.setObjectName("label_block_title")
        right_layout.addWidget(list_title)

        hint = QLabel("Haz clic en un empleado para seleccionarlo")
        hint.setObjectName("section_hint")
        hint.setWordWrap(True)
        right_layout.addWidget(hint)

        self.print_search_edit = QLineEdit()
        self.print_search_edit.setObjectName("label_form_input")
        self.print_search_edit.setPlaceholderText("Buscar por nombre o ID...")
        self.print_search_edit.textChanged.connect(self._print_refresh_emp_list)
        right_layout.addWidget(self.print_search_edit)

        self.print_emp_list = QListWidget()
        self.print_emp_list.setObjectName("print_emp_list")
        self.print_emp_list.itemClicked.connect(self._print_on_list_select)
        right_layout.addWidget(self.print_emp_list, 1)

        root.addWidget(left_card)
        root.addLayout(center_col, 1)
        root.addWidget(right_card)

        self._print_copies = 1
        self._print_selected_employee = None
        self._print_refresh_printers()
        self._print_refresh_emp_list()

    def _print_refresh_printers(self) -> None:
        combo = getattr(self, "print_printer_combo", None)
        if combo is None:
            return

        combo.blockSignals(True)
        combo.clear()

        printers = QPrinterInfo.availablePrinters()
        default_printer = QPrinterInfo.defaultPrinter()
        default_name = default_printer.printerName() if not default_printer.isNull() else ""

        for info in printers:
            name = info.printerName()
            display = f"{name}  ★" if name == default_name else name
            combo.addItem(display, name)

        combo.blockSignals(False)

        if combo.count() == 0:
            combo.addItem("— No se detectaron impresoras —", "")
            self._print_set_status("No hay impresoras instaladas o disponibles.", error=True)
        else:
            for i in range(combo.count()):
                if combo.itemData(i) == default_name:
                    combo.setCurrentIndex(i)
                    break
            self._print_on_printer_changed()

    def _print_on_printer_changed(self) -> None:
        combo = getattr(self, "print_printer_combo", None)
        if combo is None:
            return
        printer_name = combo.currentData()
        if not printer_name:
            self._print_set_status("Sin impresora seleccionada.", error=True)
            return

        all_printers = QPrinterInfo.availablePrinters()
        default_name = QPrinterInfo.defaultPrinter().printerName()
        info = next((p for p in all_printers if p.printerName() == printer_name), None)

        if info is None:
            self._print_set_status(f"Impresora '{printer_name}' no encontrada.", error=True)
            return

        parts = []
        if printer_name == default_name:
            parts.append("Predeterminada")
        if info.isRemote():
            parts.append("Red")
        if info.isDefault():
            parts.append("Default del sistema")
        status_text = "  ·  ".join(parts) if parts else "Lista"
        self._print_set_status(f"✓  {status_text}", error=False)

    def _print_set_status(self, text: str, error: bool = False) -> None:
        lbl = getattr(self, "print_printer_status", None)
        if lbl is None:
            return
        color = "#ff6b6b" if error else "#5c9a70"
        lbl.setStyleSheet(f"color: {color}; font-size: 11px;")
        lbl.setText(text)

    def _print_set_feedback(self, text: str, error: bool = False) -> None:
        lbl = getattr(self, "print_feedback_lbl", None)
        if lbl is None:
            return
        color = "#ff6b6b" if error else "#5c9a70"
        lbl.setStyleSheet(f"color: {color}; font-size: 11px;")
        lbl.setText(text)

    def _print_change_copies(self, delta: int) -> None:
        self._print_copies = max(1, min(10, getattr(self, "_print_copies", 1) + delta))
        edit = getattr(self, "print_copies_edit", None)
        if edit:
            edit.setText(str(self._print_copies))

    def _print_refresh_emp_list(self) -> None:
        lst = getattr(self, "print_emp_list", None)
        if lst is None:
            return

        search_edit = getattr(self, "print_search_edit", None)
        query = search_edit.text().strip().lower() if search_edit else ""

        lst.clear()
        for emp in self._employees:
            code = str(emp.get("code", "")).strip()
            name = str(emp.get("name", "")).strip()
            line = str(emp.get("line", "")).strip()

            if query and query not in name.lower() and query not in code.lower():
                continue

            item_text = f"[{code}]  {name}  ({line})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, emp)
            lst.addItem(item)

    def _print_on_list_select(self, item: QListWidgetItem) -> None:
        emp = item.data(Qt.UserRole)
        if emp:
            self._print_select_employee(emp)

    def _print_select_employee(self, emp: dict) -> None:
        self._print_selected_employee = emp
        code = str(emp.get("code", ""))
        name = str(emp.get("name", ""))

        id_edit = getattr(self, "print_id_edit", None)
        name_display = getattr(self, "print_name_display", None)
        if id_edit:
            id_edit.blockSignals(True)
            id_edit.setText(code)
            id_edit.blockSignals(False)
        if name_display:
            name_display.setText(name)

        self._print_render_preview(code, name)

    def _print_on_id_changed(self, text: str) -> None:
        code = text.strip()
        normalized = self._normalize_employee_code(code)
        emp = self._employee_index.get(normalized)
        if emp:
            self._print_selected_employee = emp
            name = str(emp.get("name", ""))
            name_display = getattr(self, "print_name_display", None)
            if name_display:
                name_display.setText(name)
            self._print_render_preview(str(emp.get("code", code)), name)
        else:
            self._print_selected_employee = None
            name_display = getattr(self, "print_name_display", None)
            if name_display:
                name_display.setText("")
            self._print_render_preview(code, "")

    def _print_search_by_id(self) -> None:
        id_edit = getattr(self, "print_id_edit", None)
        if id_edit is None:
            return
        code = id_edit.text().strip()
        normalized = self._normalize_employee_code(code)
        emp = self._employee_index.get(normalized)
        if emp:
            self._print_select_employee(emp)
            lst = getattr(self, "print_emp_list", None)
            if lst:
                target_code = str(emp.get("code", ""))
                for i in range(lst.count()):
                    item = lst.item(i)
                    item_emp = item.data(Qt.UserRole)
                    if item_emp and str(item_emp.get("code", "")) == target_code:
                        lst.setCurrentItem(item)
                        lst.scrollToItem(item)
                        break
        else:
            self._print_set_feedback(f"No se encontro empleado con ID '{code}'.", error=True)

    def _print_render_preview(self, code: str, name: str) -> None:
        id_lbl = getattr(self, "badge_id_lbl", None)
        name_lbl = getattr(self, "badge_name_lbl", None)
        barcode_lbl = getattr(self, "badge_barcode_lbl", None)
        barcode_text = getattr(self, "badge_barcode_text", None)

        if id_lbl:
            id_lbl.setText(code if code else "—")
        if name_lbl:
            name_lbl.setText(name if name else "Empleado no registrado")
        if barcode_lbl and barcode_text:
            if code:
                digits = "".join(c for c in code if c.isdigit())
                pattern = "|".join(
                    ["||" if int(d) % 2 == 0 else "|" for d in digits]
                ) if digits else "|||| ||| |||| |"
                barcode_lbl.setText(pattern)
                barcode_text.setText(code)
            else:
                barcode_lbl.setText("— — — — — —")
                barcode_text.setText("")

    def _print_test_page(self) -> None:
        combo = getattr(self, "print_printer_combo", None)
        if combo is None:
            return
        printer_name = combo.currentData()
        if not printer_name:
            self._print_set_feedback("Selecciona una impresora primero.", error=True)
            return

        printer = QPrinter(QPrinter.HighResolution)
        printer.setPrinterName(printer_name)
        printer.setPageSize(QPrinter.Letter)
        printer.setCopyCount(1)

        painter = QPainter()
        if not painter.begin(printer):
            self._print_set_feedback("No se pudo conectar con la impresora.", error=True)
            return

        rect = printer.pageRect()
        pen = QPen(QColor("#8b0000"))
        pen.setWidth(8)
        painter.setPen(pen)
        painter.drawRect(rect.adjusted(40, 40, -40, -40))

        title_font = QFont("Arial", 36, QFont.Bold)
        painter.setFont(title_font)
        painter.setPen(QColor("#1a1a1a"))
        painter.drawText(
            rect.adjusted(60, 80, -60, 0),
            Qt.AlignHCenter | Qt.AlignTop,
            "BlackERP — Pagina de Prueba",
        )

        body_font = QFont("Arial", 18)
        painter.setFont(body_font)
        painter.drawText(
            rect.adjusted(60, 200, -60, 0),
            Qt.AlignHCenter | Qt.AlignTop,
            "Impresora configurada correctamente.\n\nModulo: Produccion en Linea\nSub-modulo: Empleados Impresion",
        )

        painter.end()
        self._print_set_feedback("Pagina de prueba enviada a la impresora.", error=False)

    def _print_employee_badge(self) -> None:
        id_edit = getattr(self, "print_id_edit", None)
        code = id_edit.text().strip() if id_edit else ""
        name_display = getattr(self, "print_name_display", None)
        name = name_display.text().strip() if name_display else ""

        if not code:
            self._print_set_feedback("Ingresa o selecciona un empleado primero.", error=True)
            return

        combo = getattr(self, "print_printer_combo", None)
        printer_name = combo.currentData() if combo else ""

        printer = QPrinter(QPrinter.HighResolution)
        if printer_name:
            printer.setPrinterName(printer_name)

        copies = getattr(self, "_print_copies", 1)
        printer.setCopyCount(copies)

        dlg = QPrintDialog(printer, self)
        dlg.setWindowTitle("Imprimir Badge de Empleado")
        if dlg.exec_() != QPrintDialog.Accepted:
            return

        painter = QPainter()
        if not painter.begin(printer):
            self._print_set_feedback("Error al iniciar la impresion.", error=True)
            return

        self._print_draw_badge(painter, printer, code, name)
        painter.end()
        self._print_set_feedback(
            f"Badge de '{name or code}' enviado ({copies} copia(s)).", error=False
        )

    def _print_draw_badge(self, painter: QPainter, printer: QPrinter, code: str, name: str) -> None:
        rect = printer.pageRect()
        w = rect.width()
        h = rect.height()

        painter.fillRect(rect, QColor("#ffffff"))

        border_pen = QPen(QColor("#8b0000"))
        border_pen.setWidth(12)
        painter.setPen(border_pen)
        painter.drawRect(rect.adjusted(20, 20, -20, -20))

        header_font = QFont("Arial", 28, QFont.Bold)
        painter.setFont(header_font)
        painter.setPen(QColor("#8b0000"))
        painter.drawText(
            rect.adjusted(40, 50, -40, 0),
            Qt.AlignHCenter | Qt.AlignTop,
            "BlackERP",
        )

        sub_font = QFont("Arial", 14)
        painter.setFont(sub_font)
        painter.setPen(QColor("#555555"))
        painter.drawText(
            rect.adjusted(40, 140, -40, 0),
            Qt.AlignHCenter | Qt.AlignTop,
            "BADGE DE EMPLEADO — PRODUCCION EN LINEA",
        )

        sep_pen = QPen(QColor("#cccccc"))
        sep_pen.setWidth(3)
        painter.setPen(sep_pen)
        y_sep = h // 4
        painter.drawLine(60, y_sep, w - 60, y_sep)

        id_font = QFont("Arial", 72, QFont.Bold)
        painter.setFont(id_font)
        painter.setPen(QColor("#1a1a1a"))
        painter.drawText(
            rect.adjusted(40, y_sep + 20, -40, -int(h * 0.35)),
            Qt.AlignHCenter | Qt.AlignVCenter,
            code,
        )

        name_font = QFont("Arial", 22, QFont.Bold)
        painter.setFont(name_font)
        painter.setPen(QColor("#333333"))
        painter.drawText(
            rect.adjusted(40, int(h * 0.58), -40, -int(h * 0.18)),
            Qt.AlignHCenter | Qt.AlignVCenter,
            name if name else "—",
        )

        barcode_font = QFont("Consolas", 24, QFont.Bold)
        painter.setFont(barcode_font)
        painter.setPen(QColor("#000000"))
        digits = "".join(c for c in code if c.isdigit())
        barcode_str = " ".join(["|||" if int(d) % 2 == 0 else "||" for d in digits]) if digits else "||| || |||| |"
        painter.drawText(
            rect.adjusted(40, int(h * 0.76), -40, -int(h * 0.04)),
            Qt.AlignHCenter | Qt.AlignVCenter,
            barcode_str,
        )

        code_font = QFont("Consolas", 14)
        painter.setFont(code_font)
        painter.setPen(QColor("#444444"))
        painter.drawText(
            rect.adjusted(40, int(h * 0.88), -40, -10),
            Qt.AlignHCenter | Qt.AlignTop,
            code,
        )

    def _clear_rows(self) -> None:
        if not hasattr(self, '_rows') or not self._rows:
            self._set_scan_feedback("No hay registros para limpiar.", error=True)
            return

        self._rows.clear()
        self._pending_employee_label = None
        self._pending_description_label = None
        self._label_selected_box = None
        self._clear_label_form()
        self._set_label_feedback("No hay cajas activas de produccion. Puedes seguir consultando historial.", error=False)
        self._set_scan_feedback("Lista de cajas limpiada.", error=False)
        self._refresh_ui()

    def _set_scan_feedback(self, text: str, error: bool) -> None:
        try:
            color = PRIMARY if error else "#5c9a70"
        except NameError:
            color = "#ff6b6b" if error else "#5c9a70"
        if hasattr(self, 'scan_feedback_lbl'):
            self.scan_feedback_lbl.setStyleSheet(f"color: {color}; font-size: 11px;")
            self.scan_feedback_lbl.setText(text)

    def _resolve_employee(self, raw_code: str) -> dict | None:
        normalized = self._normalize_employee_code(raw_code)
        if not normalized:
            return None
        return self._employee_index.get(normalized)

    @staticmethod
    def _normalize_employee_code(raw_code: str) -> str:
        text = str(raw_code).strip().upper()
        digits = "".join(char for char in text if char.isdigit())
        if digits:
            return digits.lstrip("0") or "0"
        return text

    def _card_frame(self) -> QFrame:
        card = QFrame()
        card.setObjectName("production_card")
        return card

    @staticmethod
    def _normalize_box_id(raw_box: str, employee_code: str, line: str) -> str:
        token = str(raw_box).strip().upper()
        if token.count("-") >= 2:
            return token

        digits = "".join(char for char in token if char.isdigit())
        if digits:
            return f"{employee_code}-{digits[-5:].zfill(5)}-{line}"

        compact = "".join(char for char in token if char.isalnum())
        if compact:
            suffix = compact[-5:].upper().rjust(5, "0")
            return f"{employee_code}-{suffix}-{line}"

        return f"{employee_code}-00000-{line}"

    @staticmethod
    def _presentation_for_box(box_id: str) -> str:
        try:
            index = sum(ord(char) for char in box_id) % len(_PRESENTATION_ORDER)
            return _PRESENTATION_ORDER[index]
        except NameError:
            return "Jumbo"

    @staticmethod
    def _time_to_seconds(value: str) -> int:
        try:
            hour, minute, second = [int(part) for part in value.split(":", 2)]
        except ValueError:
            return 0
        return (hour * 3600) + (minute * 60) + second
    
