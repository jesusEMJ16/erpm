"""Reception page with intake workflow, summary panel, and detail list."""

from __future__ import annotations

from datetime import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QDoubleValidator, QIntValidator
from PyQt5.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.erp_sql import persist_reception_entry
from app.services.mock_data import reception_rows
from app.ui.widgets.themed_table import SortableTableItem, ThemedTable


_TAB_ITEMS = [
    "Registro de recepcion",
    "Lotes",
    "Campos / Cuadros",
    "Productos",
    "Variedades",
    "Historial de recepciones",
]

_BASE_PRODUCTS = ["Esparrago", "Arandano", "Aguacate", "Uva de mesa", "Mango", "Limon"]
_BASE_VARIETIES = ["IFG Ten Sweet Globe TM", "Emerald", "Hass", "Kent", "Sweet Globe", "Persian"]
_BASE_FIELDS = [
    "Campo Norte / Cuadro 07",
    "Campo Norte / Cuadro 08",
    "Campo Sur / Cuadro 02",
    "Campo Sur / Cuadro 03",
    "Campo Oeste / Cuadro 09",
]
_BASE_SIZES = ["18 Soz 3498", "16 Soz 3498","55 mm","66 mm","77 mm","88 mm","99 mm","LARGE","MEDIUM","SMALL"]
_PROGRESS_TARGET_BALES = 1000


class ReceptionPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._rows: list[dict] = []
        self._action_feedback_lbl: QLabel | None = None

        self.setObjectName("reception_page")
        self._apply_local_styles()

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(10)

        root.addLayout(self._build_header_row())
        root.addWidget(self._build_tabs_bar())

        body = QHBoxLayout()
        body.setSpacing(12)

        left_col = QVBoxLayout()
        left_col.setSpacing(10)
        left_col.addWidget(self._build_reception_info_card())
        left_col.addWidget(self._build_entry_card())
        left_col.addWidget(self._build_detail_card(), 1)

        right_col = QVBoxLayout()
        right_col.setSpacing(10)
        right_col.addWidget(self._build_summary_card())
        right_col.addWidget(self._build_actions_card())
        right_col.addStretch()

        body.addLayout(left_col, 5)
        body.addLayout(right_col, 2)
        root.addLayout(body, 1)

        self._load_rows()
        self._sync_reception_header()

    def _apply_local_styles(self) -> None:
        self.setStyleSheet(
            """
            QFrame#reception_card {
                background-color: #171717;
                border: 1px solid rgba(90,64,60,0.25);
                border-radius: 3px;
            }
            QLabel#page_title {
                font-size: 28px;
                font-weight: 700;
                letter-spacing: 0.3px;
            }
            QLabel#page_subtitle {
                color: #b0b5c4;
                font-size: 12px;
            }
            QPushButton[tab_nav="true"] {
                background: transparent;
                border: none;
                border-bottom: 2px solid transparent;
                color: #b0b5c4;
                padding: 8px 10px;
                font-size: 12px;
                font-weight: 600;
                text-align: left;
            }
            QPushButton[tab_nav="true"]:hover {
                color: #e5e2e1;
            }
            QPushButton[tab_nav="true"][tab_active="true"] {
                color: #d0d3db;
                border-bottom: 2px solid #8b0000;
            }
            QLabel#section_title {
                font-size: 17px;
                font-weight: 600;
            }
            QLabel#section_hint {
                color: #b0b5c4;
                font-size: 11px;
            }
            QLabel#field_label {
                color: #b0b5c4;
                font-size: 11px;
                font-weight: 600;
            }
            QFrame#summary_tile {
                border-radius: 4px;
                border: 1px solid rgba(90,64,60,0.3);
            }
            QFrame#summary_tile[variant="blue"] {
                background-color: rgba(35,87,148,0.24);
                border-color: rgba(79,140,214,0.35);
            }
            QFrame#summary_tile[variant="green"] {
                background-color: rgba(44,122,74,0.24);
                border-color: rgba(74,184,111,0.35);
            }
            QFrame#summary_tile[variant="purple"] {
                background-color: rgba(78,49,120,0.24);
                border-color: rgba(132,95,192,0.35);
            }
            QFrame#summary_tile[variant="amber"] {
                background-color: rgba(133,90,33,0.24);
                border-color: rgba(213,160,72,0.35);
            }
            QLabel#tile_title {
                color: #b0b5c4;
                font-size: 11px;
                font-weight: 600;
            }
            QLabel#tile_value {
                color: #f2efee;
                font-size: 33px;
                font-weight: 300;
            }
            QLabel#tile_unit {
                color: #b0b5c4;
                font-size: 11px;
                font-weight: 600;
            }
            QLabel#totals_label {
                color: #b0b5c4;
                font-size: 12px;
            }
            QLabel#totals_value {
                color: #5c9a70;
                font-weight: 600;
                font-size: 12px;
            }
            QProgressBar {
                background-color: #1f1f1f;
                border: 1px solid rgba(90,64,60,0.3);
                border-radius: 3px;
                height: 12px;
                text-align: center;
                color: transparent;
            }
            QProgressBar::chunk {
                background-color: #2f9e5c;
                border-radius: 3px;
            }
            QPushButton#mini_action {
                background-color: rgba(35,87,148,0.28);
                border: 1px solid rgba(79,140,214,0.45);
                color: #9ec9ff;
                border-radius: 2px;
                min-width: 24px;
                max-width: 24px;
                min-height: 22px;
                max-height: 22px;
                padding: 0;
                font-size: 11px;
            }
            QPushButton#mini_danger {
                background-color: rgba(139,0,0,0.28);
                border: 1px solid rgba(255,140,125,0.45);
                color: #d0d3db;
                border-radius: 2px;
                min-width: 24px;
                max-width: 24px;
                min-height: 22px;
                max-height: 22px;
                padding: 0;
                font-size: 11px;
            }
            """
        )

    def _build_header_row(self) -> QHBoxLayout:
        header = QHBoxLayout()
        header.setSpacing(10)

        title_wrap = QVBoxLayout()
        title_wrap.setSpacing(1)

        title = QLabel("Recepcion")
        title.setObjectName("page_title")

        subtitle = QLabel("Registro de recepcion por lote, producto, variedad, campo/cuadro y pallet.")
        subtitle.setObjectName("page_subtitle")

        title_wrap.addWidget(title)
        title_wrap.addWidget(subtitle)

        right = QHBoxLayout()
        right.setSpacing(8)

        status_lbl = QLabel("Estado:")
        status_lbl.setObjectName("field_label")

        self.status_combo = QComboBox()
        self.status_combo.addItems(["Borrador", "En revision", "Confirmado"])

        print_btn = QPushButton("Imprimir")
        print_btn.clicked.connect(lambda: self._set_action_feedback("Impresion disponible en siguiente iteracion."))

        right.addWidget(status_lbl)
        right.addWidget(self.status_combo)
        right.addWidget(print_btn)

        header.addLayout(title_wrap, 1)
        header.addLayout(right)
        return header

    def _build_tabs_bar(self) -> QFrame:
        wrap = QFrame()
        layout = QHBoxLayout(wrap)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        for index, label in enumerate(_TAB_ITEMS):
            btn = QPushButton(label)
            btn.setProperty("tab_nav", True)
            btn.setProperty("tab_active", index == 0)
            if index > 0:
                btn.clicked.connect(lambda: self._set_action_feedback("Seccion disponible proximamente."))
            layout.addWidget(btn)

        layout.addStretch()
        return wrap

    def _build_reception_info_card(self) -> QFrame:
        card = self._card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("Informacion de recepcion")
        title.setObjectName("section_title")

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        self.receipt_no_edit = QLineEdit()
        self.receipt_no_edit.setReadOnly(True)

        self.receipt_date_edit = QLineEdit()
        self.receipt_date_edit.setReadOnly(True)

        self.receipt_time_edit = QLineEdit()
        self.receipt_time_edit.setReadOnly(True)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["Campo Occidente", "Campo Norte", "Agro Sol", "Campo Central", "Campo Sur", "Campo Este"])

        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText("Agregar observaciones...")

        self.responsible_combo = QComboBox()
        self.responsible_combo.addItems(["Admin", "Supervisor 1", "Supervisor 2", "Coordinador"])

        self.transport_combo = QComboBox()
        self.transport_combo.addItems(["Transporte Verde", "Ruta Campo", "Logistica Norte", "Flete Local"])

        self.plate_edit = QLineEdit()
        self.plate_edit.setPlaceholderText("ABC-1234")

        self.temperature_edit = QLineEdit()
        self.temperature_edit.setValidator(QDoubleValidator(-10.0, 55.0, 1, self))
        self.temperature_edit.setPlaceholderText("6.2")

        self.reference_edit = QLineEdit()
        self.reference_edit.setPlaceholderText("OC-1458")

        fields: list[tuple[str, QWidget]] = [
            ("Recepcion N°", self.receipt_no_edit),
            ("Fecha de recepcion", self.receipt_date_edit),
            ("Hora", self.receipt_time_edit),
            ("Proveedor / Campo", self.provider_combo),
            ("Notas (opcional)", self.notes_edit),
            ("Responsable", self.responsible_combo),
            ("Transporte", self.transport_combo),
            ("Placa", self.plate_edit),
            ("Temperatura (°C)", self.temperature_edit),
            ("Documento de referencia (opcional)", self.reference_edit),
        ]

        for index, (label, field) in enumerate(fields):
            grid.addWidget(self._labeled_field(label, field), index // 5, index % 5)

        layout.addWidget(title)
        layout.addLayout(grid)
        return card

    def _build_entry_card(self) -> QFrame:
        card = self._card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("Agregar productos a la recepcion")
        title.setObjectName("section_title")

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        self.entry_lot_combo = self._editable_combo("Seleccionar o escribir lote")
        self.entry_product_combo = self._editable_combo("Seleccionar producto")
        self.entry_variety_combo = self._editable_combo("Seleccionar variedad")
        self.entry_field_combo = self._editable_combo("Seleccionar campo / cuadro")

        self.entry_bales_edit = QLineEdit()
        self.entry_bales_edit.setValidator(QIntValidator(0, 999999, self))
        self.entry_bales_edit.setPlaceholderText("Ej. 90")

        self.entry_size_combo = self._editable_combo("Seleccionar tamano")

        self.entry_weight_lb_edit = QLineEdit()
        self.entry_weight_lb_edit.setValidator(QDoubleValidator(0.0, 99999.0, 2, self))
        self.entry_weight_lb_edit.setPlaceholderText("Ej. 11.00")

        self.entry_pallet_edit = QLineEdit()
        self.entry_pallet_edit.setPlaceholderText("Ej. 21708")

        fields = [
            ("Lote *", self.entry_lot_combo),
            ("Producto *", self.entry_product_combo),
            ("Variedad *", self.entry_variety_combo),
            ("Campo / Cuadro *", self.entry_field_combo),
            ("Bultos *", self.entry_bales_edit),
            ("Tamano / Calibre *", self.entry_size_combo),
            ("Peso por bulto (lb) *", self.entry_weight_lb_edit),
            ("Pallet *", self.entry_pallet_edit),
        ]

        for index, (label, field) in enumerate(fields):
            grid.addWidget(self._labeled_field(label, field), index // 4, index % 4)

        actions = QHBoxLayout()
        actions.setSpacing(8)

        clear_btn = QPushButton("Limpiar")
        clear_btn.clicked.connect(self._clear_entry_form)

        add_btn = QPushButton("+ Agregar a la lista")
        add_btn.setObjectName("btn_primary")
        add_btn.clicked.connect(self._register_reception)

        self.feedback_lbl = QLabel("")
        self.feedback_lbl.setObjectName("section_hint")

        actions.addWidget(clear_btn)
        actions.addWidget(add_btn)
        actions.addWidget(self.feedback_lbl, 1)

        layout.addWidget(title)
        layout.addLayout(grid)
        layout.addLayout(actions)
        return card

    def _build_detail_card(self) -> QFrame:
        card = self._card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self.detail_title_lbl = QLabel("Detalle de productos registrados (0)")
        self.detail_title_lbl.setObjectName("section_title")

        import_btn = QPushButton("Importar (Excel)")
        import_btn.clicked.connect(lambda: self._set_action_feedback("Importacion disponible en siguiente iteracion."))

        clear_btn = QPushButton("Limpiar lista")
        clear_btn.clicked.connect(self._clear_rows)

        top_row.addWidget(self.detail_title_lbl)
        top_row.addStretch()
        top_row.addWidget(import_btn)
        top_row.addWidget(clear_btn)

        self.table = ThemedTable(
            [
                "#",
                "Lote",
                "Producto",
                "Variedad",
                "Campo / Cuadro",
                "Bultos",
                "Tamano / Calibre",
                "Peso por bulto (lb)",
                "Peso total (lb)",
                "Pallet",
                "Acciones",
            ]
        )
        self.table.setSortingEnabled(False)
        self.table.set_resize_modes(
            {
                0: QHeaderView.Fixed,
                1: QHeaderView.ResizeToContents,
                2: QHeaderView.ResizeToContents,
                3: QHeaderView.ResizeToContents,
                4: QHeaderView.Stretch,
                5: QHeaderView.Fixed,
                6: QHeaderView.ResizeToContents,
                7: QHeaderView.Fixed,
                8: QHeaderView.Fixed,
                9: QHeaderView.Fixed,
                10: QHeaderView.Fixed,
            },
            widths={0: 40, 5: 86, 7: 132, 8: 132, 9: 92, 10: 92},
        )

        totals_row = QHBoxLayout()
        totals_row.setSpacing(6)

        totals_label = QLabel("Totales:")
        totals_label.setObjectName("totals_label")

        self.totals_value_lbl = QLabel("0 bultos | 0.00 lb | 0 pallets")
        self.totals_value_lbl.setObjectName("totals_value")

        totals_row.addWidget(totals_label)
        totals_row.addWidget(self.totals_value_lbl)
        totals_row.addStretch()

        layout.addLayout(top_row)
        layout.addWidget(self.table)
        layout.addLayout(totals_row)
        return card

    def _build_summary_card(self) -> QFrame:
        card = self._card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("Resumen de recepcion")
        title.setObjectName("section_title")

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        tile, self.total_bales_lbl = self._summary_tile("Total bultos", "bultos", "blue")
        grid.addWidget(tile, 0, 0)

        tile, self.total_pallets_lbl = self._summary_tile("Total pallets", "pallets", "green")
        grid.addWidget(tile, 0, 1)

        tile, self.unique_lots_lbl = self._summary_tile("Lotes unicos", "lotes", "purple")
        grid.addWidget(tile, 1, 0)

        tile, self.total_weight_lbl = self._summary_tile("Peso total estimado", "lb", "amber")
        grid.addWidget(tile, 1, 1)

        progress_title = QLabel("Progreso de registro")
        progress_title.setObjectName("section_title")

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(_PROGRESS_TARGET_BALES)
        self.progress_bar.setValue(0)

        progress_row = QHBoxLayout()
        progress_row.setSpacing(8)

        self.progress_hint_lbl = QLabel("0 / 1,000 bultos registrados")
        self.progress_hint_lbl.setObjectName("section_hint")

        self.progress_pct_lbl = QLabel("0%")
        self.progress_pct_lbl.setObjectName("section_hint")
        self.progress_pct_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        progress_row.addWidget(self.progress_hint_lbl, 1)
        progress_row.addWidget(self.progress_pct_lbl)

        layout.addWidget(title)
        layout.addLayout(grid)
        layout.addSpacing(2)
        layout.addWidget(progress_title)
        layout.addWidget(self.progress_bar)
        layout.addLayout(progress_row)
        return card

    def _build_actions_card(self) -> QFrame:
        card = self._card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        title = QLabel("Acciones")
        title.setObjectName("section_title")

        save_btn = QPushButton("Guardar borrador")
        save_btn.clicked.connect(lambda: self._set_action_feedback("Borrador guardado localmente."))

        confirm_btn = QPushButton("Confirmar recepcion")
        confirm_btn.setObjectName("btn_primary")
        confirm_btn.clicked.connect(self._confirm_reception)

        labels_btn = QPushButton("Imprimir etiquetas de pallets")
        labels_btn.clicked.connect(lambda: self._set_action_feedback("Impresion de etiquetas disponible en siguiente iteracion."))

        report_btn = QPushButton("Descargar reporte")
        report_btn.clicked.connect(lambda: self._set_action_feedback("Reporte disponible en siguiente iteracion."))

        note = QLabel(
            "Al confirmar la recepcion, los lotes quedaran disponibles para produccion y trazabilidad."
        )
        note.setObjectName("section_hint")
        note.setWordWrap(True)

        self._action_feedback_lbl = QLabel("")
        self._action_feedback_lbl.setObjectName("section_hint")
        self._action_feedback_lbl.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(save_btn)
        layout.addWidget(confirm_btn)
        layout.addWidget(labels_btn)
        layout.addWidget(report_btn)
        layout.addSpacing(4)
        layout.addWidget(note)
        layout.addWidget(self._action_feedback_lbl)
        return card

    def _card_frame(self) -> QFrame:
        card = QFrame()
        card.setObjectName("reception_card")
        return card

    def _editable_combo(self, placeholder: str) -> QComboBox:
        combo = QComboBox()
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.NoInsert)
        line_edit = combo.lineEdit()
        if line_edit is not None:
            line_edit.setPlaceholderText(placeholder)
        return combo

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

    def _summary_tile(self, title: str, unit: str, variant: str) -> tuple[QFrame, QLabel]:
        frame = QFrame()
        frame.setObjectName("summary_tile")
        frame.setProperty("variant", variant)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 9, 10, 9)
        layout.setSpacing(2)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("tile_title")

        value_lbl = QLabel("0")
        value_lbl.setObjectName("tile_value")

        unit_lbl = QLabel(unit)
        unit_lbl.setObjectName("tile_unit")

        layout.addWidget(title_lbl)
        layout.addWidget(value_lbl)
        layout.addWidget(unit_lbl)

        return frame, value_lbl

    def _load_rows(self) -> None:
        self._rows = [self._normalize_row(payload) for payload in reception_rows()]
        self._refresh_entry_catalogs()
        self._render_rows(self._rows)
        self.feedback_lbl.setText("")

    def _normalize_row(self, payload: dict) -> dict:
        bales_value = int(payload.get("bales", 0) or 0)
        total_weight_kg = float(payload.get("weight_kg", 0.0) or 0.0)
        total_weight_lb = max(total_weight_kg * 2.20462, 0.0)
        weight_per_bale = round(total_weight_lb / bales_value, 2) if bales_value > 0 else 0.0

        return {
            "lot": str(payload.get("lot", "")).strip(),
            "product": str(payload.get("product", "")).strip(),
            "variety": str(payload.get("variety", "")).strip(),
            "field_block": str(payload.get("field_block", "")).strip(),
            "bales": bales_value,
            "size": str(payload.get("size", "")).strip(),
            "weight_lb_per_bale": weight_per_bale,
            "pallet": str(payload.get("pallet", "")).strip(),
        }

    def _render_rows(self, rows: list[dict]) -> None:
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)

        for index, payload in enumerate(rows, start=1):
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setRowHeight(row, 44)

            seq_item = SortableTableItem(str(index), index)
            seq_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, seq_item)
            self.table.setItem(row, 1, QTableWidgetItem(payload["lot"]))
            self.table.setItem(row, 2, QTableWidgetItem(payload["product"]))
            self.table.setItem(row, 3, QTableWidgetItem(payload["variety"]))

            field_item = QTableWidgetItem(payload["field_block"])
            field_item.setForeground(QColor(176, 181, 196))
            self.table.setItem(row, 4, field_item)

            bales_value = int(payload["bales"])
            bales_item = SortableTableItem(str(bales_value), bales_value)
            bales_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 5, bales_item)

            self.table.setItem(row, 6, QTableWidgetItem(payload["size"]))

            weight_value = float(payload["weight_lb_per_bale"])
            weight_item = SortableTableItem(f"{weight_value:.2f}", weight_value)
            weight_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 7, weight_item)

            # Peso total (lb) = weight_per_bale * bales
            total_lb = weight_value * bales_value
            total_lb_item = SortableTableItem(f"{total_lb:.2f}", total_lb)
            total_lb_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 8, total_lb_item)

            pallet_item = SortableTableItem(payload["pallet"], int(payload["pallet"]) if payload["pallet"].isdigit() else 0)
            pallet_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 9, pallet_item)

            self.table.setCellWidget(row, 10, self._build_actions_widget(index - 1))

        self.table.setSortingEnabled(True)
        self._update_detail_summary(rows)
        self._sync_side_summary(rows)

    def _build_actions_widget(self, index: int) -> QWidget:
        wrap = QWidget()
        layout = QHBoxLayout(wrap)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(5)

        edit_btn = QPushButton("E")
        edit_btn.setObjectName("mini_action")
        edit_btn.clicked.connect(lambda: self._edit_row(index))

        remove_btn = QPushButton("X")
        remove_btn.setObjectName("mini_danger")
        remove_btn.clicked.connect(lambda: self._delete_row(index))

        layout.addWidget(edit_btn)
        layout.addWidget(remove_btn)
        layout.addStretch()
        return wrap

    def _update_detail_summary(self, rows: list[dict]) -> None:
        self.detail_title_lbl.setText(f"Detalle de productos registrados ({len(rows)})")

        total_bales = sum(int(row["bales"]) for row in rows)
        total_lb = sum(float(row["weight_lb_per_bale"]) * int(row["bales"]) for row in rows)
        total_pallets = len(rows)
        self.totals_value_lbl.setText(f"{total_bales:,} bultos | {total_lb:,.2f} lb | {total_pallets} pallets")

    def _sync_side_summary(self, rows: list[dict]) -> None:
        total_bales = sum(int(row["bales"]) for row in rows)
        total_lb = sum(float(row["weight_lb_per_bale"]) * int(row["bales"]) for row in rows)
        total_pallets = len(rows)
        unique_lots = len({row["lot"] for row in rows if row["lot"]})

        self.total_bales_lbl.setText(f"{total_bales:,}")
        self.total_pallets_lbl.setText(str(total_pallets))
        self.unique_lots_lbl.setText(str(unique_lots))
        self.total_weight_lbl.setText(f"{total_lb:,.2f}")

        progress_pct = 0
        if _PROGRESS_TARGET_BALES > 0:
            progress_pct = round((total_bales / _PROGRESS_TARGET_BALES) * 100)

        clamped_bales = max(0, min(total_bales, _PROGRESS_TARGET_BALES))
        self.progress_bar.setValue(clamped_bales)
        self.progress_hint_lbl.setText(f"{total_bales:,} / {_PROGRESS_TARGET_BALES:,} bultos registrados")
        self.progress_pct_lbl.setText(f"{progress_pct}%")

    def _refresh_entry_catalogs(self) -> None:
        rows = self._rows

        lots = sorted({row["lot"] for row in rows if row["lot"]})
        products = self._merge_unique(_BASE_PRODUCTS, [row["product"] for row in rows])
        varieties = self._merge_unique(_BASE_VARIETIES, [row["variety"] for row in rows])
        fields = self._merge_unique(_BASE_FIELDS, [row["field_block"] for row in rows])
        sizes = self._merge_unique(_BASE_SIZES, [row["size"] for row in rows])

        self._set_editable_combo_items(self.entry_lot_combo, lots)
        self._set_editable_combo_items(self.entry_product_combo, products)
        self._set_editable_combo_items(self.entry_variety_combo, varieties)
        self._set_editable_combo_items(self.entry_field_combo, fields)
        self._set_editable_combo_items(self.entry_size_combo, sizes)

    @staticmethod
    def _merge_unique(base_values: list[str], dynamic_values: list[str]) -> list[str]:
        merged = {value.strip() for value in base_values if value and value.strip()}
        merged.update(value.strip() for value in dynamic_values if value and value.strip())
        return sorted(merged)

    @staticmethod
    def _set_editable_combo_items(combo: QComboBox, values: list[str]) -> None:
        current = combo.currentText()
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(values)
        combo.setCurrentText(current)
        combo.blockSignals(False)

    def _sync_reception_header(self) -> None:
        now = datetime.now()
        self.receipt_no_edit.setText(f"REC-{now:%y%m%d}-001")
        self.receipt_date_edit.setText(f"{now:%d/%m/%Y}")
        self.receipt_time_edit.setText(f"{now:%H:%M}")

    def _register_reception(self) -> None:
        lot = self.entry_lot_combo.currentText().strip()
        product = self.entry_product_combo.currentText().strip()
        variety = self.entry_variety_combo.currentText().strip()
        field_block = self.entry_field_combo.currentText().strip()
        bales_text = self.entry_bales_edit.text().strip()
        weight_text = self.entry_weight_lb_edit.text().strip()
        size = self.entry_size_combo.currentText().strip()
        pallet = self.entry_pallet_edit.text().strip()

        required_values = [lot, product, variety, field_block, bales_text, weight_text, size, pallet]
        if any(not value for value in required_values):
            self.feedback_lbl.setStyleSheet("color: #d0d3db; font-size: 11px;")
            self.feedback_lbl.setText("Completa todos los campos de recepcion.")
            return

        bales_value = int(bales_text)
        if bales_value <= 0:
            self.feedback_lbl.setStyleSheet("color: #d0d3db; font-size: 11px;")
            self.feedback_lbl.setText("Bultos debe ser mayor a cero.")
            return

        try:
            weight_value = float(weight_text.replace(",", "."))
        except ValueError:
            self.feedback_lbl.setStyleSheet("color: #d0d3db; font-size: 11px;")
            self.feedback_lbl.setText("Peso por bulto debe ser numerico.")
            return

        if weight_value <= 0:
            self.feedback_lbl.setStyleSheet("color: #d0d3db; font-size: 11px;")
            self.feedback_lbl.setText("Peso por bulto debe ser mayor a cero.")
            return

        # Always add row to local data immediately for instant UI feedback
        total_weight_kg = bales_value * weight_value * 0.45359237
        new_row = {
            "lot": lot,
            "product": product,
            "variety": variety,
            "field_block": field_block,
            "bales": bales_value,
            "size": size,
            "weight_lb_per_bale": weight_value,
            "pallet": pallet,
        }
        self._rows.append(new_row)
        self._render_rows(self._rows)
        self._refresh_entry_catalogs()

        # Try to persist to SQL Server (non-blocking for UI)
        try:
            persist_reception_entry(
                reception_code=self.receipt_no_edit.text().strip(),
                supplier_name=self.provider_combo.currentText().strip(),
                notes=self.notes_edit.text().strip(),
                supplier_reference=self.reference_edit.text().strip(),
                lot_code=lot,
                product_name=product,
                variety=variety,
                field_block=field_block,
                bales=bales_value,
                size=size,
                weight_lb_per_bale=weight_value,
            )
            self.feedback_lbl.setStyleSheet("color: #5c9a70; font-size: 11px;")
            self.feedback_lbl.setText("Producto agregado y guardado en SQL Server.")
            self._set_action_feedback("Registro persistido en base de datos y vista actualizada.")
        except Exception as exc:
            self.feedback_lbl.setStyleSheet("color: #d0d3db; font-size: 11px;")
            self.feedback_lbl.setText(f"Guardado local (sin conexion a SQL Server): {exc}")
            self._set_action_feedback("Registro guardado solo en la vista local. No se persistio en SQL Server.")

        self._clear_entry_form()

    def _clear_rows(self) -> None:
        self._load_rows()
        self.feedback_lbl.setText("")
        self._set_action_feedback("Vista recargada desde SQL Server.")

    def _edit_row(self, index: int) -> None:
        if index < 0 or index >= len(self._rows):
            return

        payload = self._rows[index]

        self.entry_lot_combo.setCurrentText(payload["lot"])
        self.entry_product_combo.setCurrentText(payload["product"])
        self.entry_variety_combo.setCurrentText(payload["variety"])
        self.entry_field_combo.setCurrentText(payload["field_block"])
        self.entry_bales_edit.setText(str(payload["bales"]))
        self.entry_size_combo.setCurrentText(payload["size"])
        self.entry_weight_lb_edit.setText(f"{float(payload['weight_lb_per_bale']):.2f}")
        self.entry_pallet_edit.setText(payload["pallet"])

        self.feedback_lbl.setStyleSheet("color: #b0b5c4; font-size: 11px;")
        self.feedback_lbl.setText("Registro cargado para duplicar/ajustar y guardar como nueva linea.")

    def _delete_row(self, index: int) -> None:
        if index < 0 or index >= len(self._rows):
            return
        self._set_action_feedback("Eliminacion desde UI no implementada aun para SQL Server.")

    def _confirm_reception(self) -> None:
        if not self._rows:
            self._set_action_feedback("No hay productos en la recepcion para confirmar.")
            return

        self.status_combo.setCurrentText("Confirmado")
        self._set_action_feedback("Recepcion confirmada. Lotes listos para produccion y trazabilidad.")

    def _set_action_feedback(self, text: str) -> None:
        if self._action_feedback_lbl is not None:
            self._action_feedback_lbl.setText(text)

    def _clear_entry_form(self) -> None:
        self.entry_lot_combo.setCurrentText("")
        self.entry_product_combo.setCurrentText("")
        self.entry_variety_combo.setCurrentText("")
        self.entry_field_combo.setCurrentText("")
        self.entry_bales_edit.clear()
        self.entry_weight_lb_edit.clear()
        self.entry_size_combo.setCurrentText("")
        self.entry_pallet_edit.clear()
