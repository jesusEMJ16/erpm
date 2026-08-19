"""SQL Server bridge for BLACKERP UI pages and workflows."""

from __future__ import annotations

from datetime import datetime
import re
import uuid

from db.connection import get_connection
from db.sql_names import qn
from modules.boxes import get_box_by_code, register_box
from modules.pallets import assign_box_to_pallet, fetch_pallet_boxes


CLIENTS_TABLE = qn("clients")
EMPLOYEES_TABLE = qn("employees")
PRODUCTS_TABLE = qn("products")
RECEPTIONS_TABLE = qn("receptions")
RECEPTION_DETAILS_TABLE = qn("reception_details")
LOTS_TABLE = qn("lots")
BOXES_TABLE = qn("boxes")
PACKING_LABELS_TABLE = qn("packing_labels")
PALLETS_TABLE = qn("pallets")
PALLET_BOXES_TABLE = qn("pallet_boxes")
SHIPMENTS_TABLE = qn("shipments")
SHIPMENT_PALLETS_TABLE = qn("shipment_pallets")


def _rows_to_dicts(cursor) -> list[dict]:
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _scalar(cursor, query: str, *params):
    cursor.execute(query, *params)
    row = cursor.fetchone()
    return None if row is None else row[0]


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _time_label(value) -> str:
    if isinstance(value, datetime):
        return value.strftime("%H:%M")
    text = str(value or "").strip()
    if len(text) >= 5:
        return text[:5]
    return text or "-"


def _compact_code(value: str, *, prefix: str, max_length: int = 24) -> str:
    cleaned = re.sub(r"[^A-Z0-9]+", "_", str(value or "").upper()).strip("_")
    if not cleaned:
        cleaned = prefix
    if cleaned[0].isdigit():
        cleaned = f"{prefix}_{cleaned}"
    return cleaned[:max_length]


def _line_from_role(role_text: str) -> str:
    match = re.search(r"L\d{2}", str(role_text or "").upper())
    if match:
        return match.group(0)
    return "L07"


def _shipment_status_to_ui(status: str) -> str:
    mapping = {
        "DRAFT": "Pending Dispatch",
        "READY": "Pending Dispatch",
        "IN_TRANSIT": "In Transit",
        "CLOSED": "Delivered",
        "CANCELLED": "Alert",
    }
    return mapping.get(str(status or "").upper(), "Pending Dispatch")


def _shipment_status_to_manifest(status: str) -> str:
    mapping = {
        "Pending Dispatch": "Draft",
        "In Transit": "Issued",
        "Delivered": "Signed",
        "Alert": "Alert",
    }
    return mapping.get(status, "Draft")


def _normalize_employee_code(raw_code: str) -> str:
    token = str(raw_code or "").strip().upper()
    digits = "".join(ch for ch in token if ch.isdigit())
    if digits:
        return digits.lstrip("0") or "0"
    return token


def _default_lot_code(line: str) -> str:
    normalized_line = _compact_code(line, prefix="L", max_length=8)
    return f"LOT-{datetime.utcnow():%y%m%d}-{normalized_line}"


def fetch_packing_label_by_id(label_id: str) -> dict | None:
    normalized_label_id = str(label_id or "").strip()
    if not normalized_label_id:
        return None

    # La columna label_id en packing_labels es INT. Rechazar valores no numéricos
    # para evitar pyodbc.DataError (22018) de conversión nvarchar → int.
    if not normalized_label_id.isdigit():
        return None

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            SELECT TOP 1
                pl.label_id,
                pl.presentation,
                pl.packed_weight_lb,
                pl.packed_date,
                pl.created_at,
                pl.lot_code,
                pl.variety_name,
                pl.client_name,
                p.product_name
            FROM {PACKING_LABELS_TABLE} pl
            LEFT JOIN {LOTS_TABLE} l ON pl.lot_code = l.lot_code
            LEFT JOIN {PRODUCTS_TABLE} p ON l.product_id = p.product_id
            WHERE pl.label_id = ?
            """,
            normalized_label_id,
        )

        row = cursor.fetchone()
        if row is None:
            return None

        columns = [column[0] for column in cursor.description]
        payload = dict(zip(columns, row))
        payload["label_id"] = str(payload.get("label_id", "")).strip()
        payload["presentation"] = str(payload.get("presentation", "")).strip()
        payload["lot_code"] = str(payload.get("lot_code", "")).strip()
        payload["variety_name"] = str(payload.get("variety_name", "")).strip()
        payload["client_name"] = str(payload.get("client_name", "")).strip()
        payload["packed_weight_lb"] = _safe_float(payload.get("packed_weight_lb", 0.0))
        return payload
    finally:
        connection.close()


def _compose_reception_notes(field_block: str, notes: str) -> str:
    base = str(notes or "").strip()
    field = str(field_block or "").strip()
    if field:
        if base:
            return f"FIELD_BLOCK={field}; {base}"
        return f"FIELD_BLOCK={field}"
    return base


def _extract_field_block(notes: str, supplier_name: str) -> str:
    note_text = str(notes or "")
    match = re.search(r"FIELD_BLOCK=([^;]+)", note_text)
    if match:
        return match.group(1).strip()
    supplier = str(supplier_name or "").strip()
    return supplier or "Campo sin especificar"


def _fetch_or_create_product(cursor, product_name: str) -> tuple[int, str, str]:
    normalized_name = str(product_name or "").strip() or "Producto sin nombre"

    cursor.execute(
        f"""
        SELECT TOP 1 product_id, product_code, product_name
        FROM {PRODUCTS_TABLE}
        WHERE product_name = ?
           OR product_code = ?
        ORDER BY product_id ASC
        """,
        normalized_name,
        _compact_code(normalized_name, prefix="PRD"),
    )
    row = cursor.fetchone()
    if row is not None:
        return int(row[0]), str(row[1]), str(row[2])

    product_code = _compact_code(normalized_name, prefix="PRD")
    cursor.execute(
        f"""
        INSERT INTO {PRODUCTS_TABLE} (product_code, product_name, unit_of_measure)
        OUTPUT INSERTED.product_id
        VALUES (?, ?, ?)
        """,
        product_code,
        normalized_name,
        "BOX",
    )
    created_row = cursor.fetchone()
    if created_row is None:
        raise RuntimeError("Could not create product")

    return int(created_row[0]), product_code, normalized_name


def _ensure_employee(cursor, *, employee_code: str, full_name: str, line: str) -> None:
    normalized_code = _normalize_employee_code(employee_code)
    if not normalized_code:
        raise ValueError("employee_code is required")

    normalized_name = str(full_name or "").strip() or f"Empleado {normalized_code}"
    normalized_line = str(line or "").strip().upper() or "L07"
    role = f"OPERATOR {normalized_line}"

    current_id = _scalar(
        cursor,
        f"SELECT employee_id FROM {EMPLOYEES_TABLE} WHERE employee_code = ?",
        normalized_code,
    )

    if current_id is None:
        cursor.execute(
            f"""
            INSERT INTO {EMPLOYEES_TABLE} (employee_code, full_name, role, is_active)
            VALUES (?, ?, ?, 1)
            """,
            normalized_code,
            normalized_name,
            role,
        )
        return

    cursor.execute(
        f"""
        UPDATE {EMPLOYEES_TABLE}
        SET full_name = ?, role = ?, is_active = 1
        WHERE employee_id = ?
        """,
        normalized_name,
        role,
        int(current_id),
    )


def _ensure_lot(cursor, *, lot_code: str, product_id: int) -> str:
    normalized_lot_code = str(lot_code or "").strip().upper()
    if not normalized_lot_code:
        normalized_lot_code = _default_lot_code("L07")

    existing_lot_id = _scalar(
        cursor,
        f"SELECT lot_id FROM {LOTS_TABLE} WHERE lot_code = ?",
        normalized_lot_code,
    )
    if existing_lot_id is not None:
        return normalized_lot_code

    raise ValueError(
        f"lot not found: {normalized_lot_code}. Create the lot from reception before registering production boxes."
    )


def fetch_production_employees() -> list[dict]:
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            SELECT employee_code, full_name, role
            FROM {EMPLOYEES_TABLE}
            WHERE is_active = 1
            ORDER BY employee_code ASC
            """
        )
        rows = _rows_to_dicts(cursor)

        employees: list[dict] = []
        for row in rows:
            employees.append(
                {
                    "code": str(row.get("employee_code", "")).strip(),
                    "name": str(row.get("full_name", "")).strip(),
                    "line": _line_from_role(str(row.get("role", ""))),
                    "goal": 200,
                }
            )
        return employees
    finally:
        connection.close()


def fetch_production_rows(limit: int = 250) -> list[dict]:
    safe_limit = max(1, min(_safe_int(limit, 250), 5000))

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            SELECT TOP ({safe_limit})
                b.produced_at,
                b.box_code,
                e.employee_code,
                e.full_name,
                b.production_line,
                p.product_name,
                ISNULL(rd.variety, 'N/D') AS variety,
                b.presentation,
                l.lot_code,
                b.net_weight_kg,
                b.status
            FROM {BOXES_TABLE} AS b
            INNER JOIN {EMPLOYEES_TABLE} AS e ON e.employee_id = b.employee_id
            INNER JOIN {PRODUCTS_TABLE} AS p ON p.product_id = b.product_id
            INNER JOIN {LOTS_TABLE} AS l ON l.lot_id = b.lot_id
            LEFT JOIN {RECEPTION_DETAILS_TABLE} AS rd ON rd.reception_detail_id = l.reception_detail_id
            ORDER BY b.produced_at DESC, b.box_id DESC
            """
        )

        rows = _rows_to_dicts(cursor)
        payloads: list[dict] = []
        for row in rows:
            produced_at = row.get("produced_at")
            time_text = produced_at.strftime("%H:%M:%S") if isinstance(produced_at, datetime) else ""
            payloads.append(
                {
                    "time": time_text,
                    "box_id": str(row.get("box_code", "")).strip().upper(),
                    "employee_code": str(row.get("employee_code", "")).strip(),
                    "employee_name": str(row.get("full_name", "")).strip(),
                    "line": str(row.get("production_line", "")).strip().upper() or "L07",
                    "product": str(row.get("product_name", "")).strip() or "N/D",
                    "variety": str(row.get("variety", "")).strip() or "N/D",
                    "presentation": str(row.get("presentation", "")).strip().title() or "Medium",
                    "lot": str(row.get("lot_code", "")).strip().upper() or "Sin lote",
                    "weight_kg": _safe_float(row.get("net_weight_kg", 0.0)),
                    "status": str(row.get("status", "")).strip().title() or "Registrada",
                }
            )

        return payloads
    finally:
        connection.close()


def fetch_inventory_rows() -> list[dict]:
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            SELECT
                p.product_id,
                p.product_name,
                p.product_code,
                p.unit_of_measure,
                ISNULL(SUM(l.available_units), 0) AS available_units,
                ISNULL(SUM(l.available_weight_kg), 0) AS available_weight_kg
            FROM {PRODUCTS_TABLE} AS p
            LEFT JOIN {LOTS_TABLE} AS l ON l.product_id = p.product_id
            GROUP BY p.product_id, p.product_name, p.product_code, p.unit_of_measure
            ORDER BY p.product_name ASC
            """
        )

        rows = _rows_to_dicts(cursor)
        payloads: list[dict] = []
        for row in rows:
            stock_units = _safe_int(row.get("available_units"), 0)
            stock_weight_kg = _safe_float(row.get("available_weight_kg"), 0.0)

            if stock_units <= 0:
                status = "Out of Stock"
            elif stock_units < 25:
                status = "Low Stock"
            else:
                status = "In Stock"

            payloads.append(
                {
                    "id": _safe_int(row.get("product_id"), 0),
                    "name": str(row.get("product_name", "")).strip() or "Producto sin nombre",
                    "description": (
                        f"{str(row.get('product_code', '')).strip()} | "
                        f"{str(row.get('unit_of_measure', '')).strip()} | {stock_weight_kg:.1f} kg"
                    ),
                    "price": 0.0,
                    "stock": stock_units,
                    "status": status,
                }
            )

        return payloads
    finally:
        connection.close()


def fetch_reception_rows(limit: int = 300) -> list[dict]:
    safe_limit = max(1, min(_safe_int(limit, 300), 5000))

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            SELECT TOP ({safe_limit})
                r.reception_code,
                r.supplier_name,
                r.notes,
                ISNULL(l.lot_code, '') AS lot_code,
                p.product_name,
                rd.variety,
                rd.size,
                rd.received_units,
                rd.net_weight_kg,
                ISNULL((
                    SELECT TOP 1 pa.pallet_code
                    FROM {BOXES_TABLE} AS b2
                    INNER JOIN {PALLET_BOXES_TABLE} AS pb2 ON pb2.box_id = b2.box_id
                    INNER JOIN {PALLETS_TABLE} AS pa ON pa.pallet_id = pb2.pallet_id
                    WHERE b2.lot_id = l.lot_id
                    ORDER BY pb2.assigned_at DESC
                ), '') AS pallet_code
            FROM {RECEPTION_DETAILS_TABLE} AS rd
            INNER JOIN {RECEPTIONS_TABLE} AS r ON r.reception_id = rd.reception_id
            INNER JOIN {PRODUCTS_TABLE} AS p ON p.product_id = rd.product_id
            LEFT JOIN {LOTS_TABLE} AS l ON l.reception_detail_id = rd.reception_detail_id
            WHERE CAST(r.received_at AS date) = CAST(GETDATE() AS date)
            ORDER BY r.received_at DESC, rd.reception_detail_id DESC
            """
        )

        rows = _rows_to_dicts(cursor)
        payloads: list[dict] = []
        for row in rows:
            payloads.append(
                {
                    "receipt_id": str(row.get("reception_code", "")).strip(),
                    "lot": str(row.get("lot_code", "")).strip().upper() or "Sin lote",
                    "product": str(row.get("product_name", "")).strip(),
                    "variety": str(row.get("variety", "")).strip() or "N/D",
                    "field_block": _extract_field_block(
                        str(row.get("notes", "")),
                        str(row.get("supplier_name", "")),
                    ),
                    "bales": _safe_int(row.get("received_units"), 0),
                    "weight_kg": _safe_float(row.get("net_weight_kg"), 0.0),
                    "size": str(row.get("size", "")).strip() or "N/D",
                    "pallet": str(row.get("pallet_code", "")).strip().upper(),
                }
            )

        return payloads
    finally:
        connection.close()


def fetch_shipment_rows(limit: int = 300) -> list[dict]:
    safe_limit = max(1, min(_safe_int(limit, 300), 5000))

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            SELECT TOP ({safe_limit})
                s.shipment_code,
                s.destination_name,
                s.scheduled_departure,
                s.departed_at,
                s.arrival_eta,
                s.status,
                s.created_at,
                COALESCE(c.display_name, c.legal_name, c.client_code) AS client_name,
                ISNULL(cargo.crop, 'N/D') AS crop,
                ISNULL(cargo.lot, 'Sin lote') AS lot,
                ISNULL(stats.pallets, 0) AS pallets_count,
                ISNULL(stats.boxes, 0) AS boxes_count
            FROM {SHIPMENTS_TABLE} AS s
            INNER JOIN {CLIENTS_TABLE} AS c ON c.client_id = s.client_id
            OUTER APPLY (
                SELECT TOP 1
                    pr.product_name AS crop,
                    l.lot_code AS lot
                FROM {SHIPMENT_PALLETS_TABLE} AS sp
                INNER JOIN {PALLET_BOXES_TABLE} AS pb ON pb.pallet_id = sp.pallet_id
                INNER JOIN {BOXES_TABLE} AS b ON b.box_id = pb.box_id
                INNER JOIN {LOTS_TABLE} AS l ON l.lot_id = b.lot_id
                INNER JOIN {PRODUCTS_TABLE} AS pr ON pr.product_id = b.product_id
                WHERE sp.shipment_id = s.shipment_id
                ORDER BY sp.loaded_at DESC
            ) AS cargo
            OUTER APPLY (
                SELECT
                    COUNT(DISTINCT sp2.pallet_id) AS pallets,
                    COUNT(pb2.box_id) AS boxes
                FROM {SHIPMENT_PALLETS_TABLE} AS sp2
                LEFT JOIN {PALLET_BOXES_TABLE} AS pb2 ON pb2.pallet_id = sp2.pallet_id
                WHERE sp2.shipment_id = s.shipment_id
            ) AS stats
            ORDER BY COALESCE(s.departed_at, s.scheduled_departure, s.created_at) DESC, s.shipment_id DESC
            """
        )

        rows = _rows_to_dicts(cursor)
        payloads: list[dict] = []
        for row in rows:
            departure_value = row.get("departed_at") or row.get("scheduled_departure")
            payloads.append(
                {
                    "id": str(row.get("shipment_code", "")).strip(),
                    "client": str(row.get("client_name", "")).strip() or "Cliente",
                    "crop": str(row.get("crop", "")).strip() or "N/D",
                    "lot": str(row.get("lot", "")).strip() or "Sin lote",
                    "origin": "Planta EMINENT",
                    "destination": str(row.get("destination_name", "")).strip() or "Destino pendiente",
                    "departure": _time_label(departure_value),
                    "eta": _time_label(row.get("arrival_eta")),
                    "status": _shipment_status_to_ui(str(row.get("status", ""))),
                    "pallets": _safe_int(row.get("pallets_count"), 0),
                    "boxes": _safe_int(row.get("boxes_count"), 0),
                    "created_at": row.get("created_at"),
                }
            )
        return payloads
    finally:
        connection.close()


def fetch_shipment_manifest_rows(limit: int = 300) -> list[dict]:
    rows = fetch_shipment_rows(limit=limit)
    payloads: list[dict] = []

    for row in rows:
        shipment_id = str(row.get("id", "")).strip()
        if not shipment_id:
            continue

        if shipment_id.startswith("SHP-"):
            manifest_id = shipment_id.replace("SHP-", "EMB-", 1)
        else:
            manifest_id = f"EMB-{shipment_id}"

        status = _shipment_status_to_manifest(str(row.get("status", "")))

        payloads.append(
            {
                "manifest_id": manifest_id,
                "shipment_id": shipment_id,
                "carrier": "EMINENT Logistics",
                "driver": "Pendiente",
                "vehicle": "Pendiente",
                "doc_type": "Outbound",
                "issued_at": str(row.get("departure", "")).strip() or datetime.now().strftime("%H:%M"),
                "status": status,
            }
        )

    return payloads


def fetch_dashboard_snapshot() -> dict[str, float]:
    connection = get_connection()
    try:
        cursor = connection.cursor()

        boxes_today = _scalar(
            cursor,
            f"""
            SELECT COUNT(*)
            FROM {BOXES_TABLE}
            WHERE CAST(produced_at AS date) = CAST(SYSUTCDATETIME() AS date)
            """,
        )

        pallets_total = _scalar(cursor, f"SELECT COUNT(*) FROM {PALLETS_TABLE}")

        shipments_active = _scalar(
            cursor,
            f"""
            SELECT COUNT(*)
            FROM {SHIPMENTS_TABLE}
            WHERE status IN ('READY', 'IN_TRANSIT')
            """,
        )

        weight_today = _scalar(
            cursor,
            f"""
            SELECT ISNULL(SUM(net_weight_kg), 0)
            FROM {BOXES_TABLE}
            WHERE CAST(produced_at AS date) = CAST(SYSUTCDATETIME() AS date)
            """,
        )

        return {
            "boxes_today": float(_safe_int(boxes_today, 0)),
            "pallets_total": float(_safe_int(pallets_total, 0)),
            "shipments_active": float(_safe_int(shipments_active, 0)),
            "weight_today_kg": float(_safe_float(weight_today, 0.0)),
        }
    finally:
        connection.close()


def fetch_dashboard_client_pallet_rows(limit: int = 4) -> list[tuple[str, int]]:
    safe_limit = max(1, min(_safe_int(limit, 4), 20))

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            SELECT TOP ({safe_limit})
                COALESCE(c.display_name, c.legal_name, c.client_code) AS client_name,
                COUNT(DISTINCT sp.pallet_id) AS pallet_count
            FROM {SHIPMENTS_TABLE} AS s
            INNER JOIN {CLIENTS_TABLE} AS c ON c.client_id = s.client_id
            LEFT JOIN {SHIPMENT_PALLETS_TABLE} AS sp ON sp.shipment_id = s.shipment_id
            GROUP BY COALESCE(c.display_name, c.legal_name, c.client_code)
            ORDER BY pallet_count DESC, client_name ASC
            """
        )

        rows = _rows_to_dicts(cursor)
        return [(str(row["client_name"]), _safe_int(row["pallet_count"], 0)) for row in rows]
    finally:
        connection.close()


def fetch_dashboard_trend_points() -> list[tuple[str, int]]:
    checkpoints = [0, 3, 9, 12, 15, 18]

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            SELECT
                DATEPART(HOUR, produced_at) AS produced_hour,
                COUNT(*) AS boxes_count
            FROM {BOXES_TABLE}
            WHERE CAST(produced_at AS date) = CAST(SYSUTCDATETIME() AS date)
            GROUP BY DATEPART(HOUR, produced_at)
            """
        )

        rows = _rows_to_dicts(cursor)
        by_hour: dict[int, int] = {int(row["produced_hour"]): _safe_int(row["boxes_count"], 0) for row in rows}

        cumulative_points: list[tuple[str, int]] = []
        for hour in checkpoints:
            cumulative = 0
            for key_hour, value in by_hour.items():
                if key_hour <= hour:
                    cumulative += value
            cumulative_points.append((f"{hour:02d}:00", cumulative))

        return cumulative_points
    finally:
        connection.close()


def fetch_dashboard_alert_rows() -> list[dict]:
    connection = get_connection()
    try:
        cursor = connection.cursor()

        incomplete_pallets = _scalar(
            cursor,
            f"""
            SELECT COUNT(*)
            FROM {PALLETS_TABLE}
            WHERE status IN ('OPEN', 'LOADED')
            """,
        )

        boxes_without_label = _scalar(
            cursor,
            f"""
            SELECT COUNT(*)
            FROM {BOXES_TABLE}
            WHERE status = 'CREATED'
            """,
        )

        return [
            {"label": "Incomplete Pallets", "count": _safe_int(incomplete_pallets, 0)},
            {"label": "Boxes Without Label", "count": _safe_int(boxes_without_label, 0)},
            {"label": "Duplicates Detected", "count": 0},
        ]
    finally:
        connection.close()


def fetch_dashboard_shipments_today_rows(limit: int = 12) -> list[dict]:
    rows = fetch_shipment_rows(limit=limit)

    payloads: list[dict] = []
    for row in rows:
        status = str(row.get("status", "")).strip()
        dashboard_status = "Closed" if status == "Delivered" else "In Progress"

        payloads.append(
            {
                "shipment_id": str(row.get("id", "")).strip(),
                "client": str(row.get("client", "")).strip() or "Cliente",
                "pallets": _safe_int(row.get("pallets"), 0),
                "boxes": _safe_int(row.get("boxes"), 0),
                "status": dashboard_status,
            }
        )

    return payloads


def persist_reception_entry(
    *,
    reception_code: str,
    supplier_name: str,
    notes: str,
    supplier_reference: str,
    lot_code: str,
    product_name: str,
    variety: str,
    field_block: str,
    bales: int,
    size: str,
    weight_lb_per_bale: float,
) -> dict:
    normalized_reception_code = str(reception_code or "").strip().upper()
    if not normalized_reception_code:
        normalized_reception_code = f"REC-{datetime.now():%y%m%d}-{uuid.uuid4().hex[:3].upper()}"

    normalized_supplier = str(supplier_name or "").strip() or "Proveedor sin nombre"
    normalized_reference = str(supplier_reference or "").strip() or None
    normalized_lot = str(lot_code or "").strip().upper() or f"LOT-{datetime.utcnow():%y%m%d}-{uuid.uuid4().hex[:4].upper()}"
    normalized_product = str(product_name or "").strip() or "Producto sin nombre"
    normalized_variety = str(variety or "").strip() or "N/D"
    normalized_size = str(size or "").strip() or "N/D"
    normalized_field = str(field_block or "").strip()

    bales_value = max(1, _safe_int(bales, 1))
    weight_lb_value = max(0.01, _safe_float(weight_lb_per_bale, 0.01))
    total_weight_kg = bales_value * weight_lb_value * 0.45359237

    connection = get_connection()
    try:
        cursor = connection.cursor()

        product_id, _, product_label = _fetch_or_create_product(cursor, normalized_product)

        reception_id = _scalar(
            cursor,
            f"SELECT reception_id FROM {RECEPTIONS_TABLE} WHERE reception_code = ?",
            normalized_reception_code,
        )

        if reception_id is None:
            cursor.execute(
                f"""
                INSERT INTO {RECEPTIONS_TABLE} (
                    reception_code,
                    supplier_name,
                    supplier_reference,
                    received_at,
                    status,
                    notes
                )
                OUTPUT INSERTED.reception_id
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                normalized_reception_code,
                normalized_supplier,
                normalized_reference,
                datetime.utcnow(),
                "OPEN",
                _compose_reception_notes(normalized_field, notes),
            )
            created_row = cursor.fetchone()
            if created_row is None:
                raise RuntimeError("Could not create reception")
            reception_id = int(created_row[0])

        next_line = _scalar(
            cursor,
            f"SELECT ISNULL(MAX(line_no), 0) + 1 FROM {RECEPTION_DETAILS_TABLE} WHERE reception_id = ?",
            int(reception_id),
        )
        line_no = _safe_int(next_line, 1)

        cursor.execute(
            f"""
            INSERT INTO {RECEPTION_DETAILS_TABLE} (
                reception_id,
                line_no,
                product_id,
                variety,
                size,
                package_type,
                received_units,
                gross_weight_kg,
                net_weight_kg
            )
            OUTPUT INSERTED.reception_detail_id
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            int(reception_id),
            line_no,
            int(product_id),
            normalized_variety,
            normalized_size,
            "BOX",
            bales_value,
            total_weight_kg,
            total_weight_kg,
        )
        detail_row = cursor.fetchone()
        if detail_row is None:
            raise RuntimeError("Could not create reception detail")
        detail_id = int(detail_row[0])

        existing_lot_id = _scalar(
            cursor,
            f"SELECT lot_id FROM {LOTS_TABLE} WHERE lot_code = ?",
            normalized_lot,
        )

        if existing_lot_id is None:
            cursor.execute(
                f"""
                INSERT INTO {LOTS_TABLE} (
                    lot_code,
                    reception_detail_id,
                    product_id,
                    harvest_date,
                    status,
                    available_units,
                    available_weight_kg
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                normalized_lot,
                detail_id,
                int(product_id),
                datetime.utcnow().date(),
                "OPEN",
                bales_value,
                total_weight_kg,
            )
        else:
            cursor.execute(
                f"""
                UPDATE {LOTS_TABLE}
                SET
                    available_units = available_units + ?,
                    available_weight_kg = available_weight_kg + ?,
                    status = 'OPEN',
                    updated_at = SYSUTCDATETIME()
                WHERE lot_id = ?
                """,
                bales_value,
                total_weight_kg,
                int(existing_lot_id),
            )

        connection.commit()

        return {
            "receipt_id": normalized_reception_code,
            "lot": normalized_lot,
            "product": product_label,
            "variety": normalized_variety,
            "field_block": normalized_field or normalized_supplier,
            "bales": bales_value,
            "weight_kg": total_weight_kg,
            "size": normalized_size,
            "pallet": "",
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def persist_production_scan(
    *,
    row_payload: dict,
    pallet_code: str | None = None,
    pallet_position: int | None = None,
) -> dict:
    box_code = str(row_payload.get("box_id", "")).strip().upper()
    employee_code = _normalize_employee_code(str(row_payload.get("employee_code", "")))
    employee_name = str(row_payload.get("employee_name", "")).strip() or f"Empleado {employee_code}"
    line = str(row_payload.get("line", "")).strip().upper() or "L07"
    product_name = str(row_payload.get("product", "")).strip() or "Producto generico"
    lot_code = str(row_payload.get("lot", "")).strip().upper()
    presentation = str(row_payload.get("presentation", "")).strip().title() or "Medium"
    net_weight_kg = max(0.1, _safe_float(row_payload.get("weight_kg", 0.0), 0.0))

    if not box_code:
        raise ValueError("box_id is required")
    if not employee_code:
        raise ValueError("employee_code is required")

    if not lot_code or lot_code.upper() in {"SIN LOTE", "SIN LOTE ASIGNADO"}:
        lot_code = _default_lot_code(line)

    connection = get_connection()
    try:
        cursor = connection.cursor()

        _ensure_employee(
            cursor,
            employee_code=employee_code,
            full_name=employee_name,
            line=line,
        )

        product_id, product_code, _ = _fetch_or_create_product(cursor, product_name)
        lot_code = _ensure_lot(cursor, lot_code=lot_code, product_id=product_id)

        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    units_map = {"Jumbo": 24, "Medium": 28, "Small": 32}
    units_per_box = units_map.get(presentation, 24)
    gross_weight_kg = round(net_weight_kg + 0.35, 3)

    box_id: int
    created = False
    try:
        box_id = register_box(
            box_code=box_code,
            lot_code=lot_code,
            employee_code=employee_code,
            product_code=product_code,
            production_line=line,
            presentation=presentation,
            units_per_box=units_per_box,
            gross_weight_kg=gross_weight_kg,
            net_weight_kg=net_weight_kg,
            produced_at=datetime.utcnow(),
            status="CREATED",
        )
        created = True
    except ValueError as exc:
        if "box_code already exists" not in str(exc):
            raise

        current = get_box_by_code(box_code)
        if current is None:
            raise
        box_id = _safe_int(current.get("box_id"), 0)

    pallet_assigned = False
    if pallet_code and pallet_position and pallet_position > 0:
        try:
            assign_box_to_pallet(
                pallet_code=str(pallet_code).strip().upper(),
                box_code=box_code,
                position_index=int(pallet_position),
                assembled_by_employee_code=employee_code,
            )
            pallet_assigned = True
        except ValueError as exc:
            if "already assigned" not in str(exc) and "position already occupied" not in str(exc):
                raise

    return {
        "box_id": box_id,
        "box_code": box_code,
        "created": created,
        "pallet_assigned": pallet_assigned,
    }


def fetch_current_pallet_rows(pallet_code: str) -> list[dict]:
    code = str(pallet_code or "").strip().upper()
    if not code:
        return []

    rows = fetch_pallet_boxes(code)
    payloads: list[dict] = []
    for index, row in enumerate(rows, start=1):
        assigned_at = row.get("assigned_at")
        time_text = assigned_at.strftime("%H:%M:%S") if isinstance(assigned_at, datetime) else ""
        payloads.append(
            {
                "seq": index,
                "box_id": str(row.get("box_code", "")).strip().upper(),
                "time": time_text,
                "action": "Quitar",
            }
        )
    return payloads


def fetch_completed_pallets(limit: int = 60) -> list[dict]:
    safe_limit = max(1, min(_safe_int(limit, 60), 200))

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            SELECT TOP ({safe_limit})
                p.pallet_code,
                COALESCE((
                    SELECT TOP 1 b.presentation
                    FROM {PALLET_BOXES_TABLE} AS pb1
                    INNER JOIN {BOXES_TABLE} AS b ON b.box_id = pb1.box_id
                    WHERE pb1.pallet_id = p.pallet_id
                    ORDER BY pb1.assigned_at DESC
                ), 'N/D') AS presentation,
                ISNULL((
                    SELECT COUNT(*)
                    FROM {PALLET_BOXES_TABLE} AS pb2
                    WHERE pb2.pallet_id = p.pallet_id
                ), 0) AS boxes_count,
                p.closed_at,
                p.built_at
            FROM {PALLETS_TABLE} AS p
            WHERE p.status IN ('CLOSED', 'SHIPPED')
            ORDER BY COALESCE(p.closed_at, p.built_at) DESC, p.pallet_id DESC
            """
        )

        rows = _rows_to_dicts(cursor)
        payloads: list[dict] = []
        for row in rows:
            closed_value = row.get("closed_at") or row.get("built_at")
            closed_text = _time_label(closed_value)
            payloads.append(
                {
                    "pallet_id": str(row.get("pallet_code", "")).strip().upper(),
                    "presentation": str(row.get("presentation", "")).strip().title() or "N/D",
                    "boxes": _safe_int(row.get("boxes_count"), 0),
                    "closed_at": closed_text,
                    "actions": "Ver",
                }
            )
        return payloads
    finally:
        connection.close()


def close_pallet(pallet_code: str) -> bool:
    normalized = str(pallet_code or "").strip().upper()
    if not normalized:
        return False

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            UPDATE {PALLETS_TABLE}
            SET
                status = 'CLOSED',
                closed_at = COALESCE(closed_at, SYSUTCDATETIME()),
                updated_at = SYSUTCDATETIME()
            WHERE pallet_code = ?
              AND status IN ('OPEN', 'LOADED')
            """,
            normalized,
        )
        updated_rows = int(cursor.rowcount or 0)
        connection.commit()
        return updated_rows > 0
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


# ---------------------------------------------------------------------------
# Pallet Manager — Catalog & Label functions
# ---------------------------------------------------------------------------

def fetch_all_pallets(include_inactive: bool = False) -> list[dict]:
    """Return all pallets for the catalog manager, optionally including inactive ones."""
    connection = get_connection()
    try:
        cursor = connection.cursor()

        inactive_filter = "" if include_inactive else "AND ISNULL(p.is_active, 1) = 1"

        cursor.execute(
            f"""
            SELECT
                p.pallet_id,
                p.pallet_code,
                p.status,
                ISNULL(p.is_active, 1) AS is_active,
                ISNULL(p.is_mixed, 0) AS is_mixed,
                p.lot_code,
                p.variety,
                p.presentation_override,
                p.notes,
                p.built_at,
                p.closed_at,
                ISNULL((
                    SELECT COUNT(*)
                    FROM {PALLET_BOXES_TABLE} AS pb
                    WHERE pb.pallet_id = p.pallet_id
                ), 0) AS boxes_count,
                COALESCE((
                    SELECT TOP 1 b.presentation
                    FROM {PALLET_BOXES_TABLE} AS pb2
                    INNER JOIN {BOXES_TABLE} AS b ON b.box_id = pb2.box_id
                    WHERE pb2.pallet_id = p.pallet_id
                    ORDER BY pb2.assigned_at DESC
                ), p.presentation_override, 'N/D') AS detected_presentation,
                ISNULL((
                    SELECT SUM(b2.net_weight_kg)
                    FROM {PALLET_BOXES_TABLE} AS pb3
                    INNER JOIN {BOXES_TABLE} AS b2 ON b2.box_id = pb3.box_id
                    WHERE pb3.pallet_id = p.pallet_id
                ), 0.0) AS total_weight_kg,
                ISNULL(e.employee_code, '') AS employee_code,
                ISNULL(e.name, '') AS employee_name
            FROM {PALLETS_TABLE} AS p
            LEFT JOIN {EMPLOYEES_TABLE} AS e ON e.employee_id = p.assembled_by_employee_id
            WHERE 1=1 {inactive_filter}
            ORDER BY p.pallet_id DESC
            """
        )
        rows = _rows_to_dicts(cursor)
        payloads: list[dict] = []
        for row in rows:
            built_value = row.get("built_at")
            built_text = _time_label(built_value)
            closed_value = row.get("closed_at")
            closed_text = _time_label(closed_value) if closed_value else "—"
            payloads.append(
                {
                    "pallet_id": _safe_int(row.get("pallet_id"), 0),
                    "pallet_code": str(row.get("pallet_code", "")).strip().upper(),
                    "status": str(row.get("status", "")).strip().upper(),
                    "is_active": bool(row.get("is_active", True)),
                    "is_mixed": bool(row.get("is_mixed", False)),
                    "lot_code": str(row.get("lot_code") or "").strip(),
                    "variety": str(row.get("variety") or "").strip(),
                    "presentation_override": str(row.get("presentation_override") or "").strip(),
                    "notes": str(row.get("notes") or "").strip(),
                    "detected_presentation": str(row.get("detected_presentation", "N/D")).strip().title(),
                    "boxes_count": _safe_int(row.get("boxes_count"), 0),
                    "total_weight_kg": float(row.get("total_weight_kg") or 0.0),
                    "built_at": built_text,
                    "closed_at": closed_text,
                    "employee_code": str(row.get("employee_code", "")).strip(),
                    "employee_name": str(row.get("employee_name", "")).strip(),
                }
            )
        return payloads
    finally:
        connection.close()


def fetch_pallet_label_data(pallet_code: str) -> dict | None:
    """Return full data for a pallet's printed label, or None if not found."""
    normalized = str(pallet_code or "").strip().upper()
    if not normalized:
        return None

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            SELECT
                p.pallet_id,
                p.pallet_code,
                p.status,
                ISNULL(p.is_mixed, 0) AS is_mixed,
                p.lot_code,
                p.variety,
                p.presentation_override,
                p.notes,
                p.built_at,
                p.closed_at,
                ISNULL((
                    SELECT COUNT(*)
                    FROM {PALLET_BOXES_TABLE} AS pb
                    WHERE pb.pallet_id = p.pallet_id
                ), 0) AS boxes_count,
                COALESCE((
                    SELECT TOP 1 b.presentation
                    FROM {PALLET_BOXES_TABLE} AS pb2
                    INNER JOIN {BOXES_TABLE} AS b ON b.box_id = pb2.box_id
                    WHERE pb2.pallet_id = p.pallet_id
                    ORDER BY pb2.assigned_at DESC
                ), p.presentation_override, 'N/D') AS detected_presentation,
                ISNULL((
                    SELECT SUM(b2.net_weight_kg)
                    FROM {PALLET_BOXES_TABLE} AS pb3
                    INNER JOIN {BOXES_TABLE} AS b2 ON b2.box_id = pb3.box_id
                    WHERE pb3.pallet_id = p.pallet_id
                ), 0.0) AS total_weight_kg,
                ISNULL(e.employee_code, '') AS employee_code,
                ISNULL(e.name, '') AS employee_name
            FROM {PALLETS_TABLE} AS p
            LEFT JOIN {EMPLOYEES_TABLE} AS e ON e.employee_id = p.assembled_by_employee_id
            WHERE p.pallet_code = ?
            """,
            normalized,
        )
        row = cursor.fetchone()
        if row is None:
            return None

        columns = [col[0] for col in cursor.description]
        data = dict(zip(columns, row))

        built_value = data.get("built_at")
        built_text = built_value.strftime("%Y-%m-%d") if isinstance(built_value, datetime) else ""

        return {
            "pallet_code": str(data.get("pallet_code", "")).strip().upper(),
            "status": str(data.get("status", "")).strip().upper(),
            "is_mixed": bool(data.get("is_mixed", False)),
            "lot_code": str(data.get("lot_code") or "").strip(),
            "variety": str(data.get("variety") or "").strip(),
            "presentation": str(data.get("detected_presentation") or data.get("presentation_override") or "N/D").strip().title(),
            "notes": str(data.get("notes") or "").strip(),
            "boxes_count": _safe_int(data.get("boxes_count"), 0),
            "total_weight_kg": float(data.get("total_weight_kg") or 0.0),
            "built_at": built_text,
            "employee_code": str(data.get("employee_code", "")).strip(),
            "employee_name": str(data.get("employee_name", "")).strip(),
        }
    finally:
        connection.close()


def deactivate_pallet(pallet_code: str) -> bool:
    """Soft-delete a pallet by setting is_active = 0. Never physically deletes."""
    normalized = str(pallet_code or "").strip().upper()
    if not normalized:
        return False

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            UPDATE {PALLETS_TABLE}
            SET is_active = 0,
                updated_at = SYSUTCDATETIME()
            WHERE pallet_code = ?
              AND ISNULL(is_active, 1) = 1
            """,
            normalized,
        )
        updated_rows = int(cursor.rowcount or 0)
        connection.commit()
        return updated_rows > 0
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def reactivate_pallet(pallet_code: str) -> bool:
    """Re-activate a previously deactivated pallet (sets is_active = 1)."""
    normalized = str(pallet_code or "").strip().upper()
    if not normalized:
        return False

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            UPDATE {PALLETS_TABLE}
            SET is_active = 1,
                updated_at = SYSUTCDATETIME()
            WHERE pallet_code = ?
              AND ISNULL(is_active, 1) = 0
            """,
            normalized,
        )
        updated_rows = int(cursor.rowcount or 0)
        connection.commit()
        return updated_rows > 0
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def update_pallet_info(
    pallet_code: str,
    *,
    variety: str | None = None,
    lot_code: str | None = None,
    presentation_override: str | None = None,
    is_mixed: bool | None = None,
    notes: str | None = None,
) -> bool:
    """Update editable metadata fields of a pallet."""
    normalized = str(pallet_code or "").strip().upper()
    if not normalized:
        return False

    connection = get_connection()
    try:
        cursor = connection.cursor()

        set_parts = ["updated_at = SYSUTCDATETIME()"]
        params: list = []

        if variety is not None:
            set_parts.append("variety = ?")
            params.append(str(variety).strip() or None)
        if lot_code is not None:
            set_parts.append("lot_code = ?")
            params.append(str(lot_code).strip() or None)
        if presentation_override is not None:
            set_parts.append("presentation_override = ?")
            params.append(str(presentation_override).strip() or None)
        if is_mixed is not None:
            set_parts.append("is_mixed = ?")
            params.append(1 if is_mixed else 0)
        if notes is not None:
            set_parts.append("notes = ?")
            params.append(str(notes).strip() or None)

        if len(set_parts) == 1:
            return False

        params.append(normalized)
        cursor.execute(
            f"UPDATE {PALLETS_TABLE} SET {', '.join(set_parts)} WHERE pallet_code = ?",
            *params,
        )
        updated_rows = int(cursor.rowcount or 0)
        connection.commit()
        return updated_rows > 0
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
