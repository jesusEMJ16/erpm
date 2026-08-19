"""Settings module with local persistence and actionable controls."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core.chart_palette import CHART_PRESET_OPTIONS, normalize_chart_preset
from app.services.settings_store import default_settings, load_settings, save_settings, settings_file_path
from db.connection_manager import (
    SqlServerConfig,
    database_config_file_path,
    load_sqlserver_config,
    save_sqlserver_config,
    test_sqlserver_connection,
    validate_sqlserver_config,
)
from db.db_initializer import initialize_database


class SettingsPage(QWidget):
    _STARTUP_PAGE_OPTIONS = [
        ("dashboard", "Dashboard"),
        ("production", "Produccion en linea"),
        ("shipments", "Shipments"),
        ("traceability", "Traceability"),
        ("reception", "Reception"),
        ("inventory", "Inventory"),
        ("settings", "Settings"),
    ]

    _DENSITY_OPTIONS = [
        ("compact", "Compact"),
        ("standard", "Standard"),
        ("comfortable", "Comfortable"),
    ]

    _DOC_OPTIONS = [
        ("embarque", "Embarque"),
        ("remision", "Remision"),
        ("manifest", "Manifest"),
    ]

    _LANGUAGE_OPTIONS = [
        ("es-MX", "Spanish (Mexico)"),
        ("es-US", "Spanish (United States)"),
        ("en-US", "English (US)"),
    ]

    _TIMEZONE_OPTIONS = [
        "America/Hermosillo",
        "America/Phoenix",
        "America/Los_Angeles",
        "America/Mexico_City",
        "UTC",
    ]

    _CURRENCY_OPTIONS = [
        "MXN",
        "USD",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loading = False
        self._disk_settings = load_settings()
        self._applied_settings = dict(self._disk_settings)
        self._disk_db_config = load_sqlserver_config(use_cache=False)
        self._last_db_test_signature = None

        self._build_ui()
        self._wire_signals()
        self._populate_form(self._disk_settings)
        self._populate_database_form(self._disk_db_config)
        self._refresh_summary()
        self._refresh_database_summary()
        self._refresh_database_dirty_state()
        self._refresh_dirty_state()
        self._refresh_storage_info()

        if settings_file_path().exists():
            self._set_badge("PROFILE LOADED", "ok")
            self._set_notice("Local profile loaded from disk.")
        else:
            self._set_badge("USING DEFAULT PROFILE", "neutral")
            self._set_notice("No settings profile found. Save to create one.")

    def _build_ui(self) -> None:
        self.setStyleSheet(
            """
            QLabel#settings_title {
                font-size: 20px;
                font-weight: 600;
                letter-spacing: 0.5px;
            }
            QLabel#settings_subtitle {
                color: #b0b5c4;
                font-size: 11px;
            }
            QLabel#state_badge {
                background-color: rgba(58,57,57,0.55);
                border: 1px solid rgba(90,64,60,0.35);
                border-radius: 2px;
                color: #c8cbd4;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1px;
                padding: 6px 10px;
            }
            QLabel#state_badge[tone="ok"] {
                color: #d0d3db;
                border-color: rgba(208,211,219,0.45);
                background-color: rgba(139,0,0,0.25);
            }
            QLabel#state_badge[tone="warn"] {
                color: #e5e2e1;
                border-color: rgba(215,190,145,0.6);
                background-color: rgba(121,90,36,0.35);
            }
            QLabel#state_badge[tone="error"] {
                color: #f0eded;
                border-color: rgba(255,180,168,0.7);
                background-color: rgba(139,0,0,0.45);
            }
            QFrame#settings_card {
                background-color: #1c1b1b;
                border: 1px solid rgba(90,64,60,0.22);
                border-radius: 2px;
            }
            QLabel#section_title {
                font-size: 13px;
                font-weight: 600;
                letter-spacing: 0.4px;
            }
            QLabel#section_subtitle {
                color: #b0b5c4;
                font-size: 11px;
            }
            QLabel#field_label {
                color: #c8cbd4;
                font-size: 11px;
            }
            QLineEdit,
            QComboBox,
            QSpinBox {
                background-color: #0e0e0e;
                border: 1px solid rgba(90,64,60,0.4);
                border-radius: 2px;
                color: #e5e2e1;
                font-size: 12px;
                padding: 7px 10px;
                min-height: 22px;
            }
            QLineEdit:focus,
            QComboBox:focus,
            QSpinBox:focus {
                border-color: #d0d3db;
            }
            QComboBox::drop-down {
                border: none;
                width: 22px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #b0b5c4;
                margin-right: 6px;
            }
            QComboBox QAbstractItemView {
                background-color: #2a2a2a;
                color: #e5e2e1;
                border: 1px solid rgba(90,64,60,0.5);
                selection-background-color: #8b0000;
                selection-color: #f0eded;
                outline: none;
            }
            QCheckBox {
                color: #e5e2e1;
                font-size: 12px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 15px;
                height: 15px;
                border: 1px solid rgba(90,64,60,0.65);
                border-radius: 2px;
                background-color: #0e0e0e;
            }
            QCheckBox::indicator:checked {
                background-color: #8b0000;
                border-color: #d0d3db;
            }
            QLabel#notice_lbl {
                color: #b0b5c4;
                font-size: 11px;
            }
            QLabel#dirty_status {
                color: #c8cbd4;
                font-size: 11px;
                font-weight: 600;
            }
            QLabel#dirty_status[tone="ok"] {
                color: #b0b5c4;
            }
            QLabel#dirty_status[tone="warn"] {
                color: #d0d3db;
            }
            QLabel#info_label {
                color: #c8cbd4;
                font-size: 12px;
            }
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        title_col = QVBoxLayout()
        title_col.setSpacing(3)

        title = QLabel("Settings")
        title.setObjectName("settings_title")
        subtitle = QLabel("Configure local profile, interface behavior and operational guards.")
        subtitle.setObjectName("settings_subtitle")

        title_col.addWidget(title)
        title_col.addWidget(subtitle)

        self.state_badge = QLabel()
        self.state_badge.setObjectName("state_badge")
        self.state_badge.setFixedHeight(30)

        header_row.addLayout(title_col)
        header_row.addStretch()
        header_row.addWidget(self.state_badge, 0, Qt.AlignTop)

        root.addLayout(header_row)

        content_row = QHBoxLayout()
        content_row.setSpacing(12)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        left_layout.addWidget(self._build_database_card())
        left_layout.addWidget(self._build_identity_card())
        left_layout.addWidget(self._build_interface_card())
        left_layout.addWidget(self._build_operations_card())
        left_layout.addWidget(self._build_security_card())
        left_layout.addStretch()

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.NoFrame)
        left_scroll.setWidget(left_panel)

        content_row.addWidget(left_scroll, 1)

        side_panel = QWidget()
        side_panel.setFixedWidth(340)
        side_layout = QVBoxLayout(side_panel)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(12)

        side_layout.addWidget(self._build_summary_card())
        side_layout.addWidget(self._build_actions_card())
        side_layout.addWidget(self._build_storage_card())
        side_layout.addStretch()

        content_row.addWidget(side_panel)
        root.addLayout(content_row, 1)

    def _make_card(self, title_text: str, subtitle_text: str) -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame()
        frame.setObjectName("settings_card")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel(title_text)
        title.setObjectName("section_title")

        subtitle = QLabel(subtitle_text)
        subtitle.setObjectName("section_subtitle")
        subtitle.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        return frame, layout

    def _add_form_row(self, form: QFormLayout, label_text: str, field) -> None:
        label = QLabel(label_text)
        label.setObjectName("field_label")
        form.addRow(label, field)

    def _build_database_card(self) -> QFrame:
        card, layout = self._make_card(
            "SQL Server Connection",
            "Configure the ERP database endpoint. Saved changes are written to disk and take effect after restart.",
        )

        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignTop)

        self.db_server_edit = QLineEdit()
        self.db_server_edit.setPlaceholderText("IP address or server name")

        self.db_instance_edit = QLineEdit()
        self.db_instance_edit.setPlaceholderText("Optional instance, e.g. SQLEXPRESS")

        self.db_port_spin = QSpinBox()
        self.db_port_spin.setRange(0, 65535)
        self.db_port_spin.setSpecialValueText("Auto")

        self.db_name_edit = QLineEdit()
        self.db_name_edit.setPlaceholderText("Database name")

        self.db_auth_combo = QComboBox()
        self.db_auth_combo.addItem("Windows Authentication", "windows")
        self.db_auth_combo.addItem("SQL Server Authentication", "sql_server")

        self.db_user_edit = QLineEdit()
        self.db_user_edit.setPlaceholderText("SQL Server user")

        self.db_password_edit = QLineEdit()
        self.db_password_edit.setPlaceholderText("SQL Server password")
        self.db_password_edit.setEchoMode(QLineEdit.Password)

        self._add_form_row(form, "Server", self.db_server_edit)
        self._add_form_row(form, "Instance", self.db_instance_edit)
        self._add_form_row(form, "Port", self.db_port_spin)
        self._add_form_row(form, "Database", self.db_name_edit)
        self._add_form_row(form, "Authentication", self.db_auth_combo)
        self._add_form_row(form, "User", self.db_user_edit)
        self._add_form_row(form, "Password", self.db_password_edit)

        actions = QHBoxLayout()
        actions.setSpacing(8)

        self.db_test_btn = QPushButton("Probar conexion")
        self.db_save_btn = QPushButton("Guardar conexion")

        actions.addWidget(self.db_test_btn)
        actions.addWidget(self.db_save_btn)

        self.db_status_lbl = QLabel()
        self.db_status_lbl.setObjectName("notice_lbl")
        self.db_status_lbl.setWordWrap(True)

        layout.addLayout(form)
        layout.addLayout(actions)
        layout.addWidget(self.db_status_lbl)
        return card

    def _build_identity_card(self) -> QFrame:
        card, layout = self._make_card(
            "Workspace Identity",
            "Business identity and locale defaults used by generated documents and labels.",
        )

        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignTop)

        self.company_name_edit = QLineEdit()
        self.company_name_edit.setPlaceholderText("Visible app title")
        self.site_code_edit = QLineEdit()
        self.site_code_edit.setPlaceholderText("Example: MAIN-HQ")

        self.timezone_combo = QComboBox()
        for timezone in self._TIMEZONE_OPTIONS:
            self.timezone_combo.addItem(timezone, timezone)

        self.language_combo = QComboBox()
        for value, label in self._LANGUAGE_OPTIONS:
            self.language_combo.addItem(label, value)

        self.currency_combo = QComboBox()
        for currency in self._CURRENCY_OPTIONS:
            self.currency_combo.addItem(currency, currency)

        self._add_form_row(form, "Company Name", self.company_name_edit)
        self._add_form_row(form, "Site Code", self.site_code_edit)
        self._add_form_row(form, "Timezone", self.timezone_combo)
        self._add_form_row(form, "Language", self.language_combo)
        self._add_form_row(form, "Currency", self.currency_combo)

        layout.addLayout(form)
        return card

    def _build_interface_card(self) -> QFrame:
        card, layout = self._make_card(
            "Interface",
            "Set startup behavior and list density for operational modules.",
        )

        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignTop)

        self.startup_page_combo = QComboBox()
        for value, label in self._STARTUP_PAGE_OPTIONS:
            self.startup_page_combo.addItem(label, value)

        self.chart_preset_combo = QComboBox()
        for value, label in CHART_PRESET_OPTIONS:
            self.chart_preset_combo.addItem(label, value)

        self.table_density_combo = QComboBox()
        for value, label in self._DENSITY_OPTIONS:
            self.table_density_combo.addItem(label, value)

        self.rows_per_page_spin = QSpinBox()
        self.rows_per_page_spin.setRange(10, 200)
        self.rows_per_page_spin.setSingleStep(5)

        self._add_form_row(form, "Startup Module", self.startup_page_combo)
        self._add_form_row(form, "Chart Theme", self.chart_preset_combo)
        self._add_form_row(form, "Table Density", self.table_density_combo)
        self._add_form_row(form, "Rows Per Page", self.rows_per_page_spin)

        self.live_refresh_check = QCheckBox("Auto refresh dashboard and module snapshots")
        self.show_tooltips_check = QCheckBox("Show contextual tooltips in forms")
        self.show_badges_check = QCheckBox("Show status badges in high-volume tables")

        layout.addLayout(form)
        layout.addSpacing(2)
        layout.addWidget(self.live_refresh_check)
        layout.addWidget(self.show_tooltips_check)
        layout.addWidget(self.show_badges_check)
        return card

    def _build_operations_card(self) -> QFrame:
        card, layout = self._make_card(
            "Operations",
            "Control safeguards and default behavior for shipping and reporting tasks.",
        )

        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignTop)

        self.auto_refresh_spin = QSpinBox()
        self.auto_refresh_spin.setRange(5, 300)
        self.auto_refresh_spin.setSingleStep(5)
        self.auto_refresh_spin.setSuffix(" s")

        self.default_document_combo = QComboBox()
        for value, label in self._DOC_OPTIONS:
            self.default_document_combo.addItem(label, value)

        self._add_form_row(form, "Refresh Interval", self.auto_refresh_spin)
        self._add_form_row(form, "Default Document", self.default_document_combo)

        self.require_signoff_check = QCheckBox("Require supervisor signoff on critical actions")
        self.strict_validation_check = QCheckBox("Use strict data validation before save/export")
        self.auto_pdf_check = QCheckBox("Auto-generate PDF after document closure")

        layout.addLayout(form)
        layout.addSpacing(2)
        layout.addWidget(self.require_signoff_check)
        layout.addWidget(self.strict_validation_check)
        layout.addWidget(self.auto_pdf_check)
        return card

    def _build_security_card(self) -> QFrame:
        card, layout = self._make_card(
            "Security and Alerts",
            "Session timeout, lockout policy and operator alert behavior.",
        )

        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignTop)

        self.session_timeout_spin = QSpinBox()
        self.session_timeout_spin.setRange(5, 240)
        self.session_timeout_spin.setSingleStep(5)
        self.session_timeout_spin.setSuffix(" min")

        self.lockout_spin = QSpinBox()
        self.lockout_spin.setRange(3, 12)

        self.escalation_spin = QSpinBox()
        self.escalation_spin.setRange(5, 120)
        self.escalation_spin.setSingleStep(5)
        self.escalation_spin.setSuffix(" min")

        self._add_form_row(form, "Session Timeout", self.session_timeout_spin)
        self._add_form_row(form, "Lockout Attempts", self.lockout_spin)
        self._add_form_row(form, "Alert Escalation", self.escalation_spin)

        self.allow_multi_session_check = QCheckBox("Allow concurrent sessions per user")
        self.mask_sensitive_check = QCheckBox("Mask sensitive values in logs and previews")
        self.desktop_alerts_check = QCheckBox("Enable desktop alerts")
        self.sound_alerts_check = QCheckBox("Enable sound alerts")

        layout.addLayout(form)
        layout.addSpacing(2)
        layout.addWidget(self.allow_multi_session_check)
        layout.addWidget(self.mask_sensitive_check)
        layout.addWidget(self.desktop_alerts_check)
        layout.addWidget(self.sound_alerts_check)
        return card

    def _build_summary_card(self) -> QFrame:
        card, layout = self._make_card(
            "Profile Summary",
            "Live preview of the current values in the editor.",
        )

        self.summary_identity = QLabel()
        self.summary_identity.setObjectName("info_label")
        self.summary_identity.setWordWrap(True)

        self.summary_interface = QLabel()
        self.summary_interface.setObjectName("info_label")
        self.summary_interface.setWordWrap(True)

        self.summary_operations = QLabel()
        self.summary_operations.setObjectName("info_label")
        self.summary_operations.setWordWrap(True)

        self.summary_security = QLabel()
        self.summary_security.setObjectName("info_label")
        self.summary_security.setWordWrap(True)

        self.summary_database = QLabel()
        self.summary_database.setObjectName("info_label")
        self.summary_database.setWordWrap(True)

        layout.addWidget(self.summary_database)
        layout.addWidget(self.summary_identity)
        layout.addWidget(self.summary_interface)
        layout.addWidget(self.summary_operations)
        layout.addWidget(self.summary_security)
        return card

    def _build_actions_card(self) -> QFrame:
        card, layout = self._make_card(
            "Actions",
            "Apply for this session, save profile to disk, or reset quickly.",
        )

        self.apply_btn = QPushButton("Apply Session")
        self.apply_btn.setObjectName("btn_primary")

        self.save_btn = QPushButton("Save Profile")
        self.reload_btn = QPushButton("Reload From Disk")
        self.defaults_btn = QPushButton("Restore Defaults")

        self.dirty_status_lbl = QLabel()
        self.dirty_status_lbl.setObjectName("dirty_status")

        self.notice_lbl = QLabel()
        self.notice_lbl.setObjectName("notice_lbl")
        self.notice_lbl.setWordWrap(True)

        layout.addWidget(self.apply_btn)
        layout.addWidget(self.save_btn)
        layout.addWidget(self.reload_btn)
        layout.addWidget(self.defaults_btn)
        layout.addSpacing(4)
        layout.addWidget(self.dirty_status_lbl)
        layout.addWidget(self.notice_lbl)
        return card

    def _build_storage_card(self) -> QFrame:
        card, layout = self._make_card(
            "Storage",
            "Settings are stored in a local JSON profile on this machine.",
        )

        self.path_value_lbl = QLabel(str(settings_file_path()))
        self.path_value_lbl.setObjectName("info_label")
        self.path_value_lbl.setWordWrap(True)

        self.db_path_value_lbl = QLabel(str(database_config_file_path()))
        self.db_path_value_lbl.setObjectName("info_label")
        self.db_path_value_lbl.setWordWrap(True)

        self.last_saved_lbl = QLabel("Last saved: never")
        self.last_saved_lbl.setObjectName("info_label")

        layout.addWidget(QLabel("UI profile:"))
        layout.addWidget(self.path_value_lbl)
        layout.addWidget(QLabel("Database profile:"))
        layout.addWidget(self.db_path_value_lbl)
        layout.addWidget(self.last_saved_lbl)
        return card

    def _wire_signals(self) -> None:
        self.db_server_edit.textChanged.connect(self._on_database_form_edited)
        self.db_instance_edit.textChanged.connect(self._on_database_form_edited)
        self.db_port_spin.valueChanged.connect(self._on_database_form_edited)
        self.db_name_edit.textChanged.connect(self._on_database_form_edited)
        self.db_auth_combo.currentIndexChanged.connect(self._on_database_auth_changed)
        self.db_user_edit.textChanged.connect(self._on_database_form_edited)
        self.db_password_edit.textChanged.connect(self._on_database_form_edited)

        self.db_test_btn.clicked.connect(self._test_database_connection)
        self.db_save_btn.clicked.connect(self._save_database_connection)

        self.company_name_edit.textChanged.connect(self._on_form_edited)
        self.site_code_edit.textChanged.connect(self._on_form_edited)
        self.timezone_combo.currentIndexChanged.connect(self._on_form_edited)
        self.language_combo.currentIndexChanged.connect(self._on_form_edited)
        self.currency_combo.currentIndexChanged.connect(self._on_form_edited)

        self.startup_page_combo.currentIndexChanged.connect(self._on_form_edited)
        self.chart_preset_combo.currentIndexChanged.connect(self._on_form_edited)
        self.table_density_combo.currentIndexChanged.connect(self._on_form_edited)
        self.rows_per_page_spin.valueChanged.connect(self._on_form_edited)
        self.live_refresh_check.toggled.connect(self._on_form_edited)
        self.show_tooltips_check.toggled.connect(self._on_form_edited)
        self.show_badges_check.toggled.connect(self._on_form_edited)

        self.auto_refresh_spin.valueChanged.connect(self._on_form_edited)
        self.default_document_combo.currentIndexChanged.connect(self._on_form_edited)
        self.require_signoff_check.toggled.connect(self._on_form_edited)
        self.strict_validation_check.toggled.connect(self._on_form_edited)
        self.auto_pdf_check.toggled.connect(self._on_form_edited)

        self.session_timeout_spin.valueChanged.connect(self._on_form_edited)
        self.lockout_spin.valueChanged.connect(self._on_form_edited)
        self.escalation_spin.valueChanged.connect(self._on_form_edited)
        self.allow_multi_session_check.toggled.connect(self._on_form_edited)
        self.mask_sensitive_check.toggled.connect(self._on_form_edited)
        self.desktop_alerts_check.toggled.connect(self._on_form_edited)
        self.sound_alerts_check.toggled.connect(self._on_form_edited)

        self.apply_btn.clicked.connect(self._apply_session)
        self.save_btn.clicked.connect(self._save_profile)
        self.reload_btn.clicked.connect(self._reload_profile)
        self.defaults_btn.clicked.connect(self._restore_defaults)

    def _set_combo_data(self, combo: QComboBox, value) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)
            return

        text_index = combo.findText(str(value))
        if text_index >= 0:
            combo.setCurrentIndex(text_index)

    @staticmethod
    def _combo_data_or_default(combo: QComboBox, fallback):
        data = combo.currentData()
        if data is None:
            text = combo.currentText().strip()
            return text or fallback
        return data

    def _populate_form(self, payload: dict) -> None:
        self._loading = True
        defaults = default_settings()

        self.company_name_edit.setText(str(payload.get("company_name", defaults["company_name"])))
        self.site_code_edit.setText(str(payload.get("site_code", defaults["site_code"])))

        self._set_combo_data(self.timezone_combo, payload.get("timezone", defaults["timezone"]))
        self._set_combo_data(self.language_combo, payload.get("language", defaults["language"]))
        self._set_combo_data(self.currency_combo, payload.get("currency", defaults["currency"]))

        self._set_combo_data(self.startup_page_combo, payload.get("startup_page", defaults["startup_page"]))
        self._set_combo_data(
            self.chart_preset_combo,
            normalize_chart_preset(payload.get("chart_color_preset", defaults["chart_color_preset"])),
        )
        self._set_combo_data(self.table_density_combo, payload.get("table_density", defaults["table_density"]))
        self.rows_per_page_spin.setValue(int(payload.get("rows_per_page", defaults["rows_per_page"])))
        self.live_refresh_check.setChecked(bool(payload.get("live_refresh", defaults["live_refresh"])))
        self.show_tooltips_check.setChecked(bool(payload.get("show_tooltips", defaults["show_tooltips"])))
        self.show_badges_check.setChecked(bool(payload.get("show_activity_badges", defaults["show_activity_badges"])))

        self.auto_refresh_spin.setValue(int(payload.get("auto_refresh_seconds", defaults["auto_refresh_seconds"])))
        self._set_combo_data(self.default_document_combo, payload.get("default_document", defaults["default_document"]))
        self.require_signoff_check.setChecked(bool(payload.get("require_signoff", defaults["require_signoff"])))
        self.strict_validation_check.setChecked(bool(payload.get("strict_validation", defaults["strict_validation"])))
        self.auto_pdf_check.setChecked(bool(payload.get("auto_generate_pdf", defaults["auto_generate_pdf"])))

        self.session_timeout_spin.setValue(
            int(payload.get("session_timeout_minutes", defaults["session_timeout_minutes"]))
        )
        self.lockout_spin.setValue(int(payload.get("lockout_attempts", defaults["lockout_attempts"])))
        self.escalation_spin.setValue(int(payload.get("escalation_minutes", defaults["escalation_minutes"])))
        self.allow_multi_session_check.setChecked(
            bool(payload.get("allow_multi_session", defaults["allow_multi_session"]))
        )
        self.mask_sensitive_check.setChecked(bool(payload.get("mask_sensitive_data", defaults["mask_sensitive_data"])))
        self.desktop_alerts_check.setChecked(bool(payload.get("desktop_alerts", defaults["desktop_alerts"])))
        self.sound_alerts_check.setChecked(bool(payload.get("sound_alerts", defaults["sound_alerts"])))

        self._loading = False

    def _populate_database_form(self, config: SqlServerConfig) -> None:
        self._loading = True

        self.db_server_edit.setText(config.host)
        self.db_instance_edit.setText(config.instance)
        self.db_port_spin.setValue(int(config.port or 0))
        self.db_name_edit.setText(config.database)
        self._set_combo_data(self.db_auth_combo, "windows" if config.trusted_connection else "sql_server")
        self.db_user_edit.setText("" if config.trusted_connection else config.user)
        self.db_password_edit.setText("" if config.trusted_connection else config.password)
        self._refresh_database_auth_fields()

        self._loading = False

    def _collect_database_config(self) -> SqlServerConfig:
        auth_value = self._combo_data_or_default(self.db_auth_combo, "sql_server")
        trusted_connection = auth_value == "windows"

        port_value = int(self.db_port_spin.value())
        return replace(
            self._disk_db_config,
            host=self.db_server_edit.text().strip(),
            instance=self.db_instance_edit.text().strip(),
            port=port_value if port_value > 0 else None,
            database=self.db_name_edit.text().strip(),
            user="" if trusted_connection else self.db_user_edit.text().strip(),
            password="" if trusted_connection else self.db_password_edit.text(),
            trusted_connection=trusted_connection,
        )

    @staticmethod
    def _database_config_signature(config: SqlServerConfig) -> tuple:
        return (
            config.driver,
            config.host,
            config.port,
            config.instance,
            config.database,
            config.schema,
            config.user,
            config.password,
            config.trusted_connection,
            config.encrypt,
            config.trust_server_certificate,
            config.timeout,
        )

    def _database_endpoint_label(self, config: SqlServerConfig) -> str:
        if config.instance:
            return f"{config.host}\\{config.instance}"
        if config.port is not None:
            return f"{config.host},{config.port}"
        return config.host or "(server missing)"

    def _refresh_database_auth_fields(self) -> None:
        auth_value = self._combo_data_or_default(self.db_auth_combo, "sql_server")
        sql_auth = auth_value == "sql_server"
        self.db_user_edit.setEnabled(sql_auth)
        self.db_password_edit.setEnabled(sql_auth)

    def _refresh_database_summary(self) -> None:
        config = self._collect_database_config()
        auth_label = "Windows Authentication" if config.trusted_connection else f"SQL Auth ({config.user or 'no user'})"
        endpoint = self._database_endpoint_label(config)
        self.summary_database.setText(
            f"Database: {endpoint} | {config.database} | schema {config.schema}\n"
            f"Authentication: {auth_label}"
        )

    def _refresh_database_dirty_state(self) -> None:
        current_signature = self._database_config_signature(self._collect_database_config())
        disk_signature = self._database_config_signature(self._disk_db_config)
        if current_signature == disk_signature:
            self.db_status_lbl.setText(
                f"Database profile loaded from {database_config_file_path()}."
            )
            return

        self.db_status_lbl.setText("Unsaved database connection changes. Test before saving.")

    def _on_database_auth_changed(self, *_args) -> None:
        self._refresh_database_auth_fields()
        self._on_database_form_edited()

    def _on_database_form_edited(self, *_args) -> None:
        if self._loading:
            return
        self._last_db_test_signature = None
        self._refresh_database_summary()
        self._refresh_database_dirty_state()

    def _validate_and_initialize_database_config(self, *, show_success: bool) -> bool:
        config = self._collect_database_config()
        errors = validate_sqlserver_config(config)
        if errors:
            message = "\n".join(errors)
            self.db_status_lbl.setText(message)
            QMessageBox.warning(self, "SQL Server", message)
            return False

        try:
            connection_info = test_sqlserver_connection(config)
            init_result = initialize_database(config=config, schema=config.schema)
        except Exception as exc:
            self.db_status_lbl.setText(f"Connection failed: {exc}")
            QMessageBox.critical(
                self,
                "SQL Server",
                f"Could not connect to SQL Server or initialize schema.\n\n{exc}",
            )
            return False

        self._last_db_test_signature = self._database_config_signature(config)
        created_count = len(init_result["created"])
        existing_count = len(init_result["existing"])
        server_name = connection_info.get("server_name") or connection_info.get("server") or self._database_endpoint_label(config)
        message = (
            f"Connection OK: {server_name} / {connection_info.get('database') or config.database}. "
            f"Tables created: {created_count}; existing: {existing_count}."
        )
        self.db_status_lbl.setText(message)

        if show_success:
            QMessageBox.information(self, "SQL Server", message)
        return True

    def _test_database_connection(self) -> None:
        self._validate_and_initialize_database_config(show_success=True)

    def _save_database_connection(self) -> None:
        config = self._collect_database_config()
        current_signature = self._database_config_signature(config)

        if self._last_db_test_signature != current_signature:
            if not self._validate_and_initialize_database_config(show_success=False):
                return
            config = self._collect_database_config()
            current_signature = self._database_config_signature(config)

        try:
            saved_path = save_sqlserver_config(config)
        except (OSError, ValueError) as exc:
            self.db_status_lbl.setText("Could not save database profile.")
            QMessageBox.critical(self, "SQL Server", f"Could not save database profile.\n\n{exc}")
            return

        self._disk_db_config = config
        self._last_db_test_signature = current_signature
        self._refresh_database_summary()
        self._refresh_database_dirty_state()
        self.db_status_lbl.setText(
            f"Database profile saved to {saved_path}. Restart the app to use it for new ERP connections."
        )

    def _collect_settings(self) -> dict:
        defaults = default_settings()
        return {
            "company_name": self.company_name_edit.text().strip() or defaults["company_name"],
            "site_code": self.site_code_edit.text().strip() or defaults["site_code"],
            "timezone": self._combo_data_or_default(self.timezone_combo, defaults["timezone"]),
            "language": self._combo_data_or_default(self.language_combo, defaults["language"]),
            "currency": self._combo_data_or_default(self.currency_combo, defaults["currency"]),
            "startup_page": self._combo_data_or_default(self.startup_page_combo, defaults["startup_page"]),
            "chart_color_preset": normalize_chart_preset(
                self._combo_data_or_default(self.chart_preset_combo, defaults["chart_color_preset"])
            ),
            "table_density": self._combo_data_or_default(self.table_density_combo, defaults["table_density"]),
            "rows_per_page": int(self.rows_per_page_spin.value()),
            "live_refresh": bool(self.live_refresh_check.isChecked()),
            "show_tooltips": bool(self.show_tooltips_check.isChecked()),
            "show_activity_badges": bool(self.show_badges_check.isChecked()),
            "auto_refresh_seconds": int(self.auto_refresh_spin.value()),
            "require_signoff": bool(self.require_signoff_check.isChecked()),
            "strict_validation": bool(self.strict_validation_check.isChecked()),
            "default_document": self._combo_data_or_default(self.default_document_combo, defaults["default_document"]),
            "auto_generate_pdf": bool(self.auto_pdf_check.isChecked()),
            "session_timeout_minutes": int(self.session_timeout_spin.value()),
            "lockout_attempts": int(self.lockout_spin.value()),
            "allow_multi_session": bool(self.allow_multi_session_check.isChecked()),
            "mask_sensitive_data": bool(self.mask_sensitive_check.isChecked()),
            "desktop_alerts": bool(self.desktop_alerts_check.isChecked()),
            "sound_alerts": bool(self.sound_alerts_check.isChecked()),
            "escalation_minutes": int(self.escalation_spin.value()),
        }

    def _on_form_edited(self, *_args) -> None:
        if self._loading:
            return
        self._refresh_summary()
        self._refresh_dirty_state()

    def _refresh_summary(self, payload: dict | None = None) -> None:
        data = payload or self._collect_settings()

        identity = f"Identity: {data['company_name']} ({data['site_code']})"
        locale = f"Locale: {data['language']} | {data['timezone']} | {data['currency']}"
        self.summary_identity.setText(identity + "\n" + locale)

        startup_label = self.startup_page_combo.currentText()
        chart_theme_label = self.chart_preset_combo.currentText()
        density_label = self.table_density_combo.currentText()
        interface = (
            f"Interface: startup {startup_label}, theme {chart_theme_label}, density {density_label}, rows {data['rows_per_page']}"
        )
        flags = "Flags: "
        flags += "refresh on" if data["live_refresh"] else "refresh off"
        flags += " | tooltips on" if data["show_tooltips"] else " | tooltips off"
        self.summary_interface.setText(interface + "\n" + flags)

        doc_label = self.default_document_combo.currentText()
        operations = (
            f"Operations: refresh each {data['auto_refresh_seconds']}s, default doc {doc_label}"
        )
        safeguards = "Safeguards: "
        safeguards += "signoff on" if data["require_signoff"] else "signoff off"
        safeguards += " | strict validation on" if data["strict_validation"] else " | strict validation off"
        self.summary_operations.setText(operations + "\n" + safeguards)

        security = (
            f"Security: timeout {data['session_timeout_minutes']} min, lockout {data['lockout_attempts']} attempts"
        )
        alerts = "Alerts: desktop on" if data["desktop_alerts"] else "Alerts: desktop off"
        alerts += " | sound on" if data["sound_alerts"] else " | sound off"
        self.summary_security.setText(security + "\n" + alerts)

    def _refresh_dirty_state(self) -> None:
        dirty = self._collect_settings() != self._disk_settings
        if dirty:
            self.dirty_status_lbl.setText("Unsaved changes detected.")
            self._set_label_tone(self.dirty_status_lbl, "warn")
        else:
            self.dirty_status_lbl.setText("Profile synced with local disk profile.")
            self._set_label_tone(self.dirty_status_lbl, "ok")

    def _set_label_tone(self, label: QLabel, tone: str) -> None:
        label.setProperty("tone", tone)
        label.style().unpolish(label)
        label.style().polish(label)
        label.update()

    def _set_badge(self, text: str, tone: str) -> None:
        self.state_badge.setText(text)
        self._set_label_tone(self.state_badge, tone)

    def _set_notice(self, text: str) -> None:
        self.notice_lbl.setText(text)

    def _refresh_storage_info(self) -> None:
        path = settings_file_path()
        self.path_value_lbl.setText(str(path))
        self.db_path_value_lbl.setText(str(database_config_file_path()))

        if not path.exists():
            self.last_saved_lbl.setText("Last saved: never")
            return

        try:
            saved_at = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        except OSError:
            self.last_saved_lbl.setText("Last saved: unknown")
            return

        self.last_saved_lbl.setText(f"Last saved: {saved_at}")

    def _apply_chart_theme_runtime(self, payload: dict) -> None:
        chart_preset = normalize_chart_preset(payload.get("chart_color_preset"))

        shell = self.window()
        pages = getattr(shell, "pages", None)
        if not isinstance(pages, dict):
            return

        for page_key in ("dashboard", "production"):
            page = pages.get(page_key)
            if page is None or not hasattr(page, "apply_chart_preset"):
                continue
            page.apply_chart_preset(chart_preset)

    def _apply_session(self) -> None:
        self._applied_settings = self._collect_settings()
        self._refresh_summary(self._applied_settings)
        self._apply_chart_theme_runtime(self._applied_settings)

        if self._applied_settings == self._disk_settings:
            self._set_badge("PROFILE IN SYNC", "ok")
            self._set_notice("Current values already match saved profile.")
            return

        self._set_badge("APPLIED (NOT SAVED)", "warn")
        self._set_notice("Applied in this session. Save profile to persist these changes.")

    def _save_profile(self) -> None:
        payload = self._collect_settings()

        try:
            save_settings(payload)
        except OSError as exc:
            self._set_badge("SAVE FAILED", "error")
            self._set_notice("Could not write settings profile to disk.")
            QMessageBox.critical(self, "Settings", f"Could not save settings profile.\n\n{exc}")
            return

        self._disk_settings = dict(payload)
        self._applied_settings = dict(payload)
        self._refresh_storage_info()
        self._apply_chart_theme_runtime(payload)
        self._set_badge("PROFILE SAVED", "ok")
        self._set_notice("Profile persisted successfully.")
        self._refresh_dirty_state()

    def _reload_profile(self) -> None:
        self._disk_settings = load_settings()
        self._applied_settings = dict(self._disk_settings)
        self._disk_db_config = load_sqlserver_config(use_cache=False)
        self._last_db_test_signature = None
        self._populate_form(self._disk_settings)
        self._populate_database_form(self._disk_db_config)
        self._refresh_summary(self._disk_settings)
        self._refresh_database_summary()
        self._refresh_database_dirty_state()
        self._refresh_dirty_state()
        self._refresh_storage_info()
        self._apply_chart_theme_runtime(self._disk_settings)

        if settings_file_path().exists():
            self._set_badge("PROFILE RELOADED", "ok")
            self._set_notice("Profile reloaded from local disk file.")
        else:
            self._set_badge("USING DEFAULT PROFILE", "neutral")
            self._set_notice("No file found on disk. Loaded default values.")

    def _restore_defaults(self) -> None:
        choice = QMessageBox.question(
            self,
            "Restore Defaults",
            "Replace current editor values with defaults?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if choice != QMessageBox.Yes:
            return

        defaults = default_settings()
        self._populate_form(defaults)
        self._refresh_summary(defaults)
        self._refresh_dirty_state()
        self._set_badge("DEFAULTS LOADED", "warn")
        self._set_notice("Defaults loaded into editor. Save profile to persist.")
