"""Pallet module backed by SQL Server."""

from __future__ import annotations

from db.connection import get_connection
from db.sql_names import qn


PALLETS_TABLE = qn("pallets")
PALLET_BOXES_TABLE = qn("pallet_boxes")
BOXES_TABLE = qn("boxes")
EMPLOYEES_TABLE = qn("employees")


def _fetch_row(cursor, query: str, *params):
    cursor.execute(query, *params)
    return cursor.fetchone()


def _fetch_scalar(cursor, query: str, *params):
    row = _fetch_row(cursor, query, *params)
    return None if row is None else row[0]


def _resolve_employee_id(cursor, employee_code: str | None) -> int | None:
    if not employee_code:
        return None

    normalized_code = employee_code.strip().upper()
    if not normalized_code:
        return None

    employee_id = _fetch_scalar(
        cursor,
        f"SELECT employee_id FROM {EMPLOYEES_TABLE} WHERE employee_code = ?",
        normalized_code,
    )
    if employee_id is None:
        raise ValueError(f"employee not found: {normalized_code}")

    return int(employee_id)


def _get_or_create_pallet(
    cursor,
    *,
    pallet_code: str,
    assembled_by_employee_code: str | None,
) -> int:
    normalized_code = pallet_code.strip().upper()

    pallet_row = _fetch_row(
        cursor,
        f"SELECT pallet_id, status FROM {PALLETS_TABLE} WHERE pallet_code = ?",
        normalized_code,
    )

    if pallet_row is not None:
        pallet_id = int(pallet_row[0])
        pallet_status = str(pallet_row[1]).strip().upper()

        if pallet_status in {"CLOSED", "SHIPPED"}:
            raise ValueError(f"pallet is not open for assignment: {normalized_code}")

        return pallet_id

    employee_id = _resolve_employee_id(cursor, assembled_by_employee_code)

    cursor.execute(
        f"""
        INSERT INTO {PALLETS_TABLE} (
            pallet_code,
            assembled_by_employee_id,
            status
        )
        OUTPUT INSERTED.pallet_id
        VALUES (?, ?, 'OPEN')
        """,
        normalized_code,
        employee_id,
    )

    created_row = cursor.fetchone()
    if created_row is None:
        raise RuntimeError("pallet insert did not return pallet_id")

    return int(created_row[0])


def assign_box_to_pallet(
    *,
    pallet_code: str,
    box_code: str,
    position_index: int,
    assembled_by_employee_code: str | None = None,
) -> int:
    normalized_box_code = box_code.strip().upper()
    normalized_pallet_code = pallet_code.strip().upper()

    if not normalized_box_code:
        raise ValueError("box_code is required")
    if not normalized_pallet_code:
        raise ValueError("pallet_code is required")
    if position_index <= 0:
        raise ValueError("position_index must be greater than zero")

    connection = get_connection()
    try:
        cursor = connection.cursor()

        box_row = _fetch_row(
            cursor,
            f"SELECT box_id, status FROM {BOXES_TABLE} WHERE box_code = ?",
            normalized_box_code,
        )
        if box_row is None:
            raise ValueError(f"box not found: {normalized_box_code}")

        box_id = int(box_row[0])

        already_assigned = _fetch_row(
            cursor,
            f"""
            SELECT p.pallet_code
            FROM {PALLET_BOXES_TABLE} AS pb
            INNER JOIN {PALLETS_TABLE} AS p ON p.pallet_id = pb.pallet_id
            WHERE pb.box_id = ?
            """,
            box_id,
        )
        if already_assigned is not None:
            raise ValueError(
                f"box already assigned to pallet: {normalized_box_code} -> {already_assigned[0]}"
            )

        pallet_id = _get_or_create_pallet(
            cursor,
            pallet_code=normalized_pallet_code,
            assembled_by_employee_code=assembled_by_employee_code,
        )

        occupied_position = _fetch_scalar(
            cursor,
            f"SELECT pallet_box_id FROM {PALLET_BOXES_TABLE} WHERE pallet_id = ? AND position_index = ?",
            pallet_id,
            int(position_index),
        )
        if occupied_position is not None:
            raise ValueError(
                f"position already occupied in pallet: {normalized_pallet_code} [{position_index}]"
            )

        # Check if this is the first box assigned to this pallet
        current_count = _fetch_scalar(
            cursor,
            f"SELECT COUNT(*) FROM {PALLET_BOXES_TABLE} WHERE pallet_id = ?",
            pallet_id,
        )
        if current_count == 0:
            box_details = _fetch_row(
                cursor,
                f"""
                SELECT l.lot_code, rd.variety
                FROM {BOXES_TABLE} AS b
                INNER JOIN {qn("lots")} AS l ON b.lot_id = l.lot_id
                LEFT JOIN {qn("reception_details")} AS rd ON l.reception_detail_id = rd.reception_detail_id
                WHERE b.box_id = ?
                """,
                box_id,
            )
            if box_details is not None:
                first_lot_code = box_details[0]
                first_variety = box_details[1]
                cursor.execute(
                    f"""
                    UPDATE {PALLETS_TABLE}
                    SET lot_code = ?, variety = ?, updated_at = SYSUTCDATETIME()
                    WHERE pallet_id = ?
                    """,
                    first_lot_code,
                    first_variety,
                    pallet_id,
                )

        cursor.execute(
            f"""
            INSERT INTO {PALLET_BOXES_TABLE} (
                pallet_id,
                box_id,
                position_index
            )
            OUTPUT INSERTED.pallet_box_id
            VALUES (?, ?, ?)
            """,
            pallet_id,
            box_id,
            int(position_index),
        )

        created_row = cursor.fetchone()
        if created_row is None:
            raise RuntimeError("pallet box insert did not return pallet_box_id")

        cursor.execute(
            f"UPDATE {BOXES_TABLE} SET status = 'PALLETIZED' WHERE box_id = ?",
            box_id,
        )

        connection.commit()
        return int(created_row[0])
    finally:
        connection.close()


def fetch_pallet_boxes(pallet_code: str) -> list[dict]:
    normalized_code = pallet_code.strip().upper()
    if not normalized_code:
        return []

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            SELECT
                p.pallet_code,
                pb.position_index,
                b.box_code,
                b.presentation,
                b.net_weight_kg,
                b.status,
                pb.assigned_at
            FROM {PALLET_BOXES_TABLE} AS pb
            INNER JOIN {PALLETS_TABLE} AS p ON p.pallet_id = pb.pallet_id
            INNER JOIN {BOXES_TABLE} AS b ON b.box_id = pb.box_id
            WHERE p.pallet_code = ?
            ORDER BY pb.position_index ASC
            """,
            normalized_code,
        )

        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        connection.close()
