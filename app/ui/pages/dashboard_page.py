"""Production overview dashboard with KPI cards, charts and shipments table."""

from __future__ import annotations

from PyQt5.QtCore import QLineF, QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.chart_palette import get_chart_palette, resolve_chart_preset
from app.core.theme import ON_SEC_CONT, ON_SURFACE, PRIMARY, PRIMARY_CONT, SURFACE_LOW, SURFACE_LOWEST
from app.services.mock_data import (
    dashboard_alert_rows,
    dashboard_client_pallet_rows,
    dashboard_live_summary,
    dashboard_production_kpis,
    dashboard_shipments_today_rows,
    dashboard_trend_points,
)
from app.ui.widgets.themed_table import SortableTableItem, ThemedTable


def _comma_int(value: int) -> str:
    return f"{int(value):,}"


def _nice_max(value: int) -> int:
    if value <= 0:
        return 10
    magnitude = 10 ** (len(str(value)) - 1)
    return ((value + magnitude - 1) // magnitude) * magnitude


_BAR_PALETTE: list[QColor] = [QColor(PRIMARY_CONT), QColor("#0A3D91"), QColor("#0B6B36"), QColor("#6D7583")]
_BAR_ALPHA = 232
_TREND_GREEN = QColor("#0F8D43")
_TREND_TOP_ALPHA = 85
_TREND_MID_ALPHA = 45
_ACTIVE_CHART_PRESET = "navy_forest"


def _apply_chart_palette(preset_name: str | None = None) -> str:
    global _BAR_PALETTE, _BAR_ALPHA, _TREND_GREEN, _TREND_TOP_ALPHA, _TREND_MID_ALPHA, _ACTIVE_CHART_PRESET

    palette = get_chart_palette(preset_name)
    _ACTIVE_CHART_PRESET = str(palette["name"])

    _BAR_PALETTE = [QColor(color_code) for color_code in palette["bars"]]
    _BAR_ALPHA = int(palette["bar_alpha"])
    _TREND_GREEN = QColor(str(palette["trend"]))
    _TREND_TOP_ALPHA = int(palette["trend_top_alpha"])
    _TREND_MID_ALPHA = int(palette["trend_mid_alpha"])
    return _ACTIVE_CHART_PRESET


_apply_chart_palette(resolve_chart_preset())


class MiniSparkline(QWidget):
    def __init__(self, points: list[int], line_color: str, parent=None):
        super().__init__(parent)
        self._points = [int(point) for point in points]
        self._line_color = QColor(line_color)
        self.setMinimumHeight(40)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if len(self._points) < 2:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(4, 6, -4, -4)
        min_value = min(self._points)
        max_value = max(self._points)
        span = max(max_value - min_value, 1)
        step_x = rect.width() / max(len(self._points) - 1, 1)

        points: list[QPointF] = []
        for idx, value in enumerate(self._points):
            x = rect.left() + (idx * step_x)
            norm = (value - min_value) / span
            y = rect.bottom() - (norm * rect.height())
            points.append(QPointF(x, y))

        path = QPainterPath(points[0])
        for point in points[1:]:
            path.lineTo(point)

        area = QPainterPath(path)
        area.lineTo(rect.bottomRight())
        area.lineTo(rect.bottomLeft())
        area.closeSubpath()

        gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        glow = QColor(self._line_color)
        glow.setAlpha(85)
        transparent = QColor(self._line_color)
        transparent.setAlpha(0)
        gradient.setColorAt(0.0, glow)
        gradient.setColorAt(1.0, transparent)
        painter.fillPath(area, gradient)

        pen = QPen(self._line_color, 1.8)
        painter.setPen(pen)
        painter.drawPath(path)


class BarChartWidget(QWidget):
    def __init__(self, rows: list[tuple[str, int]], parent=None):
        super().__init__(parent)
        self._rows = [(label, int(value)) for label, value in rows]
        self.setMinimumHeight(240)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if not self._rows:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(12, 8, -12, -10)
        plot = QRectF(rect.left() + 42, rect.top() + 14, rect.width() - 58, rect.height() - 48)

        values = [value for _, value in self._rows]
        y_max = _nice_max(max(values))

        grid_pen = QPen(QColor(176, 181, 196, 45), 1)
        painter.setPen(grid_pen)
        for step in range(6):
            ratio = step / 5
            y = plot.bottom() - (ratio * plot.height())
            painter.drawLine(QLineF(plot.left(), y, plot.right(), y))

        painter.setPen(QColor(176, 181, 196, 170))
        label_font = painter.font()
        label_font.setPointSize(8)
        painter.setFont(label_font)
        for step in range(6):
            ratio = step / 5
            value = int(y_max * ratio)
            y = plot.bottom() - (ratio * plot.height())
            painter.drawText(QRectF(rect.left(), y - 8, 36, 16), Qt.AlignRight | Qt.AlignVCenter, _comma_int(value))

        bar_count = len(self._rows)
        slot = plot.width() / max(bar_count, 1)
        bar_width = max(18.0, slot * 0.58)
        fm = QFontMetrics(label_font)

        for idx, (label, value) in enumerate(self._rows):
            x_center = plot.left() + (idx + 0.5) * slot
            height_ratio = value / max(y_max, 1)
            bar_height = plot.height() * height_ratio
            bar_rect = QRectF(x_center - (bar_width / 2), plot.bottom() - bar_height, bar_width, bar_height)

            fill_color = QColor(_BAR_PALETTE[idx % len(_BAR_PALETTE)])
            fill_color.setAlpha(_BAR_ALPHA)

            painter.setPen(Qt.NoPen)
            painter.setBrush(fill_color)
            painter.drawRoundedRect(bar_rect, 3, 3)

            painter.setPen(QColor(229, 226, 225, 225))
            value_rect = QRectF(bar_rect.left() - 10, bar_rect.top() - 20, bar_rect.width() + 20, 16)
            painter.drawText(value_rect, Qt.AlignCenter, _comma_int(value))

            painter.setPen(QColor(176, 181, 196, 190))
            x_label_rect = QRectF(x_center - (slot / 2), plot.bottom() + 8, slot, 24)
            clipped_label = fm.elidedText(label, Qt.ElideRight, int(slot - 6))
            painter.drawText(x_label_rect, Qt.AlignHCenter | Qt.AlignTop, clipped_label)


class TrendAreaChartWidget(QWidget):
    def __init__(self, points: list[tuple[str, int]], parent=None):
        super().__init__(parent)
        self._points = [(label, int(value)) for label, value in points]
        self.setMinimumHeight(240)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if len(self._points) < 2:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(12, 8, -12, -10)
        plot = QRectF(rect.left() + 44, rect.top() + 14, rect.width() - 58, rect.height() - 48)

        values = [value for _, value in self._points]
        y_max = _nice_max(max(values))

        grid_pen = QPen(QColor(176, 181, 196, 45), 1)
        painter.setPen(grid_pen)
        for step in range(6):
            ratio = step / 5
            y = plot.bottom() - (ratio * plot.height())
            painter.drawLine(QLineF(plot.left(), y, plot.right(), y))

        painter.setPen(QColor(176, 181, 196, 170))
        axis_font = painter.font()
        axis_font.setPointSize(8)
        painter.setFont(axis_font)
        for step in range(6):
            ratio = step / 5
            value = int(y_max * ratio)
            y = plot.bottom() - (ratio * plot.height())
            painter.drawText(QRectF(rect.left(), y - 8, 38, 16), Qt.AlignRight | Qt.AlignVCenter, _comma_int(value))

        data_points: list[QPointF] = []
        step_x = plot.width() / max(len(self._points) - 1, 1)
        for idx, (_, value) in enumerate(self._points):
            x = plot.left() + (idx * step_x)
            ratio = value / max(y_max, 1)
            y = plot.bottom() - (ratio * plot.height())
            data_points.append(QPointF(x, y))

        path = QPainterPath(data_points[0])
        for idx in range(1, len(data_points)):
            prev_pt = data_points[idx - 1]
            curr_pt = data_points[idx]
            midpoint = QPointF((prev_pt.x() + curr_pt.x()) / 2, (prev_pt.y() + curr_pt.y()) / 2)
            path.quadTo(prev_pt, midpoint)
        path.lineTo(data_points[-1])

        area = QPainterPath(path)
        area.lineTo(plot.bottomRight())
        area.lineTo(plot.bottomLeft())
        area.closeSubpath()

        fill_gradient = QLinearGradient(plot.topLeft(), plot.bottomLeft())
        top_color = QColor(_TREND_GREEN)
        top_color.setAlpha(_TREND_TOP_ALPHA)
        mid_color = QColor(_TREND_GREEN)
        mid_color.setAlpha(_TREND_MID_ALPHA)
        base_color = QColor(_TREND_GREEN)
        base_color.setAlpha(0)
        fill_gradient.setColorAt(0.0, top_color)
        fill_gradient.setColorAt(0.45, mid_color)
        fill_gradient.setColorAt(1.0, base_color)
        painter.fillPath(area, fill_gradient)

        line_pen = QPen(QColor(_TREND_GREEN), 2.2)
        painter.setPen(line_pen)
        painter.drawPath(path)

        marker_pen = QPen(QColor(_TREND_GREEN), 1.4)
        painter.setPen(marker_pen)
        painter.setBrush(QColor(SURFACE_LOWEST))
        for point in data_points:
            painter.drawEllipse(point, 3.2, 3.2)

        fm = QFontMetrics(axis_font)
        painter.setPen(QColor(176, 181, 196, 190))
        for idx, (label, _) in enumerate(self._points):
            x = plot.left() + (idx * step_x)
            x_rect = QRectF(x - (step_x / 2), plot.bottom() + 8, step_x, 22)
            clipped_label = fm.elidedText(label, Qt.ElideRight, int(step_x - 8))
            painter.drawText(x_rect, Qt.AlignHCenter | Qt.AlignTop, clipped_label)


class DashboardMetricCard(QFrame):
    def __init__(self, label: str, value: str, sub_text: str, trend_points: list[int] | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("dashboard_metric_card")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(126)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        label_widget = QLabel(label)
        label_widget.setStyleSheet(f"color: {ON_SEC_CONT}; font-size: 11px; font-weight: 500;")

        value_font_size = 42
        if len(value) > 10:
            value_font_size = 24
        elif len(value) > 7:
            value_font_size = 32

        value_widget = QLabel(value)
        value_widget.setWordWrap(True)
        value_widget.setStyleSheet(
            f"font-size: {value_font_size}px; font-weight: 300; letter-spacing: -0.5px;"
        )

        sub_widget = QLabel(sub_text)
        sub_widget.setStyleSheet(f"color: {ON_SEC_CONT}; font-size: 10px;")

        layout.addWidget(label_widget)
        layout.addWidget(value_widget)
        layout.addWidget(sub_widget)

        if trend_points:
            sparkline = MiniSparkline(trend_points, line_color=PRIMARY)
            layout.addWidget(sparkline)


class DashboardPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_chart_preset = _apply_chart_palette(resolve_chart_preset())
        self.setObjectName("dashboard_page")
        self._apply_local_styles()

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        root.addWidget(self._build_header())
        root.addLayout(self._build_main_content(), 1)
        root.addWidget(self._build_shipments_card(), 2)

    def apply_chart_preset(self, preset_name: str | None = None) -> str:
        self._active_chart_preset = _apply_chart_palette(preset_name)
        if hasattr(self, "client_chart"):
            self.client_chart.update()
        if hasattr(self, "trend_chart"):
            self.trend_chart.update()
        return self._active_chart_preset

    def _apply_local_styles(self) -> None:
        self.setStyleSheet(
            f"""
            QWidget#dashboard_page {{
                background-color: transparent;
            }}
            QFrame#dashboard_panel_card {{
                background-color: {SURFACE_LOW};
                border: 1px solid rgba(90, 64, 60, 0.25);
                border-radius: 12px;
            }}
            QFrame#dashboard_metric_card {{
                background-color: {SURFACE_LOW};
                border: 1px solid rgba(90, 64, 60, 0.24);
                border-radius: 12px;
            }}
            QFrame#dashboard_metric_card:hover {{
                border-color: rgba(208, 211, 219, 0.32);
            }}
            QLabel[dashboardTitle="true"] {{
                font-size: 34px;
                font-weight: 650;
                letter-spacing: 0.2px;
            }}
            QLabel[dashboardMuted="true"] {{
                color: {ON_SEC_CONT};
                font-size: 11px;
            }}
            QPushButton#dashboard_action_btn {{
                background-color: {SURFACE_LOW};
                color: {ON_SURFACE};
                border: 1px solid rgba(90, 64, 60, 0.35);
                border-radius: 10px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: 550;
            }}
            QPushButton#dashboard_action_btn:hover {{
                border-color: rgba(208, 211, 219, 0.38);
            }}
            QLabel[summaryLabel="true"] {{
                color: {ON_SEC_CONT};
                font-size: 11px;
            }}
            QLabel[summaryValue="true"] {{
                color: {ON_SURFACE};
                font-size: 32px;
                font-weight: 300;
                letter-spacing: -0.5px;
            }}
            QLabel[alertIcon="true"] {{
                color: #f06464;
                background-color: rgba(139, 0, 0, 0.17);
                border: 1px solid rgba(139, 0, 0, 0.45);
                border-radius: 9px;
                min-width: 18px;
                max-width: 18px;
                min-height: 18px;
                max-height: 18px;
                font-size: 11px;
                font-weight: 700;
            }}
            QLabel[alertCount="true"] {{
                color: #f4dede;
                background-color: rgba(139, 0, 0, 0.72);
                border-radius: 9px;
                min-width: 18px;
                max-width: 18px;
                min-height: 18px;
                max-height: 18px;
                font-size: 10px;
                font-weight: 600;
            }}
            """
        )

    def _build_header(self) -> QWidget:
        wrap = QWidget()
        row = QHBoxLayout(wrap)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)

        title = QLabel("Dashboard - Production Overview")
        title.setProperty("dashboardTitle", True)

        actions_btn = QPushButton("Global actions")
        actions_btn.setObjectName("dashboard_action_btn")
        actions_btn.setCursor(Qt.PointingHandCursor)

        row.addWidget(title)
        row.addStretch(1)
        row.addWidget(actions_btn)
        return wrap

    def _build_main_content(self) -> QHBoxLayout:
        main = QHBoxLayout()
        main.setSpacing(12)

        left_col = QVBoxLayout()
        left_col.setSpacing(12)

        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(12)
        for payload in dashboard_production_kpis():
            kpi_row.addWidget(
                DashboardMetricCard(
                    label=payload["label"],
                    value=payload["value"],
                    sub_text=payload["sub"],
                    trend_points=payload.get("trend"),
                )
            )
        left_col.addLayout(kpi_row)

        chart_row = QHBoxLayout()
        chart_row.setSpacing(12)
        self.client_chart = BarChartWidget(dashboard_client_pallet_rows())
        self.trend_chart = TrendAreaChartWidget(dashboard_trend_points())
        chart_row.addWidget(self._build_chart_card("Pallets per Client (Top 4)", self.client_chart))
        chart_row.addWidget(self._build_chart_card("Boxes Produced Over Time (Trend)", self.trend_chart))
        left_col.addLayout(chart_row, 1)

        right_col = QVBoxLayout()
        right_col.setSpacing(12)
        right_col.addWidget(self._build_live_summary_card())
        right_col.addWidget(self._build_alerts_card())
        right_col.addStretch(1)

        right_wrap = QWidget()
        right_wrap.setLayout(right_col)
        right_wrap.setFixedWidth(250)

        left_wrap = QWidget()
        left_wrap.setLayout(left_col)

        main.addWidget(left_wrap, 1)
        main.addWidget(right_wrap)
        return main

    def _build_chart_card(self, title: str, chart_widget: QWidget) -> QFrame:
        card = QFrame()
        card.setObjectName("dashboard_panel_card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 10)
        layout.setSpacing(8)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 13px; font-weight: 600;")

        chart_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(title_lbl)
        layout.addWidget(chart_widget, 1)
        return card

    def _build_live_summary_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("dashboard_panel_card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        title = QLabel("Live summary")
        title.setStyleSheet("font-size: 15px; font-weight: 600;")
        layout.addWidget(title)

        for label, value in dashboard_live_summary().items():
            label_widget = QLabel(label)
            label_widget.setProperty("summaryLabel", True)

            value_widget = QLabel(str(value))
            value_widget.setProperty("summaryValue", True)

            layout.addWidget(label_widget)
            layout.addWidget(value_widget)

        layout.addStretch(1)
        return card

    def _build_alerts_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("dashboard_panel_card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("Alerts")
        title.setStyleSheet("font-size: 15px; font-weight: 600;")
        layout.addWidget(title)

        for payload in dashboard_alert_rows():
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(8)

            icon = QLabel("!")
            icon.setProperty("alertIcon", True)
            icon.setAlignment(Qt.AlignCenter)

            text = QLabel(payload["label"])
            text.setStyleSheet(f"color: {ON_SURFACE}; font-size: 11px;")

            count = QLabel(str(payload["count"]))
            count.setProperty("alertCount", True)
            count.setAlignment(Qt.AlignCenter)

            row_layout.addWidget(icon)
            row_layout.addWidget(text, 1)
            row_layout.addWidget(count)
            layout.addWidget(row)

        layout.addStretch(1)
        return card

    def _build_shipments_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("dashboard_panel_card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        title = QLabel("Today's Shipments")
        title.setStyleSheet("font-size: 15px; font-weight: 600;")

        self.shipments_table = ThemedTable(["Shipment ID", "Client", "Pallets", "Boxes", "Status"])
        self.shipments_table.set_resize_modes(
            {
                0: QHeaderView.ResizeToContents,
                1: QHeaderView.Stretch,
                2: QHeaderView.ResizeToContents,
                3: QHeaderView.ResizeToContents,
                4: QHeaderView.Fixed,
            },
            widths={4: 150},
        )

        self._load_shipments_rows()

        layout.addWidget(title)
        layout.addWidget(self.shipments_table, 1)
        return card

    def _load_shipments_rows(self) -> None:
        rows = dashboard_shipments_today_rows()
        status_order = {"In Progress": 0, "Closed": 1}

        self.shipments_table.setSortingEnabled(False)
        self.shipments_table.setRowCount(0)

        for payload in rows:
            row = self.shipments_table.rowCount()
            self.shipments_table.insertRow(row)
            self.shipments_table.setRowHeight(row, 40)

            shipment_item = QTableWidgetItem(payload["shipment_id"])
            client_item = QTableWidgetItem(payload["client"])

            pallets_val = int(payload["pallets"])
            pallets_item = SortableTableItem(_comma_int(pallets_val), pallets_val)
            pallets_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            boxes_val = int(payload["boxes"])
            boxes_item = SortableTableItem(_comma_int(boxes_val), boxes_val)
            boxes_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            status = payload["status"]
            status_item = SortableTableItem("", status_order.get(status, 99))
            status_item.setData(Qt.UserRole, status)

            self.shipments_table.setItem(row, 0, shipment_item)
            self.shipments_table.setItem(row, 1, client_item)
            self.shipments_table.setItem(row, 2, pallets_item)
            self.shipments_table.setItem(row, 3, boxes_item)
            self.shipments_table.setItem(row, 4, status_item)
            self.shipments_table.setCellWidget(row, 4, self._build_status_badge(status))

        self.shipments_table.setSortingEnabled(True)

    @staticmethod
    def _build_status_badge(status: str) -> QWidget:
        label = QLabel(status)
        label.setAlignment(Qt.AlignCenter)
        label.setFixedHeight(24)

        palette = {
            "In Progress": "background-color: rgba(112,87,36,0.45); color: #e5d6a8; border: 1px solid rgba(196,159,70,0.38);",
            "Closed": "background-color: rgba(40,110,76,0.42); color: #b8e1cd; border: 1px solid rgba(58,150,103,0.42);",
        }
        fallback = f"background-color: {SURFACE_LOWEST}; color: {ON_SEC_CONT}; border: 1px solid rgba(90,64,60,0.32);"
        label.setStyleSheet(
            f"QLabel {{ {palette.get(status, fallback)} border-radius: 10px; padding: 0 8px; font-size: 11px; font-weight: 600; }}"
        )

        wrap = QWidget()
        wrap.setStyleSheet("background: transparent;")
        row = QHBoxLayout(wrap)
        row.setContentsMargins(8, 0, 8, 0)
        row.addWidget(label)
        row.setAlignment(Qt.AlignCenter)
        return wrap
