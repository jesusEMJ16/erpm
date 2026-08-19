"""Box registration module backed by SQL Server."""

from __future__ import annotations

from datetime import datetime

from db.connection import get_connection
from db.sql_names import qn


BOXES_TABLE = qn("boxes")
LOTS_TABLE = qn("lots")
EMPLOYEES_TABLE = qn("employees")
PRODUCTS_TABLE = qn("products")


def _fetch_scalar(cursor, query: str, *params):
    cursor.execute(query, *params)
    row = cursor.fetchone()
    return None if row is None else row[0]


def register_box(
    *,
    box_code: str,
    lot_code: str,
    employee_code: str,
    product_code: str,
    production_line: str,
    presentation: str,
    units_per_box: int,
    gross_weight_kg: float,
    net_weight_kg: float,
    produced_at: datetime | None = None,
    status: str = "CREATED",
) -> int:
    normalized_box_code = box_code.strip().upper()
    normalized_lot_code = lot_code.strip().upper()
    normalized_employee_code = employee_code.strip().upper()
    normalized_product_code = product_code.strip().upper()
    normalized_line = production_line.strip().upper()
    normalized_presentation = presentation.strip().title()
    normalized_status = status.strip().upper()

    if not normalized_box_code:
        raise ValueError("box_code is required")
    if units_per_box <= 0:
        raise ValueError("units_per_box must be greater than zero")
    if net_weight_kg <= 0:
        raise ValueError("net_weight_kg must be greater than zero")
    if gross_weight_kg < net_weight_kg:
        raise ValueError("gross_weight_kg must be greater than or equal to net_weight_kg")

    connection = get_connection()
    try:
        cursor = connection.cursor()

        existing_box = _fetch_scalar(
            cursor,
            f"SELECT box_id FROM {BOXES_TABLE} WHERE box_code = ?",
            normalized_box_code,
        )
        if existing_box is not None:
            raise ValueError(f"box_code already exists: {normalized_box_code}")

        lot_id = _fetch_scalar(
            cursor,
            f"SELECT lot_id FROM {LOTS_TABLE} WHERE lot_code = ?",
            normalized_lot_code,
        )
        if lot_id is None:
            raise ValueError(f"lot not found: {normalized_lot_code}")

        employee_id = _fetch_scalar(
            cursor,
            f"SELECT employee_id FROM {EMPLOYEES_TABLE} WHERE employee_code = ?",
            normalized_employee_code,
        )
        if employee_id is None:
            raise ValueError(f"employee not found: {normalized_employee_code}")

        product_id = _fetch_scalar(
            cursor,
            f"SELECT product_id FROM {PRODUCTS_TABLE} WHERE product_code = ?",
            normalized_product_code,
        )
        if product_id is None:
            raise ValueError(f"product not found: {normalized_product_code}")

        cursor.execute(
            f"""
            INSERT INTO {BOXES_TABLE} (
                box_code,
                lot_id,
                employee_id,
                product_id,
                production_line,
                presentation,
                units_per_box,
                gross_weight_kg,
                net_weight_kg,
                produced_at,
                status
            )
            OUTPUT INSERTED.box_id
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            normalized_box_code,
            int(lot_id),
            int(employee_id),
            int(product_id),
            normalized_line,
            normalized_presentation,
            int(units_per_box),
            float(gross_weight_kg),
            float(net_weight_kg),
            produced_at or datetime.utcnow(),
            normalized_status,
        )

        created_row = cursor.fetchone()
        connection.commit()

        if created_row is None:
            raise RuntimeError("box insert did not return box_id")

        return int(created_row[0])
    finally:
        connection.close()


def get_box_by_code(box_code: str) -> dict | None:
    normalized_box_code = box_code.strip().upper()
    if not normalized_box_code:
        return None

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            SELECT
                b.box_id,
                b.box_code,
                l.lot_code,
                e.employee_code,
                p.product_code,
                b.production_line,
                b.presentation,
                b.units_per_box,
                b.gross_weight_kg,
                b.net_weight_kg,
                b.produced_at,
                b.status
            FROM {BOXES_TABLE} AS b
            INNER JOIN {LOTS_TABLE} AS l ON l.lot_id = b.lot_id
            INNER JOIN {EMPLOYEES_TABLE} AS e ON e.employee_id = b.employee_id
            INNER JOIN {PRODUCTS_TABLE} AS p ON p.product_id = b.product_id
            WHERE b.box_code = ?
            """,
            normalized_box_code,
        )

        row = cursor.fetchone()
        if row is None:
            return None

        columns = [column[0] for column in cursor.description]
        return dict(zip(columns, row))
    finally:
        connection.close()
