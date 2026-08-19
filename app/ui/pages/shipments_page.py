"""Shipments page focused on agricultural logistics operations."""

from __future__ import annotations

from datetime import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import (
    QComboBox,
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
    QTabWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.theme import ON_SEC_CONT, PRIMARY, SURFACE_HIGHEST, SURFACE_LOW, SURFACE_LOWEST
from app.services.mock_data import shipment_manifest_rows, shipment_rows
from app.services.reporting import create_manifest_report, create_remision_report
from app.ui.widgets.themed_table import SortableTableItem, ThemedTable

_MANIFEST_STATUS_ORDER = {
    "Alert": 0,
    "Draft": 1,
    "Issued": 2,
    "Signed": 3,
}

_REPORT_FIELD_DEFS: list[tuple[str, str, str]] = [
    ("manifest_no", "Embarque N°", "E0001"),
    ("invoice_no", "N° Factura", "0001"),
    ("issue_date", "Fecha Embarque", "dd/mm/yyyy"),
    ("departure_time", "Hora Salida", "hh:mm:ss"),
    ("carrier", "Transportista", ""),
    ("driver", "Chofer", ""),
    ("vehicle", "Unidad / Placas", ""),
    ("truck_plate", "Placas Tractor", ""),
    ("ff_registration", "F.F. Registration", ""),
    ("shipper", "Embarcador", ""),
    ("shipper_address", "Dir. Embarcador", ""),
    ("shipper_city", "Ciudad Embarcador", ""),
    ("shipper_tax", "RFC Embarcador", ""),
    ("distributor", "Distribuidor", ""),
    ("consignee", "Consignee", ""),
    ("consignee_address", "Domic. Consignee", ""),
    ("consignee_city", "Lugar Consignee", ""),
    ("consignee_tax", "RFC Consignee", ""),
    ("driver_phone", "Telefono Chofer", ""),
    ("temperature", "Temperatura", ""),
    ("trailer_no", "N° Caja", ""),
    ("trailer_plate", "Placas Caja", ""),
    ("thermograph", "Termografo", ""),
    ("seal_no", "Sellos", ""),
    ("mex_customs_agent", "A.Ad. Mexico", ""),
    ("mex_customs_tax", "RFC A.Ad. MX", ""),
    ("mex_customs_address", "Domicilio A.Ad. MX", ""),
    ("mex_customs_city", "Lugar A.Ad. MX", ""),
    ("mex_customs_zip", "CP A.Ad. MX", ""),
    ("us_customs_agent", "A.Ad. U.S.", ""),
    ("us_customs_tax", "RFC A.Ad. U.S.", ""),
    ("us_customs_address", "Domicilio A.Ad. U.S.", ""),
    ("us_customs_city", "Lugar A.Ad. U.S.", ""),
    ("us_customs_zip", "CP A.Ad. U.S.", ""),
    ("booking", "Booking", ""),
    ("po", "PO", ""),
    ("crop", "Cultivo", ""),
    ("lot", "Lote", ""),
    ("route", "Ruta", "Origen -> Destino"),
    ("departure", "Salida Carga", ""),
    ("eta", "ETA", ""),
    ("product_name", "Nombre Producto", ""),
    ("product_code", "Producto", ""),
    ("description", "Descripcion", ""),
    ("size", "Tamaño", ""),
    ("variety", "Variedad", ""),
    ("lote_code", "Lote Tabla", ""),
    ("line_rows", "Filas", "20"),
    ("bultos_per_row", "Bultos/Fila", "0"),
    ("total_kg", "Kg Embarcados", "0"),
    ("pallet_start", "Pallet Inicial", "0"),
    ("product_quantity", "Cantidad", "20"),
    ("transport_mode", "Medio", ""),
    ("freight_advance", "Anticipo Flete", ""),
    ("scac", "SCAC", ""),
]

_REPORT_FIELD_MAP: dict[str, tuple[str, str]] = {key: (label, placeholder) for key, label, placeholder in _REPORT_FIELD_DEFS}

_REPORT_SECTIONS: list[tuple[str, list[str], bool]] = [
    (
        "Documento y Transporte",
        [
            "manifest_no",
            "invoice_no",
            "issue_date",
            "departure_time",
            "carrier",
            "driver",
            "driver_phone",
            "transport_mode",
            "vehicle",
            "truck_plate",
            "trailer_no",
            "trailer_plate",
            "temperature",
            "thermograph",
            "seal_no",
            "freight_advance",
            "scac",
        ],
        True,
    ),
    (
        "Origen, Destino y Referencias",
        [
            "ff_registration",
            "shipper",
            "shipper_address",
            "shipper_city",
            "shipper_tax",
            "distributor",
            "consignee",
            "consignee_address",
            "consignee_city",
            "consignee_tax",
            "route",
            "departure",
            "eta",
            "booking",
            "po",
            "crop",
            "lot",
        ],
        True,
    ),
    (
        "Aduanas",
        [
            "mex_customs_agent",
            "mex_customs_tax",
            "mex_customs_address",
            "mex_customs_city",
            "mex_customs_zip",
            "us_customs_agent",
            "us_customs_tax",
            "us_customs_address",
            "us_customs_city",
            "us_customs_zip",
        ],
        False,
    ),
    (
        "Detalle de Carga",
        [
            "product_name",
            "product_code",
            "description",
            "size",
            "variety",
            "lote_code",
            "line_rows",
            "bultos_per_row",
            "total_kg",
            "pallet_start",
            "product_quantity",
        ],
        False,
    ),
]

_NUMERIC_REPORT_KEYS = {
    "line_rows",
    "bultos_per_row",
    "total_kg",
    "pallet_start",
    "product_quantity",
    "invoice_no",
}

_WIDE_REPORT_KEYS = {
    "shipper_address",
    "consignee_address",
    "mex_customs_address",
    "us_customs_address",
    "route",
    "description",
    "product_name",
}

_DUPLICATE_SKIP_KEYS = {
    "manifest_no",
    "invoice_no",
    "issue_date",
    "departure_time",
}

_CARGO_REPORT_KEYS = {
    "product_name",
    "product_code",
    "description",
    "size",
    "variety",
    "lote_code",
    "line_rows",
    "bultos_per_row",
    "total_kg",
    "pallet_start",
    "product_quantity",
}

_CARGO_TABLE_COLUMNS = [
    "No.",
    "Pos.",
    "Bultos",
    "Producto",
    "DESCRIPCION",
    "TAMANO",
    "LOTE",
    "VARIEDAD",
    "PALLET",
]


class ShipmentsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._rows: list[dict] = []
        self._shipment_map: dict[str, dict] = {}
        self._manifest_rows: list[dict] = []
        self._report_field_edits: dict[str, QLineEdit] = {}
        self._report_section_toggles: list[QPushButton] = []
        self._manifest_fields_dialog: QDialog | None = None
        self._report_dialog_feedback_lbl: QLabel | None = None
        self._report_dialog_manifest_lbl: QLabel | None = None
        self._report_copy_source_combo: QComboBox | None = None
        self._report_cargo_sync_lbl: QLabel | None = None
        self._report_cargo_table: ThemedTable | None = None
        self._report_cargo_sync_text = "Sincronizado desde Operations: pendiente."
        self._report_cargo_sync_tone = "neutral"
        self.manifest_edit_fields_btn: QPushButton | None = None
        self.manifest_pdf_status_lbl: QLabel | None = None
        self._operations_scan_rows: list[dict] = []
        self._operations_activity_log: list[str] = []
        self._operations_pallet_codes: set[str] = set()
        self.operations_shipment_combo: QComboBox | None = None
        self.operations_scan_edit: QLineEdit | None = None
        self.operations_scan_feedback_lbl: QLabel | None = None
        self.operations_count_lbl: QLabel | None = None
        self.operations_summary_lbl: QLabel | None = None
        self.operations_checklist_lbl: QLabel | None = None
        self.operations_activity_lbl: QLabel | None = None
        self.operations_selected_lbl: QLabel | None = None
        self.operations_close_btn: QPushButton | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(8)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("shipments_tabs")
        self.tabs.setStyleSheet(
            f"""
            QTabWidget::pane {{
                border: 1px solid rgba(90,64,60,0.2);
                background-color: {SURFACE_LOW};
                top: -1px;
            }}
            QTabBar::tab {{
                background-color: {SURFACE_HIGHEST};
                color: {ON_SEC_CONT};
                border: 1px solid rgba(90,64,60,0.28);
                padding: 8px 14px;
                min-width: 120px;
            }}
            QTabBar::tab:selected {{
                color: {PRIMARY};
                border-bottom: 2px solid {PRIMARY};
            }}
            QTabBar::tab:hover {{
                color: {PRIMARY};
            }}
            """
        )
        root.addWidget(self.tabs, 1)

        self._build_embarques_tab()
        self._build_operations_tab()

        # Start in Embarques with Embarques as the left tab.
        if self.tabs.count() > 1:
            self.tabs.setCurrentIndex(0)

        self._load_rows()
        self._load_embarque_rows()

    def _build_operations_tab(self) -> None:
        tab = QWidget()
        root = QVBoxLayout(tab)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("Operaciones de Embarque")
        title.setStyleSheet("font-size: 20px; font-weight: 600; letter-spacing: 0.5px;")

        subtitle = QLabel("Control y validacion de pallets antes de salida")
        subtitle.setStyleSheet("color: #b0b5c4; font-size: 11px;")

        root.addWidget(title)
        root.addWidget(subtitle)

        body = QHBoxLayout()
        body.setSpacing(12)

        main_card = QFrame()
        main_card.setProperty("class", "card")
        main_layout = QVBoxLayout(main_card)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        shipment_row = QHBoxLayout()
        shipment_row.setSpacing(8)

        shipment_lbl = QLabel("Shipment Operativo")
        shipment_lbl.setStyleSheet(f"color: {ON_SEC_CONT}; font-size: 11px;")

        self.operations_shipment_combo = QComboBox()
        self.operations_shipment_combo.setMinimumWidth(420)
        self.operations_shipment_combo.currentIndexChanged.connect(self._on_operations_shipment_changed)

        shipment_row.addWidget(shipment_lbl)
        shipment_row.addWidget(self.operations_shipment_combo, 1)
        main_layout.addLayout(shipment_row)

        scan_box = QFrame()
        scan_box.setObjectName("operations_scan_box")
        scan_box.setStyleSheet(
            """
            QFrame#operations_scan_box {
                background-color: rgba(0,0,0,0.18);
                border: 1px solid rgba(90,64,60,0.35);
                border-radius: 3px;
            }
            QLabel#barcode_hint {
                color: #e5e2e1;
                font-family: Consolas;
                font-size: 14px;
                letter-spacing: 1.2px;
            }
            """
        )

        scan_layout = QHBoxLayout(scan_box)
        scan_layout.setContentsMargins(10, 8, 10, 8)
        scan_layout.setSpacing(8)

        barcode_hint = QLabel("||||||||||||||||||||||||")
        barcode_hint.setObjectName("barcode_hint")

        self.operations_scan_edit = QLineEdit()
        self.operations_scan_edit.setPlaceholderText("Escanear pallet...")
        self.operations_scan_edit.returnPressed.connect(self._process_pallet_scan)

        scan_btn = QPushButton("Escanear")
        scan_btn.clicked.connect(self._process_pallet_scan)

        scan_layout.addWidget(barcode_hint)
        scan_layout.addWidget(self.operations_scan_edit, 1)
        scan_layout.addWidget(scan_btn)
        main_layout.addWidget(scan_box)

        self.operations_scan_feedback_lbl = QLabel("Ultimo pallet escaneado: -")
        self.operations_scan_feedback_lbl.setStyleSheet(
            """
            QLabel {
                background-color: rgba(44,122,74,0.25);
                border: 1px solid rgba(74,184,111,0.35);
                border-radius: 3px;
                color: #d8ffe4;
                padding: 6px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            """
        )
        main_layout.addWidget(self.operations_scan_feedback_lbl)

        table_header = QHBoxLayout()
        table_header.setSpacing(10)

        table_title = QLabel("Secuencia de pallets escaneados")
        table_title.setStyleSheet("font-size: 14px; font-weight: 600;")

        self.operations_count_lbl = QLabel("0 registros")
        self.operations_count_lbl.setStyleSheet(f"color: {ON_SEC_CONT}; font-size: 11px;")

        self.operations_selected_lbl = QLabel("Posicion seleccionada: -")
        self.operations_selected_lbl.setStyleSheet(f"color: {ON_SEC_CONT}; font-size: 11px;")

        table_header.addWidget(table_title)
        table_header.addWidget(self.operations_count_lbl)
        table_header.addStretch(1)
        table_header.addWidget(self.operations_selected_lbl)
        main_layout.addLayout(table_header)

        self.operations_table = ThemedTable(_CARGO_TABLE_COLUMNS)
        self._configure_cargo_table_columns(self.operations_table, compact=False)
        self.operations_table.itemSelectionChanged.connect(self._on_operations_selection_changed)
        main_layout.addWidget(self.operations_table, 1)

        actions = QHBoxLayout()
        actions.setSpacing(8)

        clear_btn = QPushButton("Limpiar Lista")
        clear_btn.setObjectName("btn_primary")
        clear_btn.clicked.connect(self._clear_operations_scan_list)

        close_btn = QPushButton("Cerrar Embarque")
        close_btn.clicked.connect(self._close_operations_shipment)
        self.operations_close_btn = close_btn

        actions.addWidget(clear_btn)
        actions.addWidget(close_btn)
        actions.addStretch(1)
        main_layout.addLayout(actions)

        side_col = QVBoxLayout()
        side_col.setSpacing(10)

        summary_card = QFrame()
        summary_card.setProperty("class", "card")
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(12, 12, 12, 12)
        summary_layout.setSpacing(8)
        summary_layout.addWidget(QLabel("Summary"))

        self.operations_summary_lbl = QLabel("Total Pallets: 0\nTotal Cajas: 0")
        self.operations_summary_lbl.setStyleSheet("font-size: 12px; line-height: 1.4;")
        summary_layout.addWidget(self.operations_summary_lbl)
        side_col.addWidget(summary_card)

        checklist_card = QFrame()
        checklist_card.setProperty("class", "card")
        checklist_layout = QVBoxLayout(checklist_card)
        checklist_layout.setContentsMargins(12, 12, 12, 12)
        checklist_layout.setSpacing(8)
        checklist_layout.addWidget(QLabel("Validation Checklist"))

        self.operations_checklist_lbl = QLabel("[ ] Pallets completos\n[ ] Sin duplicados\n[ ] Etiquetas correctas")
        self.operations_checklist_lbl.setStyleSheet("font-size: 12px; line-height: 1.4;")
        checklist_layout.addWidget(self.operations_checklist_lbl)
        side_col.addWidget(checklist_card)

        activity_card = QFrame()
        activity_card.setProperty("class", "card")
        activity_layout = QVBoxLayout(activity_card)
        activity_layout.setContentsMargins(12, 12, 12, 12)
        activity_layout.setSpacing(8)
        activity_layout.addWidget(QLabel("Activity Log"))

        self.operations_activity_lbl = QLabel("Sin actividad reciente.")
        self.operations_activity_lbl.setWordWrap(True)
        self.operations_activity_lbl.setStyleSheet("font-size: 11px; line-height: 1.35;")
        activity_layout.addWidget(self.operations_activity_lbl)
        side_col.addWidget(activity_card, 1)

        body.addWidget(main_card, 4)
        body.addLayout(side_col, 2)
        root.addLayout(body, 1)

        self.tabs.addTab(tab, "Operations")

    def _set_combo_to_shipment(self, combo: QComboBox, shipment_id: str) -> bool:
        target = str(shipment_id or "").strip()
        if not target:
            return False

        for index in range(combo.count()):
            if str(combo.itemData(index) or "").strip() == target:
                combo.setCurrentIndex(index)
                return True
        return False

    def _refresh_manifest_pdf_status(self) -> None:
        if self.manifest_pdf_status_lbl is None:
            return

        shipment_id = str(self.manifest_shipment_combo.currentData() or "").strip()
        if not shipment_id:
            self.manifest_pdf_status_lbl.setStyleSheet(f"color: {ON_SEC_CONT}; font-size: 11px;")
            self.manifest_pdf_status_lbl.setText("Selecciona un shipment para habilitar Datos PDF del Embarque.")
            if self.manifest_edit_fields_btn is not None:
                self.manifest_edit_fields_btn.setEnabled(False)
            return

        related_manifest = next(
            (row for row in self._manifest_rows if str(row.get("shipment_id", "")).strip() == shipment_id),
            None,
        )

        if related_manifest is None:
            self.manifest_pdf_status_lbl.setStyleSheet("color: #ffe8c9; font-size: 11px;")
            self.manifest_pdf_status_lbl.setText(
                f"Aviso: no hay embarque registrado para {shipment_id}. Primero presiona Registrar Embarque."
            )
            if self.manifest_edit_fields_btn is not None:
                self.manifest_edit_fields_btn.setEnabled(False)
            return

        manifest_id = str(related_manifest.get("manifest_id", "")).strip() or "-"
        self.manifest_pdf_status_lbl.setStyleSheet("color: #d8ffe4; font-size: 11px;")
        self.manifest_pdf_status_lbl.setText(
            f"Datos PDF disponibles para {shipment_id} (Embarque {manifest_id})."
        )
        if self.manifest_edit_fields_btn is not None:
            self.manifest_edit_fields_btn.setEnabled(True)

    def _select_manifest_row_by_shipment(self, shipment_id: str) -> bool:
        target = str(shipment_id or "").strip()
        if not target or not hasattr(self, "manifest_table"):
            return False

        for row in range(self.manifest_table.rowCount()):
            shipment_item = self.manifest_table.item(row, 1)
            if shipment_item is None:
                continue
            if shipment_item.text().strip() == target:
                self.manifest_table.selectRow(row)
                return True

        self.manifest_table.clearSelection()
        return False

    def _on_manifest_shipment_changed(self, _index: int) -> None:
        shipment_id = str(self.manifest_shipment_combo.currentData() or "").strip()
        if not shipment_id or self.operations_shipment_combo is None:
            return

        current_ops = str(self.operations_shipment_combo.currentData() or "").strip()
        if current_ops != shipment_id:
            self.operations_shipment_combo.blockSignals(True)
            self._set_combo_to_shipment(self.operations_shipment_combo, shipment_id)
            self.operations_shipment_combo.blockSignals(False)

        self._select_manifest_row_by_shipment(shipment_id)
        self._refresh_manifest_pdf_status()

        self._apply_filter()

    def _on_operations_shipment_changed(self, _index: int) -> None:
        if self.operations_shipment_combo is None:
            return

        shipment_id = str(self.operations_shipment_combo.currentData() or "").strip()
        if not shipment_id:
            return

        current_manifest = str(self.manifest_shipment_combo.currentData() or "").strip()
        if current_manifest != shipment_id:
            self.manifest_shipment_combo.blockSignals(True)
            self._set_combo_to_shipment(self.manifest_shipment_combo, shipment_id)
            self.manifest_shipment_combo.blockSignals(False)

        self._select_manifest_row_by_shipment(shipment_id)

        self._set_operations_scan_feedback(
            f"Shipment operativo activo: {shipment_id}",
            tone="neutral",
        )
        self._refresh_manifest_pdf_status()
        self._apply_filter()

    @staticmethod
    def _format_operations_time(value: str) -> str:
        raw = str(value or "").strip()
        if not raw:
            return datetime.now().strftime("%I:%M %p")

        for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p"):
            try:
                return datetime.strptime(raw, fmt).strftime("%I:%M %p")
            except ValueError:
                continue
        return raw

    def _configure_cargo_table_columns(self, table: ThemedTable, compact: bool) -> None:
        table.set_resize_modes(
            {
                0: QHeaderView.ResizeToContents,
                1: QHeaderView.ResizeToContents,
                2: QHeaderView.ResizeToContents,
                3: QHeaderView.ResizeToContents,
                4: QHeaderView.Stretch,
                5: QHeaderView.ResizeToContents,
                6: QHeaderView.ResizeToContents,
                7: QHeaderView.Stretch,
                8: QHeaderView.ResizeToContents,
            },
            widths={2: 78, 3: 104, 6: 132, 8: 142},
        )
        table.horizontalHeader().setStretchLastSection(False)
        table.horizontalHeader().setMinimumSectionSize(44)
        table.verticalHeader().setDefaultSectionSize(34 if compact else 38)
        table.setWordWrap(False)
        table.setSortingEnabled(False)
        table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        table.setMinimumHeight(300 if compact else 280)

    def _seed_operations_scan_rows(self) -> None:
        self._operations_scan_rows.clear()
        self._operations_activity_log.clear()
        self._operations_pallet_codes.clear()

        variety_by_crop = {
            "Blueberry": "Emerald",
            "Avocado": "Hass",
            "Table Grape": "IFG Ten Sweet Globe TM",
            "Mango": "Kent",
            "Lime": "Persian",
        }

        for idx, shipment in enumerate(self._rows, start=1):
            related_manifest = next(
                (row for row in self._manifest_rows if row.get("shipment_id") == shipment.get("id")),
                None,
            )

            report = related_manifest.get("report_data") if isinstance(related_manifest, dict) else None
            if not isinstance(report, dict):
                report = {}

            bultos = 48
            bultos_text = str(report.get("bultos_per_row", "")).strip()
            if bultos_text.isdigit() and int(bultos_text) > 0:
                bultos = int(bultos_text)

            status = "VERIFICADO"
            if shipment.get("status") == "Alert" or (related_manifest and related_manifest.get("status") == "Alert"):
                status = "ERROR"
                bultos = max(40, bultos - 2)

            lot_default = str(shipment.get("lot", "")).strip()
            lot_code = str(report.get("lote_code", "")).strip() or lot_default

            scanned_at = self._format_operations_time(
                str(report.get("departure_time") or (related_manifest or {}).get("issued_at") or shipment.get("departure", ""))
            )

            pallet_code = f"PLT-{987650 + idx:06d}"
            self._operations_pallet_codes.add(pallet_code)

            row_payload = {
                "no": idx,
                "pos": f"{idx:03d}",
                "hora": scanned_at,
                "bultos": bultos,
                "producto": str(report.get("product_code", "")).strip() or "00147",
                "descripcion": str(report.get("description", "")).strip() or "18 SO2 GEN 3498",
                "tamano": str(report.get("size", "")).strip() or "77",
                "lote": lot_code,
                "variedad": str(report.get("variety", "")).strip()
                or variety_by_crop.get(str(shipment.get("crop", "")), "-"),
                "pallet": pallet_code,
                "estado": status,
                "shipment_id": shipment.get("id", ""),
            }
            self._operations_scan_rows.append(row_payload)

            event_status = "verificado" if status == "VERIFICADO" else "error"
            self._operations_activity_log.insert(0, f"{scanned_at} - Pallet {pallet_code} escaneado ({event_status})")

        self._operations_activity_log = self._operations_activity_log[:10]
        self._set_operations_scan_feedback("Ultimo pallet escaneado: base inicial cargada.", tone="neutral")

    def _set_operations_scan_feedback(self, message: str, tone: str = "neutral") -> None:
        if self.operations_scan_feedback_lbl is None:
            return

        if tone == "error":
            style = (
                "background-color: rgba(189,65,65,0.25);"
                "border: 1px solid rgba(255,180,168,0.45);"
                "color: #d0d3db;"
            )
        elif tone == "success":
            style = (
                "background-color: rgba(44,122,74,0.25);"
                "border: 1px solid rgba(74,184,111,0.35);"
                "color: #d8ffe4;"
            )
        else:
            style = (
                "background-color: rgba(35,87,148,0.2);"
                "border: 1px solid rgba(79,140,214,0.35);"
                "color: #cfe3ff;"
            )

        self.operations_scan_feedback_lbl.setStyleSheet(
            f"QLabel {{ {style} border-radius: 3px; padding: 6px 10px; font-size: 11px; font-weight: 600; }}"
        )
        self.operations_scan_feedback_lbl.setText(message)

    @staticmethod
    def _is_accepted_operations_row(row: dict) -> bool:
        return str(row.get("estado", "")).upper() == "VERIFICADO"

    def _operations_rows_for_shipment(self, shipment_id: str) -> list[dict]:
        target = str(shipment_id or "").strip()
        if not target:
            return []

        return [
            row
            for row in self._operations_scan_rows
            if str(row.get("shipment_id", "")).strip() == target and self._is_accepted_operations_row(row)
        ]

    def _active_operations_shipment_id(self) -> str:
        if self.operations_shipment_combo is not None:
            shipment_id = str(self.operations_shipment_combo.currentData() or "").strip()
            if shipment_id:
                return shipment_id

        row = self.operations_table.currentRow() if hasattr(self, "operations_table") else -1
        if row >= 0 and hasattr(self, "operations_table"):
            no_item = self.operations_table.item(row, 0)
            if no_item is not None:
                shipment_id = str(no_item.data(Qt.UserRole) or "").strip()
                if shipment_id:
                    return shipment_id

        if hasattr(self, "manifest_shipment_combo"):
            shipment_id = str(self.manifest_shipment_combo.currentData() or "").strip()
            if shipment_id:
                return shipment_id

        if self._operations_scan_rows:
            return str(self._operations_scan_rows[-1].get("shipment_id", "")).strip()

        return ""

    def _collect_operations_cargo_snapshot(self, shipment_id: str) -> dict | None:
        rows = self._operations_rows_for_shipment(shipment_id)
        if not rows:
            return None

        verified_rows = list(rows)
        source_rows = rows
        latest = source_rows[-1]
        first = source_rows[0]

        bultos_values: list[int] = []
        for row in source_rows:
            try:
                bultos_values.append(max(0, int(row.get("bultos", 0))))
            except (TypeError, ValueError):
                continue

        unique_pallets = len(
            {str(row.get("pallet", "")).strip() for row in source_rows if str(row.get("pallet", "")).strip()}
        )

        first_position = str(first.get("pos", "")).strip() or str(first.get("no", "")).strip()
        bultos_per_row = bultos_values[-1] if bultos_values else 0
        total_bultos = sum(bultos_values)

        payload = {
            "departure_time": str(latest.get("hora", "")).strip(),
            "product_code": str(latest.get("producto", "")).strip(),
            "description": str(latest.get("descripcion", "")).strip(),
            "size": str(latest.get("tamano", "")).strip(),
            "variety": str(latest.get("variedad", "")).strip(),
            "lote_code": str(latest.get("lote", "")).strip(),
            "line_rows": str(len(source_rows)),
            "bultos_per_row": str(bultos_per_row),
            "total_kg": str(total_bultos),
            "pallet_start": str(first_position),
            "product_quantity": str(unique_pallets or len(source_rows)),
        }

        return {
            "rows": rows,
            "verified_rows": verified_rows,
            "payload": payload,
        }

    def _sync_manifest_cargo_from_operations(self, manifest: dict, shipment: dict) -> bool:
        shipment_id = str(manifest.get("shipment_id", "")).strip()
        if not shipment_id:
            self._set_report_cargo_sync_status(
                "Sincronizado desde Operations: embarque sin shipment asociado.",
                tone="warning",
            )
            self._render_report_cargo_table([])
            return False

        snapshot = self._collect_operations_cargo_snapshot(shipment_id)
        if snapshot is None:
            self._set_report_cargo_sync_status(
                f"Sincronizado desde Operations: sin registros para {shipment_id}.",
                tone="warning",
            )
            self._render_report_cargo_table([])
            return False

        report_data = manifest.get("report_data")
        if not isinstance(report_data, dict):
            report_data = self._default_report_payload_for_manifest(manifest, shipment)

        cargo_payload = dict(snapshot.get("payload") or {})
        product_name = str(shipment.get("crop", "")).strip()
        if product_name:
            cargo_payload["product_name"] = product_name

        cargo_keys = {
            "product_name",
            "product_code",
            "description",
            "size",
            "variety",
            "lote_code",
            "line_rows",
            "bultos_per_row",
            "total_kg",
            "pallet_start",
            "product_quantity",
            "departure_time",
        }
        for key in cargo_keys:
            value = str(cargo_payload.get(key, "")).strip()
            if value:
                report_data[key] = value

        manifest["report_data"] = report_data

        total_rows = len(snapshot.get("rows") or [])
        verified_rows = len(snapshot.get("verified_rows") or [])
        self._render_report_cargo_table(snapshot.get("rows") or [])
        sync_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self._set_report_cargo_sync_status(
            f"Sincronizado desde Operations: {sync_time} | Shipment {shipment_id} | Registros {total_rows} | Verificados {verified_rows}",
            tone="success",
        )
        return True

    def _set_report_cargo_sync_status(self, message: str, tone: str = "neutral") -> None:
        self._report_cargo_sync_text = message
        self._report_cargo_sync_tone = tone

        if self._report_cargo_sync_lbl is None:
            return

        if tone == "success":
            style = "background-color: rgba(44,122,74,0.2); border: 1px solid rgba(74,184,111,0.35); color: #d8ffe4;"
        elif tone == "warning":
            style = "background-color: rgba(163,119,48,0.2); border: 1px solid rgba(209,164,95,0.4); color: #ffe8c9;"
        elif tone == "error":
            style = "background-color: rgba(189,65,65,0.2); border: 1px solid rgba(255,180,168,0.45); color: #ffd8d3;"
        else:
            style = "background-color: rgba(35,87,148,0.2); border: 1px solid rgba(79,140,214,0.35); color: #cfe3ff;"

        self._report_cargo_sync_lbl.setStyleSheet(
            f"QLabel {{ {style} border-radius: 3px; padding: 6px 10px; font-size: 11px; font-weight: 600; }}"
        )
        self._report_cargo_sync_lbl.setText(message)

    def _render_report_cargo_table(self, rows: list[dict]) -> None:
        if self._report_cargo_table is None:
            return

        self._report_cargo_table.setSortingEnabled(False)
        self._report_cargo_table.setRowCount(0)

        for payload in rows:
            row = self._report_cargo_table.rowCount()
            self._report_cargo_table.insertRow(row)
            self._report_cargo_table.setRowHeight(row, 34)

            values = [
                str(payload.get("no", row + 1)),
                str(payload.get("pos", "")),
                str(payload.get("bultos", "")),
                str(payload.get("producto", "")),
                str(payload.get("descripcion", "")),
                str(payload.get("tamano", "")),
                str(payload.get("lote", "")),
                str(payload.get("variedad", "")),
                str(payload.get("pallet", "")),
            ]

            for col, text in enumerate(values):
                item = QTableWidgetItem(text)
                if col in {0, 1, 2}:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self._report_cargo_table.setItem(row, col, item)

        self._report_cargo_table.setSortingEnabled(False)

    def _process_pallet_scan(self) -> None:
        if self.operations_scan_edit is None:
            return

        pallet_code = self.operations_scan_edit.text().strip().upper()
        if not pallet_code:
            self._set_operations_scan_feedback("Ingresa o escanea un codigo de pallet.", tone="error")
            return

        self.operations_scan_edit.clear()
        scanned_at = datetime.now().strftime("%I:%M %p")
        duplicate = pallet_code in self._operations_pallet_codes

        active_shipment_id = self._active_operations_shipment_id()
        scoped_template = None
        if active_shipment_id:
            scoped_rows = self._operations_rows_for_shipment(active_shipment_id)
            if scoped_rows:
                scoped_template = scoped_rows[-1]

        template = self._operations_scan_rows[-1] if self._operations_scan_rows else {
            "bultos": 48,
            "producto": "00147",
            "descripcion": "18 SO2 GEN 3498",
            "tamano": "77",
            "lote": "9011",
            "variedad": "IFG Ten Sweet Globe TM",
            "shipment_id": "",
        }
        if scoped_template is not None:
            template = scoped_template

        if not active_shipment_id:
            active_shipment_id = str(template.get("shipment_id", "")).strip()

        if active_shipment_id:
            shipment = self._shipment_map.get(active_shipment_id, {})
            default_lot = str(shipment.get("lot", "")).strip()
            default_variety = str(shipment.get("crop", "")).strip()
            if str(template.get("lote", "")).strip() in {"", "9011"} and default_lot:
                template = dict(template)
                template["lote"] = default_lot
            if str(template.get("variedad", "")).strip() in {"", "IFG Ten Sweet Globe TM"} and default_variety:
                if not isinstance(template, dict):
                    template = dict(template)
                template["variedad"] = default_variety

        if duplicate:
            self._set_operations_scan_feedback(
                f"Ultimo Pallet Escaneado: {pallet_code} (Duplicado rechazado, no registrado)",
                tone="error",
            )
            self._operations_activity_log.insert(0, f"{scanned_at} - Pallet {pallet_code} rechazado (duplicado)")
            self._operations_activity_log = self._operations_activity_log[:10]
            return

        row_no = len(self._operations_rows_for_shipment(active_shipment_id)) + 1
        self._operations_pallet_codes.add(pallet_code)

        payload = {
            "no": row_no,
            "pos": f"{row_no:03d}",
            "hora": scanned_at,
            "bultos": int(template.get("bultos", 48)),
            "producto": str(template.get("producto", "00147")),
            "descripcion": str(template.get("descripcion", "18 SO2 GEN 3498")),
            "tamano": str(template.get("tamano", "77")),
            "lote": str(template.get("lote", "9011")),
            "variedad": str(template.get("variedad", "IFG Ten Sweet Globe TM")),
            "pallet": pallet_code,
            "estado": "VERIFICADO",
            "shipment_id": active_shipment_id,
        }
        self._operations_scan_rows.append(payload)

        self._set_operations_scan_feedback(
            f"Ultimo Pallet Escaneado: {pallet_code} (Verificacion exitosa)",
            tone="success",
        )
        self._operations_activity_log.insert(0, f"{scanned_at} - Pallet {pallet_code} escaneado (verificado)")

        self._operations_activity_log = self._operations_activity_log[:10]
        self._apply_filter()
        if self.operations_table.rowCount() > 0:
            self.operations_table.selectRow(self.operations_table.rowCount() - 1)

    def _build_operations_scan_state_badge(self, state: str) -> QWidget:
        styles = {
            "VERIFICADO": "background-color: rgba(44,122,74,0.25); color: #d8ffe4; border: 1px solid rgba(74,184,111,0.35);",
            "ERROR": "background-color: rgba(189,65,65,0.25); color: #d0d3db; border: 1px solid rgba(255,180,168,0.45);",
        }
        style = styles.get(state, styles["ERROR"])
        return self._build_badge(state, style)

    def _on_operations_selection_changed(self) -> None:
        if self.operations_selected_lbl is None:
            return

        row = self.operations_table.currentRow()
        if row < 0:
            self.operations_selected_lbl.setText("Posicion seleccionada: -")
            return

        pos_item = self.operations_table.item(row, 1)
        pallet_item = self.operations_table.item(row, 8)
        shipment_item = self.operations_table.item(row, 0)
        shipment_id = shipment_item.data(Qt.UserRole) if shipment_item is not None else ""

        pos_text = pos_item.text() if pos_item is not None else "-"
        pallet_text = pallet_item.text() if pallet_item is not None else "-"
        shipment_text = str(shipment_id).strip() or "-"

        self.operations_selected_lbl.setText(
            f"Posicion {pos_text} | Pallet {pallet_text} | Shipment {shipment_text}"
        )

    def _generate_operations_documents(self) -> None:
        self.tabs.setCurrentIndex(0)
        self._set_manifest_feedback("Continua en Embarques para generar Manifiesto y Remision PDF.", tone="neutral")

    def _clear_operations_scan_list(self) -> None:
        self._operations_scan_rows.clear()
        self._operations_activity_log.clear()
        self._operations_pallet_codes.clear()
        self._set_operations_scan_feedback("Lista de escaneo limpiada.", tone="neutral")
        self._apply_filter()

    def _close_operations_shipment(self) -> None:
        self._set_operations_scan_feedback("Embarque marcado para cierre operativo.", tone="neutral")

    def _refresh_operations_side_panels(self, rows: list[dict]) -> None:
        unique_pallets = len({str(row.get("pallet", "")).strip() for row in rows if str(row.get("pallet", "")).strip()})

        total_cajas = 0
        for row in rows:
            try:
                if str(row.get("estado", "")).upper() != "ERROR":
                    total_cajas += int(row.get("bultos", 0))
            except (TypeError, ValueError):
                continue

        if self.operations_summary_lbl is not None:
            self.operations_summary_lbl.setText(
                f"Total Pallets: {unique_pallets}\nTotal Cajas: {total_cajas}"
            )

        pallets_completos = all(int(row.get("bultos", 0)) > 0 for row in rows) if rows else False
        sin_duplicados = unique_pallets == len(rows) if rows else True
        etiquetas_correctas = all(str(row.get("estado", "")).upper() == "VERIFICADO" for row in rows) if rows else False

        if self.operations_checklist_lbl is not None:
            self.operations_checklist_lbl.setText(
                f"[{'OK' if pallets_completos else 'X'}] Pallets completos\n"
                f"[{'OK' if sin_duplicados else 'X'}] Sin duplicados\n"
                f"[{'OK' if etiquetas_correctas else 'X'}] Etiquetas correctas"
            )

        if self.operations_activity_lbl is not None:
            if self._operations_activity_log:
                self.operations_activity_lbl.setText("\n".join(self._operations_activity_log[:6]))
            else:
                self.operations_activity_lbl.setText("Sin actividad reciente.")

        if self.operations_close_btn is not None:
            self.operations_close_btn.setEnabled(bool(rows))

    def _build_embarques_tab(self) -> None:
        self._build_manifests_tab()

    def _load_embarque_rows(self) -> None:
        self._load_manifest_rows()

    def _apply_embarque_filter(self) -> None:
        self._apply_manifest_filter()

    def _registrar_embarque(self) -> None:
        self._generate_manifest()

    def _on_embarque_selection_changed(self) -> None:
        self._on_manifest_selection_changed()

    def _on_embarque_table_item_double_clicked(self, item: QTableWidgetItem) -> None:
        self._on_manifest_table_item_double_clicked(item)

    def _open_embarque_pdf_fields_dialog(self) -> None:
        self._open_manifest_fields_dialog()

    def _generar_manifiesto_pdf_desde_embarque(self) -> None:
        self._export_selected_manifest_pdf()

    def _generar_remision_pdf_desde_embarque(self) -> None:
        self._export_selected_remision_pdf()

    def _selected_embarque(self) -> dict | None:
        return self._selected_manifest()

    def _set_embarque_feedback(self, message: str, tone: str = "neutral") -> None:
        self._set_manifest_feedback(message, tone)

    def _build_manifests_tab(self) -> None:
        tab = QWidget()
        root = QVBoxLayout(tab)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("Embarques")
        title.setStyleSheet("font-size: 20px; font-weight: 600; letter-spacing: 0.5px;")

        subtitle = QLabel("Registra y gestiona embarques para operaciones agricolas.")
        subtitle.setStyleSheet("color: #b0b5c4; font-size: 11px;")

        root.addWidget(title)
        root.addWidget(subtitle)

        generator_frame = QFrame()
        generator_frame.setProperty("class", "card")
        generator_layout = QVBoxLayout(generator_frame)
        generator_layout.setContentsMargins(12, 12, 12, 12)
        generator_layout.setSpacing(10)

        generator_title = QLabel("Registrar Embarque")
        generator_title.setStyleSheet("font-size: 14px; font-weight: 600;")
        generator_layout.addWidget(generator_title)

        top_controls = QHBoxLayout()
        top_controls.setSpacing(10)

        self.manifest_shipment_combo = QComboBox()
        self.manifest_shipment_combo.setMinimumWidth(320)
        self.manifest_shipment_combo.currentIndexChanged.connect(self._on_manifest_shipment_changed)

        self.manifest_type_combo = QComboBox()
        self.manifest_type_combo.addItems(["Outbound", "Transfer", "Export"])

        generate_btn = QPushButton("Registrar Embarque")
        generate_btn.setObjectName("btn_primary")
        generate_btn.clicked.connect(self._registrar_embarque)

        edit_fields_btn = QPushButton("Datos PDF del Embarque")
        edit_fields_btn.clicked.connect(self._open_embarque_pdf_fields_dialog)
        self.manifest_edit_fields_btn = edit_fields_btn

        export_btn = QPushButton("Generar Manifiesto PDF")
        export_btn.clicked.connect(self._generar_manifiesto_pdf_desde_embarque)

        remision_btn = QPushButton("Generar Remision PDF")
        remision_btn.clicked.connect(self._generar_remision_pdf_desde_embarque)

        top_controls.addWidget(self.manifest_shipment_combo, 1)
        top_controls.addWidget(self.manifest_type_combo)
        top_controls.addWidget(generate_btn)
        top_controls.addWidget(edit_fields_btn)
        top_controls.addWidget(export_btn)
        top_controls.addWidget(remision_btn)
        generator_layout.addLayout(top_controls)

        self.manifest_pdf_status_lbl = QLabel("Verificando disponibilidad de Datos PDF para el shipment activo...")
        self.manifest_pdf_status_lbl.setWordWrap(True)
        self.manifest_pdf_status_lbl.setStyleSheet(f"color: {ON_SEC_CONT}; font-size: 11px;")
        generator_layout.addWidget(self.manifest_pdf_status_lbl)

        detail_controls = QHBoxLayout()
        detail_controls.setSpacing(10)

        self.manifest_carrier_edit = QLineEdit()
        self.manifest_carrier_edit.setPlaceholderText("Carrier")
        self.manifest_driver_edit = QLineEdit()
        self.manifest_driver_edit.setPlaceholderText("Driver")
        self.manifest_vehicle_edit = QLineEdit()
        self.manifest_vehicle_edit.setPlaceholderText("Vehicle / Plate")

        detail_controls.addWidget(self.manifest_carrier_edit, 1)
        detail_controls.addWidget(self.manifest_driver_edit)
        detail_controls.addWidget(self.manifest_vehicle_edit)
        generator_layout.addLayout(detail_controls)

        self.manifest_feedback = QLabel("Completa datos del embarque para registrarlo.")
        self.manifest_feedback.setStyleSheet(f"color: {ON_SEC_CONT}; font-size: 11px;")
        generator_layout.addWidget(self.manifest_feedback)

        root.addWidget(generator_frame)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)

        self.manifest_search_edit = QLineEdit()
        self.manifest_search_edit.setPlaceholderText("Buscar por embarque, shipment, transportista, chofer o unidad")
        self.manifest_search_edit.textChanged.connect(self._apply_embarque_filter)

        self.manifest_status_combo = QComboBox()
        self.manifest_status_combo.addItems(["All Status", "Draft", "Issued", "Signed", "Alert"])
        self.manifest_status_combo.currentTextChanged.connect(self._apply_embarque_filter)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._apply_embarque_filter)

        filter_row.addWidget(self.manifest_search_edit, 1)
        filter_row.addWidget(self.manifest_status_combo)
        filter_row.addWidget(refresh_btn)

        registry_frame = QFrame()
        registry_frame.setProperty("class", "card")
        registry_layout = QVBoxLayout(registry_frame)
        registry_layout.setContentsMargins(12, 12, 12, 12)
        registry_layout.setSpacing(8)

        registry_header = QHBoxLayout()
        registry_header.setSpacing(10)

        registry_title = QLabel("Registro de Embarques")
        registry_title.setStyleSheet("font-size: 14px; font-weight: 600;")

        self.manifest_count_lbl = QLabel("0 registros")
        self.manifest_count_lbl.setStyleSheet(f"color: {ON_SEC_CONT}; font-size: 11px;")

        registry_header.addWidget(registry_title)
        registry_header.addWidget(self.manifest_count_lbl)
        registry_header.addStretch(1)

        registry_layout.addLayout(registry_header)
        registry_layout.addLayout(filter_row)

        self.manifest_selected_lbl = QLabel("Selecciona un embarque para generar manifiesto o remision PDF.")
        self.manifest_selected_lbl.setStyleSheet(f"color: {ON_SEC_CONT}; font-size: 11px;")
        registry_layout.addWidget(self.manifest_selected_lbl)

        table_frame = QFrame()
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(0, 0, 0, 0)

        self.manifest_table = ThemedTable(
            ["Embarque", "Shipment", "Cultivo", "Ruta", "Tipo", "Transportista", "Chofer", "Unidad", "Hora", "Estado"]
        )
        self.manifest_table.set_resize_modes(
            {
                0: QHeaderView.ResizeToContents,
                1: QHeaderView.ResizeToContents,
                2: QHeaderView.ResizeToContents,
                3: QHeaderView.Stretch,
                4: QHeaderView.ResizeToContents,
                5: QHeaderView.ResizeToContents,
                6: QHeaderView.ResizeToContents,
                7: QHeaderView.ResizeToContents,
                8: QHeaderView.ResizeToContents,
                9: QHeaderView.Fixed,
            },
            widths={9: 140},
        )
        self.manifest_table.setMinimumHeight(250)
        self.manifest_table.itemSelectionChanged.connect(self._on_embarque_selection_changed)
        self.manifest_table.itemDoubleClicked.connect(self._on_embarque_table_item_double_clicked)
        table_layout.addWidget(self.manifest_table)
        registry_layout.addWidget(table_frame, 1)

        root.addWidget(registry_frame, 1)

        self.tabs.addTab(tab, "Embarques")

    def _open_manifest_fields_dialog(self) -> None:
        active_shipment = str(self.manifest_shipment_combo.currentData() or "").strip()
        if active_shipment:
            self._select_manifest_row_by_shipment(active_shipment)

        manifest = self._selected_manifest()
        if manifest is None:
            if active_shipment:
                self._set_manifest_feedback(
                    f"No hay embarque registrado para {active_shipment}. Registra el embarque primero.",
                    tone="error",
                )
            else:
                self._set_manifest_feedback("Selecciona un embarque antes de abrir Datos PDF del Embarque.", tone="error")
            self._refresh_manifest_pdf_status()
            return

        shipment = self._shipment_map.get(manifest["shipment_id"], {})
        report_data = manifest.get("report_data")
        if not isinstance(report_data, dict):
            report_data = self._default_report_payload_for_manifest(manifest, shipment)
            manifest["report_data"] = report_data

        self._sync_manifest_cargo_from_operations(manifest, shipment)
        report_data = manifest.get("report_data") if isinstance(manifest.get("report_data"), dict) else report_data

        dialog_was_created = False
        if self._manifest_fields_dialog is None:
            self._manifest_fields_dialog = self._build_manifest_fields_dialog()
            dialog_was_created = True

        if dialog_was_created:
            self._sync_manifest_cargo_from_operations(manifest, shipment)
            report_data = manifest.get("report_data") if isinstance(manifest.get("report_data"), dict) else report_data

        self._set_report_field_values(report_data)
        if self._report_dialog_manifest_lbl is not None:
            self._report_dialog_manifest_lbl.setText(
                f"Embarque seleccionado: {manifest['manifest_id']} | Shipment {manifest['shipment_id']}"
            )
        self._refresh_report_copy_source_combo()
        self._set_report_dialog_feedback("Completa campos y presiona Guardar. Los datos quedan ligados a este embarque.", tone="neutral")

        self._manifest_fields_dialog.exec_()

    def _build_manifest_fields_dialog(self) -> QDialog:
        dialog = QDialog(self)
        dialog.setWindowTitle("Datos PDF del Embarque")
        dialog.setModal(True)
        dialog.resize(1220, 760)
        dialog.setStyleSheet(self._report_dialog_stylesheet())

        root = QVBoxLayout(dialog)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        title = QLabel("Datos PDF del Embarque")
        title.setStyleSheet("font-size: 16px; font-weight: 600;")

        self._report_dialog_manifest_lbl = QLabel("Selecciona un embarque primero.")
        self._report_dialog_manifest_lbl.setStyleSheet(f"color: {ON_SEC_CONT}; font-size: 11px;")

        header_row.addWidget(title)
        header_row.addWidget(self._report_dialog_manifest_lbl)
        header_row.addStretch(1)
        root.addLayout(header_row)

        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)

        expand_all_btn = QPushButton("Expand All")
        expand_all_btn.clicked.connect(self._expand_all_report_sections)

        collapse_all_btn = QPushButton("Collapse All")
        collapse_all_btn.clicked.connect(self._collapse_all_report_sections)

        copy_source_lbl = QLabel("Copiar desde")
        copy_source_lbl.setStyleSheet(f"color: {ON_SEC_CONT}; font-size: 11px;")

        self._report_copy_source_combo = QComboBox()
        self._report_copy_source_combo.setMinimumWidth(380)
        self._report_copy_source_combo.setEditable(True)
        self._report_copy_source_combo.setInsertPolicy(QComboBox.NoInsert)
        line_edit = self._report_copy_source_combo.lineEdit()
        if line_edit is not None:
            line_edit.setPlaceholderText("Escribe embarque o shipment para filtrar")

        combo_completer = self._report_copy_source_combo.completer()
        if combo_completer is not None:
            combo_completer.setCaseSensitivity(Qt.CaseInsensitive)
            combo_completer.setFilterMode(Qt.MatchContains)

        duplicate_selected_btn = QPushButton("Copiar Datos Seleccionados")
        duplicate_selected_btn.clicked.connect(self._duplicate_report_fields_from_selected_manifest)

        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self._reset_report_fields_from_dialog)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save_report_fields_from_dialog)

        save_close_btn = QPushButton("Save and Close")
        save_close_btn.setObjectName("btn_primary")
        save_close_btn.clicked.connect(lambda: self._save_report_fields_from_dialog(close_after=True))

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.reject)

        actions_row.addWidget(expand_all_btn)
        actions_row.addWidget(collapse_all_btn)
        actions_row.addWidget(copy_source_lbl)
        actions_row.addWidget(self._report_copy_source_combo)
        actions_row.addWidget(duplicate_selected_btn)
        actions_row.addWidget(reset_btn)
        actions_row.addStretch(1)
        actions_row.addWidget(save_btn)
        actions_row.addWidget(save_close_btn)
        actions_row.addWidget(close_btn)
        root.addLayout(actions_row)

        helper = QLabel("Completa el formulario, guarda y la informacion queda ligada al embarque seleccionado.")
        helper.setStyleSheet(f"color: {ON_SEC_CONT}; font-size: 11px;")
        root.addWidget(helper)

        fields_scroll = QScrollArea()
        fields_scroll.setWidgetResizable(True)
        fields_scroll.setMinimumHeight(520)

        fields_host = QWidget()
        fields_host_layout = QVBoxLayout(fields_host)
        fields_host_layout.setContentsMargins(0, 0, 0, 0)
        fields_host_layout.setSpacing(8)

        self._report_field_edits.clear()
        self._report_section_toggles.clear()

        has_detail_section = False
        for title_text, keys, expanded in _REPORT_SECTIONS:
            section_widget = self._build_report_fields_section(title_text, keys, expanded)
            if title_text == "Detalle de Carga":
                fields_host_layout.addWidget(section_widget, 1)
                has_detail_section = True
            else:
                fields_host_layout.addWidget(section_widget)

        if not has_detail_section:
            fields_host_layout.addStretch(1)
        fields_scroll.setWidget(fields_host)
        root.addWidget(fields_scroll, 1)

        self._report_dialog_feedback_lbl = QLabel("")
        self._report_dialog_feedback_lbl.setStyleSheet(f"color: {ON_SEC_CONT}; font-size: 11px;")
        root.addWidget(self._report_dialog_feedback_lbl)

        return dialog

    def _report_dialog_stylesheet(self) -> str:
        return f"""
        QDialog {{
            background-color: {SURFACE_LOW};
        }}
        QPushButton[sectionToggle="true"] {{
            background-color: {SURFACE_HIGHEST};
            color: {ON_SEC_CONT};
            border: 1px solid rgba(90,64,60,0.35);
            border-radius: 2px;
            text-align: left;
            padding: 7px 10px;
            font-size: 12px;
            font-weight: 600;
            letter-spacing: 0.4px;
        }}
        QPushButton[sectionToggle="true"]:hover {{
            color: {PRIMARY};
            border-color: {PRIMARY};
        }}
        QFrame[reportFieldCard="true"] {{
            background-color: rgba(0,0,0,0.16);
            border: 1px solid rgba(90,64,60,0.2);
            border-radius: 2px;
        }}
        QLabel[reportFieldLabel="true"] {{
            color: {ON_SEC_CONT};
            font-size: 10px;
            font-weight: 600;
        }}
        QLineEdit[reportField="true"] {{
            background-color: {SURFACE_LOWEST};
            color: #f0eded;
            border: 1px solid rgba(90,64,60,0.45);
            border-radius: 3px;
            padding: 6px 10px;
            min-height: 30px;
            selection-background-color: {PRIMARY};
        }}
        QLineEdit[reportField="true"]:focus {{
            border: 1px solid {PRIMARY};
            background-color: {SURFACE_LOWEST};
        }}
        QLineEdit[reportField="true"]::placeholder {{
            color: rgba(176,181,196,0.75);
        }}
        QScrollArea {{
            background: transparent;
            border: none;
        }}
        QScrollArea > QWidget > QWidget {{
            background: transparent;
        }}
        """

    def _save_report_fields_from_dialog(self, close_after: bool = False) -> None:
        if not self._save_report_fields_for_selected_manifest(quiet=True):
            self._set_report_dialog_feedback("Selecciona un embarque antes de guardar.", tone="error")
            return

        self._set_report_dialog_feedback("Datos PDF del embarque guardados.", tone="success")
        manifest = self._selected_manifest()
        if manifest is not None:
            self._set_manifest_feedback(f"Datos PDF guardados para {manifest['manifest_id']}.", tone="success")

        if close_after and self._manifest_fields_dialog is not None:
            self._manifest_fields_dialog.accept()

    def _reset_report_fields_from_dialog(self) -> None:
        manifest = self._selected_manifest()
        if manifest is None:
            self._set_report_dialog_feedback("Selecciona un embarque antes de reiniciar.", tone="error")
            return

        self._reset_report_fields_for_selected_manifest()
        self._set_report_dialog_feedback("Campos reiniciados para este embarque.", tone="neutral")

    def _set_report_dialog_feedback(self, message: str, tone: str = "neutral") -> None:
        if self._report_dialog_feedback_lbl is None:
            return

        if tone == "error":
            color = "#d0d3db"
        elif tone == "success":
            color = "#d8ffe4"
        else:
            color = ON_SEC_CONT

        self._report_dialog_feedback_lbl.setStyleSheet(f"color: {color}; font-size: 11px;")
        self._report_dialog_feedback_lbl.setText(message)

    def _refresh_report_copy_source_combo(self) -> None:
        if self._report_copy_source_combo is None:
            return

        current_manifest = self._selected_manifest()
        previous_selection = str(self._report_copy_source_combo.currentData() or "").strip()

        self._report_copy_source_combo.blockSignals(True)
        self._report_copy_source_combo.clear()

        if current_manifest is None:
            self._report_copy_source_combo.addItem("Selecciona un embarque primero", "")
            self._report_copy_source_combo.setEnabled(False)
            self._report_copy_source_combo.blockSignals(False)
            return

        current_id = current_manifest["manifest_id"]
        self._report_copy_source_combo.addItem("Selecciona embarque origen", "")

        available = 0
        selected_index = 0
        for index, payload in enumerate(self._manifest_rows):
            source_id = payload.get("manifest_id", "")
            if not source_id or source_id == current_id:
                continue

            shipment_id = payload.get("shipment_id", "-")
            issued_at = payload.get("issued_at", "-")
            label = f"{source_id} | {shipment_id} | {issued_at}"
            self._report_copy_source_combo.addItem(label, source_id)
            available += 1

            if source_id == previous_selection:
                selected_index = self._report_copy_source_combo.count() - 1
            elif selected_index == 0 and index > 0:
                selected_index = self._report_copy_source_combo.count() - 1

        if available == 0:
            self._report_copy_source_combo.clear()
            self._report_copy_source_combo.addItem("No hay otros embarques disponibles", "")
            self._report_copy_source_combo.setEnabled(False)
            self._report_copy_source_combo.blockSignals(False)
            return

        self._report_copy_source_combo.setEnabled(True)
        self._report_copy_source_combo.setCurrentIndex(selected_index)
        self._report_copy_source_combo.blockSignals(False)

    def _on_manifest_table_item_double_clicked(self, _item: QTableWidgetItem) -> None:
        self._open_manifest_fields_dialog()

    def _duplicate_report_fields_from_selected_manifest(self) -> None:
        manifest = self._selected_manifest()
        if manifest is None:
            self._set_report_dialog_feedback("Selecciona un embarque antes de copiar datos.", tone="error")
            return

        if self._report_copy_source_combo is None:
            self._set_report_dialog_feedback("El selector de origen no esta disponible.", tone="error")
            return

        source_id = str(self._report_copy_source_combo.currentData() or "").strip()
        if self._report_copy_source_combo.isEditable():
            typed_text = self._report_copy_source_combo.currentText().strip()
            typed_id = typed_text.split("|", 1)[0].strip()
            if typed_id:
                source_manifest_by_text = self._find_manifest_by_id(typed_id)
                if source_manifest_by_text is not None:
                    source_id = typed_id

        if not source_id:
            self._set_report_dialog_feedback("Selecciona un embarque origen en Copiar desde.", tone="error")
            return

        source_manifest = self._find_manifest_by_id(source_id)
        if source_manifest is None:
            self._set_report_dialog_feedback("No se encontro el embarque origen seleccionado.", tone="error")
            self._refresh_report_copy_source_combo()
            return

        self._duplicate_report_fields_from_manifest(source_manifest, manifest)

    def _duplicate_report_fields_from_previous_manifest(self) -> None:
        manifest = self._selected_manifest()
        if manifest is None:
            self._set_report_dialog_feedback("Selecciona un embarque antes de copiar datos.", tone="error")
            return

        previous_manifest = self._find_previous_manifest(manifest["manifest_id"])
        if previous_manifest is None:
            self._set_report_dialog_feedback("No hay un embarque previo disponible para copiar.", tone="error")
            return

        self._duplicate_report_fields_from_manifest(previous_manifest, manifest)

    def _duplicate_report_fields_from_manifest(self, source_manifest: dict, target_manifest: dict) -> None:
        source_data = source_manifest.get("report_data")
        if not isinstance(source_data, dict):
            source_shipment = self._shipment_map.get(source_manifest["shipment_id"], {})
            source_data = self._default_report_payload_for_manifest(source_manifest, source_shipment)

        shipment = self._shipment_map.get(target_manifest["shipment_id"], {})
        target_payload = self._default_report_payload_for_manifest(target_manifest, shipment)

        current = target_manifest.get("report_data")
        if isinstance(current, dict):
            target_payload.update(current)

        for key, _, _ in _REPORT_FIELD_DEFS:
            if key in _DUPLICATE_SKIP_KEYS or key in _CARGO_REPORT_KEYS:
                continue
            value = source_data.get(key, "")
            target_payload[key] = str(value).strip() if value is not None else ""

        target_manifest["report_data"] = target_payload
        self._set_report_field_values(target_payload)

        source_id = source_manifest["manifest_id"]
        target_id = target_manifest["manifest_id"]
        self._set_report_dialog_feedback(f"Datos copiados desde {source_id} hacia {target_id}.", tone="success")
        self._set_manifest_feedback(f"Datos PDF copiados desde {source_id} hacia {target_id}.", tone="success")

    def _find_manifest_by_id(self, manifest_id: str) -> dict | None:
        for payload in self._manifest_rows:
            if payload.get("manifest_id") == manifest_id:
                return payload
        return None

    def _find_previous_manifest(self, manifest_id: str) -> dict | None:
        for index, payload in enumerate(self._manifest_rows):
            if payload.get("manifest_id") != manifest_id:
                continue

            previous_index = index + 1
            if previous_index < len(self._manifest_rows):
                return self._manifest_rows[previous_index]
            return None

        return None

    def _build_report_fields_section(self, title: str, keys: list[str], expanded: bool) -> QWidget:
        section = QFrame()
        section.setProperty("class", "card")

        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(8, 8, 8, 8)
        section_layout.setSpacing(8)

        toggle_btn = QPushButton()
        toggle_btn.setProperty("sectionToggle", "true")
        toggle_btn.setCheckable(True)
        toggle_btn.setChecked(expanded)
        toggle_btn.setText(f"[{'-' if expanded else '+'}] {title}")

        content = QWidget(section)
        content_layout = QGridLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setHorizontalSpacing(8)
        content_layout.setVerticalSpacing(8)

        columns = 2
        row = 0
        col = 0

        if title == "Detalle de Carga":
            self._report_cargo_sync_lbl = QLabel(self._report_cargo_sync_text)
            self._report_cargo_sync_lbl.setWordWrap(True)
            content_layout.addWidget(self._report_cargo_sync_lbl, row, 0, 1, columns)
            self._set_report_cargo_sync_status(self._report_cargo_sync_text, self._report_cargo_sync_tone)
            row += 1

            table_frame = QFrame()
            table_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            table_layout = QVBoxLayout(table_frame)
            table_layout.setContentsMargins(0, 0, 0, 0)
            table_layout.setSpacing(0)

            self._report_cargo_table = ThemedTable(_CARGO_TABLE_COLUMNS)
            self._configure_cargo_table_columns(self._report_cargo_table, compact=True)

            table_layout.addWidget(self._report_cargo_table)
            content_layout.addWidget(table_frame, row, 0, 1, columns)
            content_layout.setRowStretch(row, 1)
            self._render_report_cargo_table([])
            row += 1

        for key in keys:
            if title == "Detalle de Carga":
                continue

            field_meta = _REPORT_FIELD_MAP.get(key)
            if field_meta is None:
                continue

            label, placeholder = field_meta

            field_card = QFrame()
            field_card.setProperty("reportFieldCard", "true")
            field_layout = QVBoxLayout(field_card)
            field_layout.setContentsMargins(8, 6, 8, 8)
            field_layout.setSpacing(4)

            field_label = QLabel(label)
            field_label.setProperty("reportFieldLabel", "true")

            field_edit = QLineEdit()
            field_edit.setProperty("reportField", "true")
            field_edit.setPlaceholderText(placeholder)
            field_edit.setClearButtonEnabled(True)
            if key in _NUMERIC_REPORT_KEYS:
                field_edit.setValidator(QIntValidator(0, 999999999, field_edit))
                field_edit.setAlignment(Qt.AlignRight)

            field_layout.addWidget(field_label)
            field_layout.addWidget(field_edit)

            self._report_field_edits[key] = field_edit

            if key in _WIDE_REPORT_KEYS:
                if col != 0:
                    row += 1
                    col = 0
                content_layout.addWidget(field_card, row, 0, 1, columns)
                row += 1
                col = 0
            else:
                content_layout.addWidget(field_card, row, col)
                col += 1
                if col >= columns:
                    row += 1
                    col = 0

        self._report_section_toggles.append(toggle_btn)
        toggle_btn.toggled.connect(
            lambda checked, btn=toggle_btn, body=content, section_title=title: self._toggle_report_section(
                btn, body, section_title, checked
            )
        )

        section_layout.addWidget(toggle_btn)
        section_layout.addWidget(content, 1 if title == "Detalle de Carga" else 0)
        content.setVisible(expanded)

        return section

    @staticmethod
    def _toggle_report_section(button: QPushButton, body: QWidget, title: str, expanded: bool) -> None:
        body.setVisible(expanded)
        button.setText(f"[{'-' if expanded else '+'}] {title}")

    def _expand_all_report_sections(self) -> None:
        for button in self._report_section_toggles:
            if not button.isChecked():
                button.setChecked(True)

    def _collapse_all_report_sections(self) -> None:
        for button in self._report_section_toggles:
            if button.isChecked():
                button.setChecked(False)

    def _load_rows(self) -> None:
        self._rows = shipment_rows()
        self._shipment_map = {row["id"]: row for row in self._rows}
        self._populate_manifest_shipment_combo()
        self._populate_operations_shipment_combo()
        self._seed_operations_scan_rows()
        self._apply_filter()
        self._refresh_manifest_pdf_status()

        if self._manifest_rows:
            self._apply_manifest_filter()

    def _load_manifest_rows(self) -> None:
        self._manifest_rows = shipment_manifest_rows()
        self._seed_operations_scan_rows()
        self._apply_manifest_filter()
        self._apply_filter()
        self._refresh_manifest_pdf_status()

    def _populate_manifest_shipment_combo(self) -> None:
        previous = self.manifest_shipment_combo.currentData()
        self.manifest_shipment_combo.blockSignals(True)
        self.manifest_shipment_combo.clear()

        for row in self._rows:
            label = f"{row['id']} | {row['crop']} | {row['origin']} -> {row['destination']}"
            self.manifest_shipment_combo.addItem(label, row["id"])

        if previous:
            for index in range(self.manifest_shipment_combo.count()):
                if self.manifest_shipment_combo.itemData(index) == previous:
                    self.manifest_shipment_combo.setCurrentIndex(index)
                    break

        self.manifest_shipment_combo.blockSignals(False)
        self._refresh_manifest_pdf_status()

    def _populate_operations_shipment_combo(self) -> None:
        if self.operations_shipment_combo is None:
            return

        previous = self.operations_shipment_combo.currentData()
        fallback = self.manifest_shipment_combo.currentData()

        self.operations_shipment_combo.blockSignals(True)
        self.operations_shipment_combo.clear()

        for row in self._rows:
            label = f"{row['id']} | {row['crop']} | {row['origin']} -> {row['destination']}"
            self.operations_shipment_combo.addItem(label, row["id"])

        target = str(previous or fallback or "").strip()
        if target:
            self._set_combo_to_shipment(self.operations_shipment_combo, target)

        self.operations_shipment_combo.blockSignals(False)

    def _render_rows(self, rows: list[dict]) -> None:
        if not hasattr(self, "operations_table"):
            return

        previous_selection = ""
        previous_row = self.operations_table.currentRow()
        if previous_row >= 0:
            previous_item = self.operations_table.item(previous_row, 8)
            if previous_item is not None:
                previous_selection = previous_item.text().strip()

        restore_row = -1

        self.operations_table.setSortingEnabled(False)
        self.operations_table.setRowCount(0)

        for payload in rows:
            row = self.operations_table.rowCount()
            self.operations_table.insertRow(row)
            self.operations_table.setRowHeight(row, 36)

            shipment_id = str(payload.get("shipment_id", "")).strip()
            no_text = str(payload.get("no", row + 1))
            pos_text = str(payload.get("pos", f"{row + 1:03d}"))
            bultos_text = str(payload.get("bultos", ""))
            product_text = str(payload.get("producto", ""))
            desc_text = str(payload.get("descripcion", ""))
            size_text = str(payload.get("tamano", ""))
            lot_text = str(payload.get("lote", ""))
            variety_text = str(payload.get("variedad", ""))
            pallet_text = str(payload.get("pallet", "")).strip()

            no_item = SortableTableItem(no_text, int(no_text) if no_text.isdigit() else row + 1)
            no_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            no_item.setData(Qt.UserRole, shipment_id)
            self.operations_table.setItem(row, 0, no_item)

            pos_item = SortableTableItem(pos_text, int(pos_text) if pos_text.isdigit() else row + 1)
            pos_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.operations_table.setItem(row, 1, pos_item)

            bultos_item = SortableTableItem(bultos_text, int(bultos_text) if bultos_text.isdigit() else 0)
            bultos_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.operations_table.setItem(row, 2, bultos_item)

            self.operations_table.setItem(row, 3, QTableWidgetItem(product_text))
            self.operations_table.setItem(row, 4, QTableWidgetItem(desc_text))
            self.operations_table.setItem(row, 5, QTableWidgetItem(size_text))
            self.operations_table.setItem(row, 6, QTableWidgetItem(lot_text))
            self.operations_table.setItem(row, 7, QTableWidgetItem(variety_text))
            self.operations_table.setItem(row, 8, QTableWidgetItem(pallet_text))

            if pallet_text == previous_selection:
                restore_row = row

        self.operations_table.setSortingEnabled(False)

        if self.operations_count_lbl is not None:
            self.operations_count_lbl.setText(f"{len(rows)} registros")

        if restore_row >= 0:
            self.operations_table.selectRow(restore_row)
        elif rows:
            self.operations_table.selectRow(len(rows) - 1)
        else:
            if self.operations_selected_lbl is not None:
                self.operations_selected_lbl.setText("Posicion seleccionada: -")

        self._refresh_operations_side_panels(rows)

    def _render_manifest_rows(self, rows: list[dict]) -> None:
        self.manifest_table.setSortingEnabled(False)
        self.manifest_table.setRowCount(0)
        self.manifest_count_lbl.setText(f"{len(rows)} registros")

        for payload in rows:
            row_idx = self.manifest_table.rowCount()
            self.manifest_table.insertRow(row_idx)
            self.manifest_table.setRowHeight(row_idx, 46)

            shipment_id = payload["shipment_id"]
            source = self._shipment_map.get(shipment_id)
            crop = source["crop"] if source else "-"
            route = f"{source['origin']} -> {source['destination']}" if source else "-"

            self.manifest_table.setItem(row_idx, 0, QTableWidgetItem(payload["manifest_id"]))
            self.manifest_table.setItem(row_idx, 1, QTableWidgetItem(shipment_id))
            self.manifest_table.setItem(row_idx, 2, QTableWidgetItem(crop))
            self.manifest_table.setItem(row_idx, 3, QTableWidgetItem(route))
            self.manifest_table.setItem(row_idx, 4, QTableWidgetItem(payload["doc_type"]))
            self.manifest_table.setItem(row_idx, 5, QTableWidgetItem(payload["carrier"]))
            self.manifest_table.setItem(row_idx, 6, QTableWidgetItem(payload["driver"]))
            self.manifest_table.setItem(row_idx, 7, QTableWidgetItem(payload["vehicle"]))

            issued_item = SortableTableItem(payload["issued_at"], payload["issued_at"])
            issued_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.manifest_table.setItem(row_idx, 8, issued_item)

            status = payload["status"]
            status_item = SortableTableItem("", _MANIFEST_STATUS_ORDER.get(status, 99))
            status_item.setData(Qt.UserRole, status)
            self.manifest_table.setItem(row_idx, 9, status_item)
            self.manifest_table.setCellWidget(row_idx, 9, self._build_manifest_status_badge(status))

        self.manifest_table.setSortingEnabled(True)

        if rows:
            self.manifest_table.selectRow(0)
        else:
            self.manifest_selected_lbl.setText("No hay embarques disponibles con los filtros actuales.")
            self._set_report_field_values({})
            if self._report_dialog_manifest_lbl is not None:
                self._report_dialog_manifest_lbl.setText("No hay embarque seleccionado.")
            self._refresh_report_copy_source_combo()

    def _build_shipment_status_badge(self, status: str) -> QWidget:
        styles = {
            "Pending Dispatch": "background-color: #353534; color: #e5e2e1; border: 1px solid rgba(90,64,60,0.3);",
            "In Transit": "background-color: rgba(139,0,0,0.2); color: #d0d3db; border: 1px solid rgba(255,180,168,0.3);",
            "Delivered": "background-color: rgba(92,154,112,0.22); color: #d8ffe4; border: 1px solid rgba(92,154,112,0.45);",
            "Alert": "background-color: rgba(189,65,65,0.25); color: #d0d3db; border: 1px solid rgba(255,180,168,0.45);",
        }
        style = styles.get(status, styles["Pending Dispatch"])
        return self._build_badge(status, style)

    def _build_manifest_status_badge(self, status: str) -> QWidget:
        styles = {
            "Draft": "background-color: #353534; color: #e5e2e1; border: 1px solid rgba(90,64,60,0.3);",
            "Issued": "background-color: rgba(139,0,0,0.2); color: #d0d3db; border: 1px solid rgba(255,180,168,0.3);",
            "Signed": "background-color: rgba(92,154,112,0.22); color: #d8ffe4; border: 1px solid rgba(92,154,112,0.45);",
            "Alert": "background-color: rgba(189,65,65,0.25); color: #d0d3db; border: 1px solid rgba(255,180,168,0.45);",
        }
        style = styles.get(status, styles["Draft"])
        return self._build_badge(status, style)

    def _apply_filter(self) -> None:
        shipment_id = ""
        if self.operations_shipment_combo is not None:
            shipment_id = str(self.operations_shipment_combo.currentData() or "").strip()

        rows = self._operations_rows_for_shipment(shipment_id) if shipment_id else self._operations_scan_rows
        self._render_rows(rows)

    def _apply_manifest_filter(self) -> None:
        text = self.manifest_search_edit.text().strip().lower()
        status_filter = self.manifest_status_combo.currentText()

        filtered: list[dict] = []
        for row in self._manifest_rows:
            shipment_id = row["shipment_id"]
            source = self._shipment_map.get(shipment_id, {})
            route = f"{source.get('origin', '')} {source.get('destination', '')}".strip().lower()
            crop = source.get("crop", "").lower()

            matches_text = (
                not text
                or text in row["manifest_id"].lower()
                or text in row["shipment_id"].lower()
                or text in row["carrier"].lower()
                or text in row["driver"].lower()
                or text in row["vehicle"].lower()
                or text in row["doc_type"].lower()
                or text in route
                or text in crop
            )
            matches_status = status_filter == "All Status" or row["status"] == status_filter
            if matches_text and matches_status:
                filtered.append(row)

        self._render_manifest_rows(filtered)

    def _generate_manifest(self) -> None:
        shipment_id = self.manifest_shipment_combo.currentData()
        carrier = self.manifest_carrier_edit.text().strip()
        driver = self.manifest_driver_edit.text().strip()
        vehicle = self.manifest_vehicle_edit.text().strip()
        doc_type = self.manifest_type_combo.currentText()

        if not shipment_id:
            self._set_manifest_feedback("Selecciona un shipment antes de registrar el embarque.", tone="error")
            return

        cargo_snapshot = self._collect_operations_cargo_snapshot(str(shipment_id))
        if cargo_snapshot is None:
            self.tabs.setCurrentIndex(1)
            self._set_manifest_feedback(
                "Primero registra la carga en Operations para este shipment antes de registrar el embarque.",
                tone="error",
            )
            self._set_operations_scan_feedback(
                f"Falta informacion de carga en Operations para {shipment_id}.",
                tone="error",
            )
            return

        cargo_rows = cargo_snapshot.get("rows") if isinstance(cargo_snapshot, dict) else []

        if not carrier or not driver or not vehicle:
            self._set_manifest_feedback("Transportista, chofer y unidad son requeridos para registrar el embarque.", tone="error")
            return

        # Encontrar el máximo folio secuencial entre TODOS los manifests existentes
        import re
        sequence = 0
        for row in self._manifest_rows:
            manifest_id = row.get("manifest_id", "")
            # Extraer el último número secuencial de cualquier formato (EMB-0001, EMB-260613-001, etc.)
            match = re.search(r"(\d+)$", manifest_id)
            if match:
                suffix = int(match.group(1))
                sequence = max(sequence, suffix)

        new_manifest = {
            "manifest_id": f"EMB-{sequence + 1:04d}",
            "shipment_id": shipment_id,
            "carrier": carrier,
            "driver": driver,
            "vehicle": vehicle,
            "doc_type": doc_type,
            "issued_at": datetime.now().strftime("%H:%M"),
            "status": "Draft",
        }
        shipment = self._shipment_map.get(shipment_id, {})
        new_manifest["report_data"] = self._default_report_payload_for_manifest(new_manifest, shipment)
        self._sync_manifest_cargo_from_operations(new_manifest, shipment)

        self._manifest_rows.insert(0, new_manifest)
        self._apply_manifest_filter()
        self._apply_filter()

        self.manifest_driver_edit.clear()
        self.manifest_vehicle_edit.clear()
        cargo_count = len(cargo_rows)
        self._set_manifest_feedback(
            f"Embarque {new_manifest['manifest_id']} registrado para {shipment_id} con {cargo_count} pallets de Operations.",
            tone="success",
        )
        self._refresh_manifest_pdf_status()

    def _on_manifest_selection_changed(self) -> None:
        manifest = self._selected_manifest()
        if manifest is None:
            self.manifest_selected_lbl.setText("Selecciona un embarque para generar manifiesto o remision PDF.")
            self._set_report_field_values({})
            self._set_report_cargo_sync_status("Sincronizado desde Operations: selecciona un embarque.", tone="neutral")
            self._render_report_cargo_table([])
            self._refresh_manifest_pdf_status()
            if self._report_dialog_manifest_lbl is not None:
                self._report_dialog_manifest_lbl.setText("Selecciona un embarque primero.")
            self._refresh_report_copy_source_combo()
            return

        selected_shipment_id = str(manifest.get("shipment_id", "")).strip()
        if selected_shipment_id:
            if str(self.manifest_shipment_combo.currentData() or "").strip() != selected_shipment_id:
                self.manifest_shipment_combo.blockSignals(True)
                self._set_combo_to_shipment(self.manifest_shipment_combo, selected_shipment_id)
                self.manifest_shipment_combo.blockSignals(False)

            ops_changed = False
            if self.operations_shipment_combo is not None:
                if str(self.operations_shipment_combo.currentData() or "").strip() != selected_shipment_id:
                    self.operations_shipment_combo.blockSignals(True)
                    self._set_combo_to_shipment(self.operations_shipment_combo, selected_shipment_id)
                    self.operations_shipment_combo.blockSignals(False)
                    ops_changed = True

            if ops_changed:
                self._apply_filter()

        shipment = self._shipment_map.get(manifest["shipment_id"], {})
        report_data = manifest.get("report_data")
        if not isinstance(report_data, dict):
            report_data = self._default_report_payload_for_manifest(manifest, shipment)
            manifest["report_data"] = report_data

        self._sync_manifest_cargo_from_operations(manifest, shipment)
        report_data = manifest.get("report_data") if isinstance(manifest.get("report_data"), dict) else report_data

        self._set_report_field_values(report_data)

        self.manifest_selected_lbl.setText(
            f"Embarque seleccionado: {manifest['manifest_id']} | Shipment {manifest['shipment_id']}"
        )
        if self._report_dialog_manifest_lbl is not None:
            self._report_dialog_manifest_lbl.setText(
                f"Embarque seleccionado: {manifest['manifest_id']} | Shipment {manifest['shipment_id']}"
            )
        self._refresh_report_copy_source_combo()
        self._refresh_manifest_pdf_status()

    def _selected_manifest(self) -> dict | None:
        selection_model = self.manifest_table.selectionModel()
        if selection_model is None:
            return None

        selected_rows = selection_model.selectedRows()
        if not selected_rows:
            return None

        row = selected_rows[0].row()

        item = self.manifest_table.item(row, 0)
        if item is None:
            return None

        manifest_id = item.text().strip()
        for payload in self._manifest_rows:
            if payload["manifest_id"] == manifest_id:
                return payload
        return None

    def _export_selected_manifest_pdf(self) -> None:
        manifest = self._selected_manifest()
        if manifest is None:
            self._set_manifest_feedback("Selecciona un embarque antes de generar el manifiesto PDF.", tone="error")
            return

        if not self._save_report_fields_for_selected_manifest(quiet=True):
            return

        shipment = self._shipment_map.get(manifest["shipment_id"], {})
        route_fallback = ""
        if shipment:
            route_fallback = f"{shipment.get('origin', '')} -> {shipment.get('destination', '')}".strip()

        payload = dict(manifest.get("report_data") or {})
        payload.update(
            {
                "manifest_id": manifest["manifest_id"],
                "shipment_id": manifest["shipment_id"],
                "doc_type": manifest["doc_type"],
                "issued_at": manifest["issued_at"],
                "status": manifest["status"],
                "carrier": payload.get("carrier") or manifest["carrier"],
                "driver": payload.get("driver") or manifest["driver"],
                "vehicle": payload.get("vehicle") or manifest["vehicle"],
                "truck_plate": payload.get("truck_plate") or manifest["vehicle"],
                "trailer_plate": payload.get("trailer_plate") or manifest["vehicle"],
            }
        )

        if not str(payload.get("crop", "")).strip():
            payload["crop"] = shipment.get("crop", "")
        if not str(payload.get("lot", "")).strip():
            payload["lot"] = shipment.get("lot", "")
        if not str(payload.get("route", "")).strip():
            payload["route"] = route_fallback
        if not str(payload.get("departure", "")).strip():
            payload["departure"] = shipment.get("departure", "")
        if not str(payload.get("eta", "")).strip():
            payload["eta"] = shipment.get("eta", "")
        if not str(payload.get("shipper_city", "")).strip():
            payload["shipper_city"] = shipment.get("origin", "")
        if not str(payload.get("distributor", "")).strip():
            payload["distributor"] = shipment.get("destination", "")
        if not str(payload.get("consignee", "")).strip():
            payload["consignee"] = shipment.get("destination", "")
        if not str(payload.get("consignee_city", "")).strip():
            payload["consignee_city"] = shipment.get("destination", "")

        manifest["report_data"] = payload

        try:
            output_path = create_manifest_report(payload)
        except Exception as exc:
            self._set_manifest_feedback(f"No se pudo generar el PDF: {exc}", tone="error")
            return

        if manifest.get("status") == "Draft":
            manifest["status"] = "Issued"
            if isinstance(manifest.get("report_data"), dict):
                manifest["report_data"]["status"] = "Issued"
            self._apply_manifest_filter()

        self._apply_filter()

        self._set_manifest_feedback(f"PDF generado en {output_path}", tone="success")

    def _export_selected_remision_pdf(self) -> None:
        manifest = self._selected_manifest()
        if manifest is None:
            self._set_manifest_feedback("Selecciona un embarque antes de generar la remision PDF.", tone="error")
            return

        if not self._save_report_fields_for_selected_manifest(quiet=True):
            return

        shipment = self._shipment_map.get(manifest["shipment_id"], {})
        route_fallback = ""
        if shipment:
            route_fallback = f"{shipment.get('origin', '')} -> {shipment.get('destination', '')}".strip()

        payload = dict(manifest.get("report_data") or {})
        payload.update(
            {
                "manifest_id": manifest["manifest_id"],
                "shipment_id": manifest["shipment_id"],
                "doc_type": manifest["doc_type"],
                "issued_at": manifest["issued_at"],
                "status": manifest["status"],
                "carrier": payload.get("carrier") or manifest["carrier"],
                "driver": payload.get("driver") or manifest["driver"],
                "vehicle": payload.get("vehicle") or manifest["vehicle"],
                "truck_plate": payload.get("truck_plate") or manifest["vehicle"],
                "trailer_plate": payload.get("trailer_plate") or manifest["vehicle"],
            }
        )

        if not str(payload.get("crop", "")).strip():
            payload["crop"] = shipment.get("crop", "")
        if not str(payload.get("lot", "")).strip():
            payload["lot"] = shipment.get("lot", "")
        if not str(payload.get("route", "")).strip():
            payload["route"] = route_fallback
        if not str(payload.get("departure", "")).strip():
            payload["departure"] = shipment.get("departure", "")
        if not str(payload.get("eta", "")).strip():
            payload["eta"] = shipment.get("eta", "")
        if not str(payload.get("shipper_city", "")).strip():
            payload["shipper_city"] = shipment.get("origin", "")
        if not str(payload.get("distributor", "")).strip():
            payload["distributor"] = shipment.get("destination", "")
        if not str(payload.get("consignee", "")).strip():
            payload["consignee"] = shipment.get("destination", "")
        if not str(payload.get("consignee_city", "")).strip():
            payload["consignee_city"] = shipment.get("destination", "")

        manifest["report_data"] = payload

        try:
            output_path = create_remision_report(payload)
        except Exception as exc:
            self._set_manifest_feedback(f"No se pudo generar la remision PDF: {exc}", tone="error")
            return

        if manifest.get("status") == "Draft":
            manifest["status"] = "Issued"
            if isinstance(manifest.get("report_data"), dict):
                manifest["report_data"]["status"] = "Issued"
            self._apply_manifest_filter()

        self._apply_filter()

        self._set_manifest_feedback(f"Remision PDF generada en {output_path}", tone="success")

    def _default_report_payload_for_manifest(self, manifest: dict, shipment: dict) -> dict:
        # Keep manifest_* payload keys unchanged to preserve the existing PDF template contract.
        manifest_tail = manifest["manifest_id"].rsplit("-", 1)[-1]
        invoice_no = manifest_tail.zfill(4) if manifest_tail.isdigit() else manifest_tail

        origin = shipment.get("origin", "")
        destination = shipment.get("destination", "")
        route = f"{origin} -> {destination}".strip(" ->") if (origin or destination) else ""

        payload = {
            "manifest_id": manifest["manifest_id"],
            "manifest_no": f"E{invoice_no}",
            "invoice_no": invoice_no,
            "issue_date": datetime.now().strftime("%d/%m/%Y"),
            "doc_type": manifest.get("doc_type", ""),
            "issued_at": manifest.get("issued_at", ""),
            "departure_time": manifest.get("issued_at", ""),
            "status": manifest.get("status", "Draft"),
            "shipment_id": manifest.get("shipment_id", ""),
            "crop": shipment.get("crop", ""),
            "lot": shipment.get("lot", ""),
            "route": route,
            "departure": shipment.get("departure", ""),
            "eta": shipment.get("eta", ""),
            "carrier": manifest.get("carrier", ""),
            "driver": manifest.get("driver", ""),
            "vehicle": manifest.get("vehicle", ""),
            "truck_plate": manifest.get("vehicle", ""),
            "trailer_plate": manifest.get("vehicle", ""),
            "shipper_city": origin,
            "distributor": destination,
            "consignee": destination,
            "consignee_city": destination,
            "line_rows": "20",
            "bultos_per_row": "0",
            "total_kg": "0",
            "pallet_start": "0",
            "product_quantity": "20",
        }

        for key, _, _ in _REPORT_FIELD_DEFS:
            payload.setdefault(key, "")

        return payload

    def _set_report_field_values(self, payload: dict) -> None:
        for key, edit in self._report_field_edits.items():
            value = payload.get(key, "") if isinstance(payload, dict) else ""
            edit.setText(str(value) if value is not None else "")

    def _collect_report_field_values(self) -> dict:
        values: dict[str, str] = {}
        for key, edit in self._report_field_edits.items():
            values[key] = edit.text().strip()
        return values

    def _save_report_fields_for_selected_manifest(self, quiet: bool = False) -> bool:
        manifest = self._selected_manifest()
        if manifest is None:
            if not quiet:
                self._set_manifest_feedback("Selecciona un embarque antes de guardar los datos PDF.", tone="error")
            return False

        shipment = self._shipment_map.get(manifest["shipment_id"], {})
        payload = self._default_report_payload_for_manifest(manifest, shipment)

        current = manifest.get("report_data")
        if isinstance(current, dict):
            payload.update(current)

        payload.update(self._collect_report_field_values())

        manifest["report_data"] = payload
        self._sync_manifest_cargo_from_operations(manifest, shipment)

        if not quiet:
            self._set_manifest_feedback(f"Datos PDF guardados para {manifest['manifest_id']}.", tone="success")

        return True

    def _reset_report_fields_for_selected_manifest(self) -> None:
        manifest = self._selected_manifest()
        if manifest is None:
            self._set_manifest_feedback("Selecciona un embarque antes de reiniciar los datos PDF.", tone="error")
            return

        shipment = self._shipment_map.get(manifest["shipment_id"], {})
        payload = self._default_report_payload_for_manifest(manifest, shipment)
        manifest["report_data"] = payload
        self._sync_manifest_cargo_from_operations(manifest, shipment)
        payload = manifest.get("report_data") if isinstance(manifest.get("report_data"), dict) else payload
        self._set_report_field_values(payload)
        self._set_manifest_feedback(f"Datos PDF reiniciados para {manifest['manifest_id']}.", tone="neutral")

    def _set_manifest_feedback(self, message: str, tone: str = "neutral") -> None:
        if tone == "error":
            color = "#d0d3db"
        elif tone == "success":
            color = "#d8ffe4"
        else:
            color = ON_SEC_CONT
        self.manifest_feedback.setStyleSheet(f"color: {color}; font-size: 11px;")
        self.manifest_feedback.setText(message)

    @staticmethod
    def _build_badge(text: str, style: str) -> QWidget:
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setFixedHeight(24)
        label.setStyleSheet(f"QLabel {{ {style} border-radius: 2px; padding: 0 8px; font-size: 11px; }}")

        wrap = QWidget()
        wrap.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(wrap)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.addWidget(label)
        layout.setAlignment(Qt.AlignCenter)
        return wrap