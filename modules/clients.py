"""Client module backed by SQL Server."""

from __future__ import annotations

from db.connection import get_connection
from db.sql_names import qn


CLIENTS_TABLE = qn("clients")


def _rows_to_dicts(cursor) -> list[dict]:
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def create_client(
    *,
    client_code: str,
    legal_name: str,
    display_name: str | None = None,
    tax_id: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    status: str = "ACTIVE",
) -> int:
    normalized_code = client_code.strip().upper()
    normalized_legal_name = legal_name.strip()
    normalized_status = status.strip().upper()

    if not normalized_code:
        raise ValueError("client_code is required")
    if not normalized_legal_name:
        raise ValueError("legal_name is required")

    connection = get_connection()
    try:
        cursor = connection.cursor()

        cursor.execute(
            f"SELECT client_id FROM {CLIENTS_TABLE} WHERE client_code = ?",
            normalized_code,
        )
        if cursor.fetchone() is not None:
            raise ValueError(f"client_code already exists: {normalized_code}")

        cursor.execute(
            f"""
            INSERT INTO {CLIENTS_TABLE} (
                client_code,
                legal_name,
                display_name,
                tax_id,
                email,
                phone,
                status
            )
            OUTPUT INSERTED.client_id
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            normalized_code,
            normalized_legal_name,
            (display_name or "").strip() or None,
            (tax_id or "").strip() or None,
            (email or "").strip() or None,
            (phone or "").strip() or None,
            normalized_status,
        )

        created_row = cursor.fetchone()
        connection.commit()

        if created_row is None:
            raise RuntimeError("client insert did not return client_id")

        return int(created_row[0])
    finally:
        connection.close()


def get_client_by_code(client_code: str) -> dict | None:
    normalized_code = client_code.strip().upper()
    if not normalized_code:
        return None

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            SELECT
                client_id,
                client_code,
                legal_name,
                display_name,
                tax_id,
                email,
                phone,
                status,
                created_at,
                updated_at
            FROM {CLIENTS_TABLE}
            WHERE client_code = ?
            """,
            normalized_code,
        )

        rows = _rows_to_dicts(cursor)
        return rows[0] if rows else None
    finally:
        connection.close()


def fetch_clients(*, status: str | None = None) -> list[dict]:
    connection = get_connection()
    try:
        cursor = connection.cursor()

        if status is None:
            cursor.execute(
                f"""
                SELECT
                    client_id,
                    client_code,
                    legal_name,
                    display_name,
                    tax_id,
                    email,
                    phone,
                    status,
                    created_at,
                    updated_at
                FROM {CLIENTS_TABLE}
                ORDER BY legal_name ASC
                """
            )
        else:
            cursor.execute(
                f"""
                SELECT
                    client_id,
                    client_code,
                    legal_name,
                    display_name,
                    tax_id,
                    email,
                    phone,
                    status,
                    created_at,
                    updated_at
                FROM {CLIENTS_TABLE}
                WHERE status = ?
                ORDER BY legal_name ASC
                """,
                status.strip().upper(),
            )

        return _rows_to_dicts(cursor)
    finally:
        connection.close()
