"""PDF reporting helpers for operational documents."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Mapping

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen.canvas import Canvas

_BG = colors.HexColor("#E9E9E9")
_BLUE = colors.HexColor("#2F5596")
_BLACK = colors.HexColor("#111111")


def _sanitize_document_token(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value).strip("-")


def default_manifest_report_path(manifest_id: str) -> Path:
    safe_id = _sanitize_document_token(manifest_id)
    if not safe_id:
        safe_id = "MANIFEST"

    if safe_id.upper().startswith("MAN-"):
        safe_id = safe_id[4:]

    return Path.home() / "Downloads" / f"MAN {safe_id}.pdf"


def default_remision_report_path(remision_no: str) -> Path:
    safe_no = _sanitize_document_token(remision_no)
    if not safe_no:
        safe_no = "E0000"
    return Path.home() / "Downloads" / f"REM {safe_no}.pdf"


def create_manifest_report(payload: Mapping[str, object], output_path: Path | None = None) -> Path:
    data = _normalize_payload(payload)
    destination = Path(output_path) if output_path else default_manifest_report_path(data["manifest_id"])
    _render_operational_document(
        data,
        destination,
        pdf_title=f"Manifest {data['manifest_id']}",
        doc_title="MANIFIESTO GENERAL",
        doc_number_label="MANIFIESTO N°",
    )
    return destination


def create_remision_report(payload: Mapping[str, object], output_path: Path | None = None) -> Path:
    data = _normalize_payload(payload)
    remision_no = _payload_text(payload, "manifest_no", data["manifest_no"])
    destination = Path(output_path) if output_path else default_remision_report_path(remision_no)
    _render_remision_document(
        data,
        destination,
        pdf_title=f"Remision {remision_no}",
    )
    return destination


def _render_remision_document(
    data: Mapping[str, object],
    destination: Path,
    *,
    pdf_title: str,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)

    pdf = Canvas(str(destination), pagesize=letter)
    page_w, page_h = letter
    pdf.setTitle(pdf_title)

    pdf.setFillColor(_BG)
    pdf.rect(0, 0, page_w, page_h, fill=1, stroke=0)

    margin_x = 22.0

    _draw_top_band(
        pdf,
        margin_x,
        709.0,
        568.0,
        56.28,
        66.0,
        data,
        "MANIFIESTO GENERAL",
        "MANIFIESTO N°",
    )

    _draw_remision_origin_dest(pdf, data)
    _draw_remision_transport(pdf, data)
    _draw_remision_detail(pdf, data)
    _draw_remision_signature(pdf, page_w, data)

    pdf.save()


def _draw_remision_doc_box(pdf: Canvas, x: float, y_top: float, w: float, h: float, data: Mapping[str, object]) -> None:
    y_bottom = y_top - h

    pdf.setStrokeColor(_BLACK)
    pdf.setLineWidth(1.8)
    pdf.rect(x, y_bottom, w, h, fill=0, stroke=1)

    row_title_h = 16.5

    y_title = y_top - row_title_h

    pdf.line(x, y_title, x + w, y_title)

    label_w = 90.0
    right_w = w - label_w
    cell_w = right_w / 2

    pdf.line(x + label_w, y_title, x + label_w, y_top)
    pdf.line(x + label_w + cell_w, y_title, x + label_w + cell_w, y_top)

    _draw_text(pdf, x + (label_w / 2), y_top - 11.8, "MANIFIESTO N°", 10.8, "Helvetica", _BLUE, align="center")

    manifest_no = _clean_report_text(data.get("manifest_no"))
    invoice_no = _clean_report_text(data.get("invoice_no"))
    _draw_text(pdf, x + label_w + (cell_w / 2), y_top - 11.8, manifest_no, 11.4, "Helvetica-Bold", _BLACK, align="center")
    _draw_text(
        pdf,
        x + label_w + cell_w + (cell_w / 2),
        y_top - 11.8,
        invoice_no,
        11.4,
        "Helvetica-Bold",
        _BLACK,
        align="center",
    )

    half_w = w / 2
    pdf.line(x + half_w, y_bottom, x + half_w, y_title)

    label_y = y_title - 8.2
    _draw_text(pdf, x + 3.8, label_y, "FECHA DE EMBARQUE", 7.9, "Helvetica", _BLUE)
    _draw_text(pdf, x + half_w + 3.8, label_y, "HORA SALIDA", 8.6, "Helvetica", _BLUE)

    value_y = y_bottom + 5.2
    _draw_text(pdf, x + 3.8, value_y, _clean_report_text(data.get("issue_date")), 9.4, "Helvetica", _BLACK)
    _draw_text(
        pdf,
        x + half_w + 3.8,
        value_y,
        _clean_report_text(data.get("departure_time")),
        9.4,
        "Helvetica",
        _BLACK,
    )


def _draw_remision_origin_dest(pdf: Canvas, data: Mapping[str, object]) -> None:
    y_top = 649.3
    _draw_remision_origin_box(pdf, 22.0, y_top, 262.0, 102.0, data)
    _draw_remision_destination_box(pdf, 290.0, y_top, 300.0, 102.0, data)


def _draw_remision_origin_box(
    pdf: Canvas,
    x: float,
    y_top: float,
    w: float,
    h: float,
    data: Mapping[str, object],
) -> None:
    title_h = _draw_titled_outline(
        pdf,
        x,
        y_top,
        w,
        h,
        "ORIGEN",
        title_h=15.0,
        title_size=10.6,
        title_y_from_top=10.8,
    )
    label_x = x + 3.8
    value_x = x + 92.5
    value_w = w - 97.0
    # Lower content block slightly so row text is visually centered in each table.
    y = y_top - title_h - 12.2
    line_h = 13.0

    rows = [
        ("Embarcador:", _clean_report_text(data.get("shipper"))),
        ("Direccion:", _clean_report_text(data.get("shipper_address"))),
        ("Ciudad:", _clean_report_text(data.get("shipper_city"))),
        ("Reg.Fed.Con.:", _clean_report_text(data.get("shipper_tax"))),
        ("Codigo Postal:", _clean_report_text(data.get("mex_customs_zip"))),
    ]

    for label, value in rows:
        _draw_text(pdf, label_x, y, label, 8.4, "Helvetica", _BLACK)
        _draw_remision_value(pdf, value_x, y, value_w, value, max_lines=1)
        y -= line_h


def _draw_remision_destination_box(
    pdf: Canvas,
    x: float,
    y_top: float,
    w: float,
    h: float,
    data: Mapping[str, object],
) -> None:
    title_h = _draw_titled_outline(
        pdf,
        x,
        y_top,
        w,
        h,
        "DESTINO/CONSIGNE",
        title_h=15.0,
        title_size=10.6,
        title_y_from_top=10.8,
    )
    label_x = x + 4.0
    value_x = x + 61.96
    value_w = w - 66.0
    y = y_top - title_h - 12.2
    line_h = 13.0

    rows = [
        ("DISTRIBUIDOR:", _clean_report_text(data.get("distributor"))),
        ("CONSIGNE:", _clean_report_text(data.get("consignee"))),
        ("DOMIC:", _clean_report_text(data.get("consignee_address"))),
        ("LUGAR:", _clean_report_text(data.get("consignee_city"))),
    ]

    for label, value in rows:
        max_lines = 2 if label == "DOMIC:" else 1
        _draw_text(pdf, label_x, y, label, 8.4, "Helvetica", _BLACK)
        _draw_remision_value(pdf, value_x, y, value_w, value, max_lines=max_lines)
        y -= line_h

    reg_tax = _clean_report_text(data.get("consignee_tax"))
    market = _remision_market_text(data)
    _draw_text(pdf, label_x, y, "REG.FED.CON,:", 8.4, "Helvetica", _BLACK)
    _draw_remision_value(pdf, value_x, y, 96.0, reg_tax, max_lines=1)
    _draw_text(pdf, x + 176.0, y, "MERCADO:", 8.4, "Helvetica", _BLACK)
    _draw_remision_value(pdf, x + 233.0, y, 63.0, market, max_lines=1)


def _draw_remision_transport(pdf: Canvas, data: Mapping[str, object]) -> None:
    x = 22.0
    y_top = 545.3
    w = 568.0
    h = 101.0

    title_h = _draw_titled_outline(
        pdf,
        x,
        y_top,
        w,
        h,
        "TRANSPORTE",
        title_h=15.0,
        title_size=10.6,
        title_y_from_top=10.8,
    )

    left_label_x = 25.8
    left_value_x = 114.48
    right_label_x = 294.0
    right_value_x = 382.0
    plate_label_x = 452.0
    plate_value_x = 490.0

    y = y_top - title_h - 12.7
    line_h = 13.8

    _draw_text(pdf, left_label_x, y, "Linea de Trans:", 8.6, "Helvetica", _BLACK)
    _draw_remision_value(pdf, left_value_x, y, 150.0, _clean_report_text(data.get("carrier")))
    _draw_text(pdf, right_label_x, y, "Reg.Fed.Con.:", 8.6, "Helvetica", _BLACK)
    _draw_remision_value(pdf, right_value_x, y, 84.0, _clean_report_text(data.get("scac")))

    y -= line_h
    _draw_text(pdf, left_label_x, y, "Chofer:", 8.6, "Helvetica", _BLACK)
    _draw_remision_value(pdf, left_value_x, y, 150.0, _clean_report_text(data.get("driver")))
    _draw_text(pdf, right_label_x, y, "N° de Factura:", 8.6, "Helvetica", _BLACK)
    _draw_remision_value(pdf, right_value_x, y, 52.0, _clean_report_text(data.get("invoice_no")))

    y -= line_h
    _draw_text(pdf, left_label_x, y, "Medio:", 8.6, "Helvetica", _BLACK)
    medio = _clean_report_text(data.get("transport_mode")) or "TRAILER"
    _draw_remision_value(pdf, left_value_x, y, 64.0, medio)
    _draw_text(pdf, 184.0, y, "N°:", 8.6, "Helvetica", _BLACK)
    _draw_remision_value(pdf, 207.96, y, 34.0, _clean_report_text(data.get("trailer_no")))
    _draw_text(pdf, right_label_x, y, "Temperatura:", 8.6, "Helvetica", _BLACK)
    _draw_remision_value(pdf, right_value_x, y, 84.0, _clean_report_text(data.get("temperature")))

    y -= line_h
    _draw_text(pdf, left_label_x, y, "N° de Placa:", 8.6, "Helvetica", _BLACK)
    _draw_remision_value(pdf, left_value_x, y, 46.0, _clean_report_text(data.get("truck_plate")))
    _draw_text(pdf, 176.0, y, "Marca:", 8.6, "Helvetica", _BLACK)
    _draw_remision_value(pdf, 207.96, y, 70.0, _clean_report_text(data.get("vehicle")))
    _draw_text(pdf, right_label_x, y, "N° de Caja:", 8.6, "Helvetica", _BLACK)
    _draw_remision_value(pdf, right_value_x, y, 56.0, _clean_report_text(data.get("trailer_no")))
    _draw_text(pdf, plate_label_x, y, "PLACA:", 8.6, "Helvetica", _BLACK)
    _draw_remision_value(pdf, plate_value_x, y, 64.0, _clean_report_text(data.get("trailer_plate")))

    y -= line_h
    _draw_text(pdf, left_label_x, y, "Termografo:", 8.6, "Helvetica", _BLACK)
    _draw_remision_value(pdf, left_value_x, y, 150.0, _clean_report_text(data.get("thermograph")))
    _draw_text(pdf, right_label_x, y, "N. De Licencia:", 8.6, "Helvetica", _BLACK)
    license_value = _clean_report_text(data.get("ff_registration")) or _clean_report_text(data.get("driver_phone"))
    _draw_remision_value(pdf, right_value_x, y, 84.0, license_value)

    y -= line_h
    _draw_text(pdf, left_label_x, y, "Carta Porte:", 8.6, "Helvetica", _BLACK)
    carta_porte = _clean_report_text(data.get("booking")) or _clean_report_text(data.get("seal_no"))
    _draw_remision_value(pdf, left_value_x, y, 150.0, carta_porte)


def _draw_remision_detail(pdf: Canvas, data: Mapping[str, object]) -> None:
    x = 22.0
    y_top = 441.5
    w = 568.0
    panel_shift = y_top - 446.7

    header_h = 18.0
    y_bottom = y_top - header_h

    pdf.setStrokeColor(_BLACK)
    pdf.setLineWidth(1.8)
    pdf.rect(x, y_bottom, w, header_h, fill=0, stroke=1)
    _draw_text(pdf, x + 4.0, y_top - 13.0, "DETALLE DE EMBARQUE", 11.8, "Helvetica", _BLACK)

    line_items = data.get("line_items")
    detail_text = ""
    if isinstance(line_items, list) and line_items:
        first = line_items[0]
        if isinstance(first, dict):
            detail_text = _clean_report_text(first.get("descripcion"))
    if not detail_text:
        detail_text = _clean_report_text(data.get("description")) or _clean_report_text(data.get("product_name"))

    total_bultos = str(_coerce_int(data.get("total_bultos"), 0))
    total_kg = f"{_coerce_int(data.get('total_kg'), 0):,}"

    upper_y = 404.16 + panel_shift
    lower_y = 388.08 + panel_shift

    _draw_text(pdf, x + 156.68, upper_y, total_bultos, 12.0, "Helvetica", _BLACK)
    _draw_text(pdf, x + 214.96, upper_y, total_kg, 12.0, "Helvetica", _BLACK)

    pdf.setLineWidth(2.0)
    pdf.line(x + 120.0, upper_y - 4.0, x + 276.0, upper_y - 4.0)

    _draw_text(pdf, x + 25.04, lower_y, "TOTAL DE CAJAS", 12.0, "Helvetica-Bold", _BLACK)
    _draw_text(pdf, x + 155.72, lower_y, total_bultos, 12.0, "Helvetica-Bold", _BLACK)
    _draw_text(pdf, x + 216.24, lower_y, total_kg, 12.0, "Helvetica-Bold", _BLACK)
    _draw_text(pdf, x + 285.0, lower_y, "Kg", 12.0, "Helvetica-Bold", _BLACK)

    detail_lines = simpleSplit(detail_text, "Helvetica-Bold", 12.0, 245.0)
    if detail_lines:
        _draw_text(pdf, x + 322.52, upper_y, detail_lines[0], 12.0, "Helvetica-Bold", _BLACK)


def _draw_remision_signature(pdf: Canvas, page_w: float, data: Mapping[str, object]) -> None:
    signer = (_clean_report_text(data.get("driver")) or "-").upper()
    line_w = 235.0
    line_y = 96.0
    x0 = (page_w - line_w) / 2

    pdf.setStrokeColor(_BLACK)
    pdf.setLineWidth(2.0)
    pdf.line(x0, line_y, x0 + line_w, line_y)
    _draw_text(pdf, page_w / 2, line_y - 15.0, signer, 12.0, "Helvetica-Bold", _BLACK, align="center")


def _draw_remision_value(pdf: Canvas, x: float, y: float, width: float, value: str, max_lines: int = 1) -> None:
    if not value:
        return

    lines = simpleSplit(value, "Helvetica", 9.0, width)
    if not lines:
        return

    for idx, line in enumerate(lines[: max_lines]):
        _draw_text(pdf, x, y - (idx * 9.8), line, 9.0, "Helvetica", _BLACK)


def _clean_report_text(value: object) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    if not text or text == "-":
        return ""
    return text


def _remision_market_text(data: Mapping[str, object]) -> str:
    doc_type = _clean_report_text(data.get("doc_type"))
    if not doc_type:
        return "Extranjero"

    if doc_type.lower() == "export":
        return "Extranjero"

    if doc_type.lower() == "transfer":
        return "Nacional"

    return doc_type


def _render_operational_document(
    data: Mapping[str, object],
    destination: Path,
    *,
    pdf_title: str,
    doc_title: str,
    doc_number_label: str,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)

    pdf = Canvas(str(destination), pagesize=letter)
    page_w, page_h = letter
    pdf.setTitle(pdf_title)

    pdf.setFillColor(_BG)
    pdf.rect(0, 0, page_w, page_h, fill=1, stroke=0)

    margin_x = 25.2
    content_w = 564.72
    y_top = page_h - 54.0

    y_top = _draw_top_band(pdf, margin_x, y_top, content_w, 56.28, 66.0, data, doc_title, doc_number_label)
    y_top -= 2.16
    y_top = _draw_origin_dest(pdf, margin_x, y_top, content_w, 82.2, 8.04, data)
    y_top -= 5.04
    y_top = _draw_transport(pdf, margin_x, y_top, content_w, 72.0, data)
    y_top -= 4.32
    y_top = _draw_customs(pdf, margin_x, y_top, content_w, 74.28, 8.04, data)
    y_top -= 1.44
    y_top = _draw_booking_po(pdf, margin_x, y_top, content_w, 13.08, 8.04, data)
    y_top -= 4.32
    y_top = _draw_detail_table(pdf, margin_x, y_top, content_w, data)
    y_top -= 25.8
    y_top = _draw_totals_strip(pdf, margin_x, y_top, content_w, 15.24, data)
    y_top -= 13.24
    _draw_product_summary(pdf, margin_x, y_top, content_w, 45.72, data)

    pdf.save()


def _draw_top_band(
    pdf: Canvas,
    x: float,
    y_top: float,
    w: float,
    h: float,
    gap: float,
    data: dict,
    doc_title: str,
    doc_number_label: str,
) -> float:
    logo_w = 260.16
    info_w = 238.56
    if logo_w + info_w > w:
        logo_w = w * 0.54
        info_w = w * 0.42
    gap = w - logo_w - info_w

    _draw_logo_zone(pdf, x, y_top, logo_w, h)
    _draw_manifest_info_zone(pdf, x + logo_w + gap, y_top, info_w, h, data, doc_title, doc_number_label)
    return y_top - h


def _draw_logo_zone(pdf: Canvas, x: float, y_top: float, w: float, h: float) -> None:
    logo_path = Path(__file__).resolve().parents[2] / "ICONS" / "ERP 4.png"
    if logo_path.exists():
        draw_h = h - (4 * mm)
        draw_w = w * 0.62
        pdf.drawImage(
            str(logo_path),
            x + (2 * mm),
            y_top - draw_h - (1 * mm),
            width=draw_w,
            height=draw_h,
            preserveAspectRatio=True,
            mask="auto",
            anchor="w",
        )
        return

    pdf.setFillColor(_BLACK)
    pdf.setFont("Helvetica-Bold", 26)
    pdf.drawString(x + (4 * mm), y_top - (13 * mm), "EMINENT")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(x + (4 * mm), y_top - (19 * mm), "ERP")


def _draw_manifest_info_zone(
    pdf: Canvas,
    x: float,
    y_top: float,
    w: float,
    h: float,
    data: dict,
    doc_title: str,
    doc_number_label: str,
) -> None:
    title_h = 11.88
    row_manifest_h = 13.44
    row_datetime_h = 19.44
    y_bottom = y_top - h

    pdf.setStrokeColor(_BLACK)
    pdf.setLineWidth(1.8)
    pdf.rect(x, y_bottom, w, h, fill=0, stroke=1)

    y = y_top - title_h
    pdf.line(x, y, x + w, y)
    _draw_text(pdf, x + (w / 2), y_top - 8.2, doc_title, 8.0, "Helvetica-Bold", _BLUE, align="center")

    y2 = y - row_manifest_h
    pdf.line(x, y2, x + w, y2)

    label_w = w * 0.56
    right_w = w - label_w
    right_cell_w = right_w / 2

    pdf.line(x + label_w, y2, x + label_w, y)
    pdf.line(x + label_w + right_cell_w, y2, x + label_w + right_cell_w, y)

    _draw_text(pdf, x + (label_w / 2), y - 8.2, doc_number_label, 9.9, "Helvetica", _BLUE, align="center")
    _draw_text(pdf, x + label_w + (right_cell_w / 2), y - 8.2, data["manifest_no"], 10.0, "Helvetica-Bold", _BLACK, align="center")
    _draw_text(
        pdf,
        x + label_w + right_cell_w + (right_cell_w / 2),
        y - 8.2,
        data["invoice_no"],
        10,
        "Helvetica-Bold",
        _BLACK,
        align="center",
    )

    y3 = y2 - row_datetime_h
    pdf.line(x, y3, x + w, y3)
    pdf.line(x + (w / 2), y3, x + (w / 2), y2)

    _draw_text(pdf, x + 6.0, y2 - 8.0, "FECHA DE EMBARQUE", 8.0, "Helvetica", _BLUE)
    _draw_text(pdf, x + 6.0, y2 - 15.3, data["issue_date"], 8.0, "Helvetica", _BLACK)
    _draw_text(pdf, x + (w / 2) + 6.0, y2 - 8.0, "HORA SALIDA", 8.0, "Helvetica", _BLUE)
    _draw_text(pdf, x + (w / 2) + 6.0, y2 - 15.3, data["departure_time"], 8.0, "Helvetica", _BLACK)

    _draw_text(pdf, x + 6.0, y3 - 8.0, "F.F.Registration N°", 9.9, "Helvetica-Bold", _BLUE)
    _draw_text(pdf, x + w - 6.0, y3 - 8.0, data["ff_registration"], 9.9, "Helvetica", _BLACK, align="right")


def _draw_origin_dest(pdf: Canvas, x: float, y_top: float, w: float, h: float, gap: float, data: dict) -> float:
    left_w = (w - gap) / 2
    right_w = left_w

    _draw_info_box(
        pdf,
        x,
        y_top,
        left_w,
        h,
        "ORIGEN/SHIPPER",
        [
            ("Embarcador:", data["shipper"]),
            ("Dirección:", data["shipper_address"]),
            ("Ciudad:", data["shipper_city"]),
            ("Reg.Fed.Con.:", data["shipper_tax"]),
        ],
    )
    _draw_info_box(
        pdf,
        x + left_w + gap,
        y_top,
        right_w,
        h,
        "DESTINO/CONSIGNE",
        [
            ("DISTRIBUIDOR:", data["distributor"]),
            ("CONSIGNE:", data["consignee"]),
            ("DOMIC:", data["consignee_address"]),
            ("LUGAR:", data["consignee_city"]),
            ("REG.FED.CON,:", data["consignee_tax"]),
        ],
    )
    return y_top - h


def _draw_transport(pdf: Canvas, x: float, y_top: float, w: float, h: float, data: dict) -> float:
    title_h = _draw_titled_outline(pdf, x, y_top, w, h, "TRANSPORTE/TRANSPORTATION", title_h=9.6)
    body_top = y_top - title_h

    left_x = x + (1.5 * mm)
    right_x = x + (w * 0.48)
    y = body_top - 6.2
    line_h = 8.2

    left_fields = [
        ("Linea De Trans.:", data["carrier"]),
        ("Chofer:", data["driver"]),
        ("Medio:", data["transport_mode"]),
        ("N° Placa Camion:", data["truck_plate"]),
        ("SCAC:", data["scac"]),
        ("Anticipo Flete:", data["freight_advance"]),
    ]
    right_fields = [
        ("TELEFONO CHOFER.:", data["driver_phone"]),
        ("N° De Factura:", data["invoice_no"]),
        ("Temperatura:", data["temperature"]),
        ("N° de Caja:", data["trailer_no"]),
        ("Placas Caja:", data["trailer_plate"]),
        ("Termografo:", data["thermograph"]),
        ("SELLOS:", data["seal_no"]),
    ]

    _draw_fields_column(pdf, left_x, y, w * 0.45, line_h, left_fields)
    _draw_fields_column(pdf, right_x, y, w * 0.50, line_h, right_fields)

    return y_top - h


def _draw_customs(pdf: Canvas, x: float, y_top: float, w: float, h: float, gap: float, data: dict) -> float:
    left_w = (w - gap) / 2
    right_w = left_w

    _draw_info_box(
        pdf,
        x,
        y_top,
        left_w,
        h,
        "AGENCIA ADUANAL MEXICANA/MEXICAN CUSTOM",
        [
            ("A.Ad.México:", data["mex_customs_agent"]),
            ("Reg.Fed.Con.:", data["mex_customs_tax"]),
            ("Domicilio:", data["mex_customs_address"]),
            ("Lugar:", data["mex_customs_city"]),
            ("Cod. Postal:", data["mex_customs_zip"]),
        ],
    )
    _draw_info_box(
        pdf,
        x + left_w + gap,
        y_top,
        right_w,
        h,
        "AGENCIA ADUANAL AMERICANA/ U.S. CUSTOM",
        [
            ("A.Ad. U.S.", data["us_customs_agent"]),
            ("Reg.Fed.Con.:", data["us_customs_tax"]),
            ("Domicilio:", data["us_customs_address"]),
            ("Lugar:", data["us_customs_city"]),
            ("Cod. Postal:", data["us_customs_zip"]),
        ],
    )
    return y_top - h


def _draw_booking_po(pdf: Canvas, x: float, y_top: float, w: float, h: float, gap: float, data: dict) -> float:
    booking_w = 120.12
    po_w = 72.36
    y_bottom = y_top - h

    _draw_tag_box(pdf, x, y_bottom, booking_w, h, "BOOKING", data["booking"])
    _draw_tag_box(pdf, x + 182.16, y_bottom, po_w, h, "PO", data["po"])
    return y_bottom


def _draw_detail_table(pdf: Canvas, x: float, y_top: float, w: float, data: dict) -> float:
    header_h = 9.6
    row_h = 10.08
    rows = data["line_items"]
    table_h = header_h + (len(rows) * row_h)
    y_bottom = y_top - table_h

    columns = [
        ("No.", 18.24),
        ("Pos.", 31.92),
        ("Bultos", 32.76),
        ("Producto", 60.12),
        ("DESCRIPCION", 173.52),
        ("TAMAÑO", 55.32),
        ("LOTE", 39.96),
        ("VARIEDAD", 98.04),
        ("PALLET", 37.56),
    ]

    raw_total = sum(width for _, width in columns)
    scale = w / raw_total if raw_total else 1.0
    widths = [width * scale for _, width in columns]

    pdf.setStrokeColor(_BLACK)
    pdf.setLineWidth(1.6)
    pdf.rect(x, y_bottom, w, table_h, fill=0, stroke=1)

    y_header = y_top - header_h
    pdf.line(x, y_header, x + w, y_header)

    x_cursor = x
    for idx, (title, _) in enumerate(columns):
        col_w = widths[idx]
        if idx > 0:
            pdf.line(x_cursor, y_bottom, x_cursor, y_top)
        _draw_text(pdf, x_cursor + (col_w / 2), y_top - 7.8, title, 8.02, "Helvetica-Bold", _BLUE, align="center")
        x_cursor += col_w

    for row_idx, item in enumerate(rows):
        y_row_top = y_header - (row_idx * row_h)
        y_row_bottom = y_row_top - row_h
        pdf.setLineWidth(0.9)
        pdf.line(x, y_row_bottom, x + w, y_row_bottom)

        values = [
            str(row_idx + 1),
            str(item["pos"]),
            str(item["bultos"]),
            str(item["producto"]),
            str(item["descripcion"]),
            str(item["tamano"]),
            str(item["lote"]),
            str(item["variedad"]),
            str(item["pallet"]),
        ]

        x_cell = x
        for col_idx, value in enumerate(values):
            col_w = widths[col_idx]
            _draw_text(
                pdf,
                x_cell + (col_w / 2),
                y_row_top - 7.1,
                value,
                8.02,
                "Helvetica",
                _BLACK,
                align="center",
            )
            x_cell += col_w

    return y_bottom


def _draw_totals_strip(pdf: Canvas, x: float, y_top: float, w: float, h: float, data: dict) -> float:
    left_x = x + 20.16
    left_w = 162.0
    right_x = x + 210.36
    right_w = 173.04
    y_bottom = y_top - h

    _draw_total_box(pdf, left_x, y_bottom, left_w, h, str(data["total_bultos"]), "Bultos Manifestados")
    _draw_total_box(pdf, right_x, y_bottom, right_w, h, f"{data['total_kg']:,}", "Kgs. Manifestados")
    return y_bottom


def _draw_product_summary(pdf: Canvas, x: float, y_top: float, w: float, h: float, data: dict) -> float:
    table_w = 425.28
    x_table = x
    header_h = 13.32
    row_h = 15.24
    y_bottom = y_top - h

    col_widths = [208.44, 115.8, 57.24, 43.8]

    pdf.setStrokeColor(_BLACK)
    pdf.setLineWidth(1.6)
    pdf.rect(x_table, y_bottom + row_h, table_w, header_h + row_h, fill=0, stroke=1)

    x_cursor = x_table
    for idx, col_w in enumerate(col_widths):
        if idx > 0:
            pdf.line(x_cursor, y_bottom + row_h, x_cursor, y_bottom + row_h + header_h + row_h)
        x_cursor += col_w

    y_header = y_bottom + row_h + row_h
    pdf.line(x_table, y_header, x_table + table_w, y_header)

    headers = ["Nombre del producto", "Cantidad", "Cajas", "Kg"]
    x_cursor = x_table
    for idx, title in enumerate(headers):
        _draw_text(
            pdf,
            x_cursor + (col_widths[idx] / 2),
            y_bottom + row_h + row_h + 4.2,
            title,
            11.02,
            "Helvetica" if idx == 0 else "Helvetica-Bold",
            _BLACK,
            align="center",
        )
        x_cursor += col_widths[idx]

    values = [
        data["product_name"],
        str(data["product_quantity"]),
        str(data["total_bultos"]),
        str(data["total_kg"]),
    ]
    x_cursor = x_table
    for idx, value in enumerate(values):
        _draw_text(
            pdf,
            x_cursor + (col_widths[idx] / 2),
            y_bottom + row_h + 4.2,
            value,
            11.02,
            "Helvetica",
            _BLACK,
            align="center",
        )
        x_cursor += col_widths[idx]

    total_x = x_table + col_widths[0] + 1.92
    total_w = table_w - col_widths[0] - 1.92
    pdf.rect(total_x, y_bottom, total_w, row_h, fill=0, stroke=1)

    sub_widths = [47.88, 66.0, 57.24, 43.8]
    x_cursor = total_x
    for idx, sub_w in enumerate(sub_widths):
        if idx > 0:
            pdf.line(x_cursor, y_bottom, x_cursor, y_bottom + row_h)
        x_cursor += sub_w

    total_cells = [str(data["product_quantity"]), "Total", str(data["total_bultos"]), str(data["total_kg"])]
    x_cursor = total_x
    for idx, value in enumerate(total_cells):
        font_name = "Helvetica-Bold" if idx > 0 else "Helvetica"
        _draw_text(
            pdf,
            x_cursor + (sub_widths[idx] / 2),
            y_bottom + 4.2,
            value,
            11.02,
            font_name,
            _BLACK,
            align="center",
        )
        x_cursor += sub_widths[idx]

    return y_bottom


def _draw_info_box(
    pdf: Canvas,
    x: float,
    y_top: float,
    w: float,
    h: float,
    title: str,
    fields: list[tuple[str, str]],
) -> None:
    title_h = _draw_titled_outline(pdf, x, y_top, w, h, title)
    y = y_top - title_h - 7.2
    line_h = 10.2
    label_w = w * 0.215

    for label, value in fields:
        wrapped = simpleSplit(value, "Helvetica", 9, w - label_w - (5 * mm))
        if not wrapped:
            wrapped = ["-"]

        _draw_text(pdf, x + (1.5 * mm), y, label, 8.02, "Helvetica", _BLACK)
        _draw_text(pdf, x + label_w + (2.2 * mm), y, wrapped[0], 8.02, "Helvetica", _BLACK)

        if len(wrapped) > 1:
            y -= 3.9 * mm
            _draw_text(pdf, x + label_w + (2.2 * mm), y, wrapped[1], 8.02, "Helvetica", _BLACK)

        y -= line_h


def _draw_fields_column(
    pdf: Canvas,
    x: float,
    y_top: float,
    w: float,
    line_h: float,
    fields: list[tuple[str, str]],
) -> None:
    label_w = w * 0.36
    y = y_top
    for label, value in fields:
        _draw_text(pdf, x, y, label, 8.02, "Helvetica", _BLACK)
        _draw_text(pdf, x + label_w, y, value, 8.02, "Helvetica", _BLACK)
        y -= line_h


def _draw_tag_box(pdf: Canvas, x: float, y: float, w: float, h: float, label: str, value: str) -> None:
    label_w = w * 0.46
    pdf.setStrokeColor(_BLACK)
    pdf.setLineWidth(1.8)
    pdf.rect(x, y, w, h, fill=0, stroke=1)
    pdf.line(x + label_w, y, x + label_w, y + h)

    _draw_text(pdf, x + (label_w / 2), y + (h / 2) - 3.0, label, 8.02, "Helvetica-Bold", _BLUE, align="center")
    _draw_text(pdf, x + label_w + ((w - label_w) / 2), y + (h / 2) - 3.0, value, 8.02, "Helvetica-Bold", _BLACK, align="center")


def _draw_total_box(pdf: Canvas, x: float, y: float, w: float, h: float, value: str, label: str) -> None:
    value_w = w * 0.42
    pdf.setStrokeColor(_BLACK)
    pdf.setLineWidth(1.8)
    pdf.rect(x, y, w, h, fill=0, stroke=1)
    pdf.line(x + value_w, y, x + value_w, y + h)

    _draw_text(pdf, x + (value_w / 2), y + (h / 2) - 4.2, value, 11.02, "Helvetica", _BLACK, align="center")
    _draw_text(pdf, x + value_w + ((w - value_w) / 2), y + (h / 2) - 4.2, label, 11.02, "Helvetica", _BLACK, align="center")


def _draw_titled_outline(
    pdf: Canvas,
    x: float,
    y_top: float,
    w: float,
    h: float,
    title: str,
    title_h: float = 11.16,
    title_size: float = 8.02,
    title_y_from_top: float = 8.2,
) -> float:
    y_bottom = y_top - h

    pdf.setStrokeColor(_BLACK)
    pdf.setLineWidth(1.8)
    pdf.rect(x, y_bottom, w, h, fill=0, stroke=1)
    pdf.line(x, y_top - title_h, x + w, y_top - title_h)

    _draw_text(pdf, x + (1.8 * mm), y_top - title_y_from_top, title, title_size, "Helvetica-Bold", _BLUE)
    return title_h


def _draw_text(
    pdf: Canvas,
    x: float,
    y: float,
    text: str,
    size: float,
    font: str,
    color: colors.Color,
    align: str = "left",
) -> None:
    pdf.setFillColor(color)
    pdf.setFont(font, size)
    if align == "center":
        pdf.drawCentredString(x, y, text)
    elif align == "right":
        pdf.drawRightString(x, y, text)
    else:
        pdf.drawString(x, y, text)


def _normalize_payload(payload: Mapping[str, object]) -> dict:
    manifest_id = _payload_text(payload, "manifest_id", "MAN-UNKNOWN")
    digits = "".join(ch for ch in manifest_id if ch.isdigit())
    short_no = digits[-4:] if len(digits) >= 4 else digits.rjust(4, "0")

    route = _payload_text(payload, "route", "-")
    if "->" in route:
        origin, destination = [part.strip() for part in route.split("->", 1)]
    else:
        origin, destination = route, "-"

    crop = _payload_text(payload, "crop", "-")
    lot = _payload_text(payload, "lot", "-")
    lot_digits = "".join(ch for ch in lot if ch.isdigit())

    row_count = _coerce_int(payload.get("line_rows"), 20)
    row_count = max(1, min(row_count, 20))
    bultos_per_row = _coerce_int(payload.get("bultos_per_row"), 0)
    bultos_per_row = max(0, bultos_per_row)

    product_code = _payload_text(payload, "product_code")
    description = _payload_text(payload, "description")
    size = _payload_text(payload, "size")
    variety = _payload_text(payload, "variety")
    lote_code = _payload_text(payload, "lote_code")
    pallet_start = _coerce_int(payload.get("pallet_start"), 0)

    line_items: list[dict[str, object]] = []
    for idx in range(row_count):
        line_items.append(
            {
                "pos": f"{idx + 1:03d}",
                "bultos": bultos_per_row,
                "producto": product_code,
                "descripcion": description,
                "tamano": size,
                "lote": lote_code,
                "variedad": variety,
                "pallet": str(pallet_start + idx),
            }
        )

    total_bultos = sum(int(item["bultos"]) for item in line_items)
    total_kg = _coerce_int(payload.get("total_kg"), 0)

    return {
        "manifest_id": manifest_id,
        "manifest_no": _payload_text(payload, "manifest_no", f"E{short_no}"),
        "invoice_no": _payload_text(payload, "invoice_no", short_no),
        "doc_type": _payload_text(payload, "doc_type"),
        "issue_date": _payload_text(payload, "issue_date", datetime.now().strftime("%d/%m/%Y")),
        "departure_time": _payload_text(payload, "departure_time", _payload_text(payload, "issued_at", datetime.now().strftime("%H:%M:%S"))),
        "ff_registration": _payload_text(payload, "ff_registration"),
        "shipper": _payload_text(payload, "shipper"),
        "shipper_address": _payload_text(payload, "shipper_address"),
        "shipper_city": _payload_text(payload, "shipper_city", origin),
        "shipper_tax": _payload_text(payload, "shipper_tax"),
        "distributor": _payload_text(payload, "distributor", destination),
        "consignee": _payload_text(payload, "consignee", destination),
        "consignee_address": _payload_text(payload, "consignee_address"),
        "consignee_city": _payload_text(payload, "consignee_city", destination),
        "consignee_tax": _payload_text(payload, "consignee_tax"),
        "carrier": _payload_text(payload, "carrier"),
        "driver": _payload_text(payload, "driver"),
        "vehicle": _payload_text(payload, "vehicle"),
        "transport_mode": _payload_text(payload, "transport_mode"),
        "truck_plate": _payload_text(payload, "truck_plate", _payload_text(payload, "vehicle", "-")),
        "scac": _payload_text(payload, "scac"),
        "freight_advance": _payload_text(payload, "freight_advance"),
        "driver_phone": _payload_text(payload, "driver_phone"),
        "temperature": _payload_text(payload, "temperature"),
        "trailer_no": _payload_text(payload, "trailer_no"),
        "trailer_plate": _payload_text(payload, "trailer_plate", _payload_text(payload, "vehicle", "-")),
        "thermograph": _payload_text(payload, "thermograph"),
        "seal_no": _payload_text(payload, "seal_no"),
        "mex_customs_agent": _payload_text(payload, "mex_customs_agent"),
        "mex_customs_tax": _payload_text(payload, "mex_customs_tax"),
        "mex_customs_address": _payload_text(payload, "mex_customs_address"),
        "mex_customs_city": _payload_text(payload, "mex_customs_city"),
        "mex_customs_zip": _payload_text(payload, "mex_customs_zip"),
        "us_customs_agent": _payload_text(payload, "us_customs_agent"),
        "us_customs_tax": _payload_text(payload, "us_customs_tax"),
        "us_customs_address": _payload_text(payload, "us_customs_address"),
        "us_customs_city": _payload_text(payload, "us_customs_city"),
        "us_customs_zip": _payload_text(payload, "us_customs_zip"),
        "booking": _payload_text(payload, "booking"),
        "po": _payload_text(payload, "po"),
        "line_items": line_items,
        "total_bultos": total_bultos,
        "total_kg": total_kg,
        "product_name": _payload_text(payload, "product_name"),
        "product_quantity": _coerce_int(payload.get("product_quantity"), len(line_items)),
    }


def _coerce_int(value: object, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _payload_text(payload: Mapping[str, object], key: str, default: str = "-") -> str:
    value = payload.get(key, default)
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    return text
