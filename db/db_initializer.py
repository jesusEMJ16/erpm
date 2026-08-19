"""Idempotent SQL Server initializer for ERP core tables."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from db.connection_manager import SqlServerConfig, get_connection
from db.sql_names import get_schema_name


LOGGER = logging.getLogger(__name__)
SCHEMA_SCRIPT_DIR = Path(__file__).resolve().parent / "schema"

TABLE_PLAN: tuple[tuple[str, str], ...] = (
    ("clients", "001_clients.sql"),
    ("employees", "002_employees.sql"),
    ("products", "003_products.sql"),
    ("receptions", "004_receptions.sql"),
    ("reception_details", "005_reception_details.sql"),
    ("lots", "006_lots.sql"),
    ("boxes", "007_boxes.sql"),
    ("pallets", "008_pallets.sql"),
    ("pallet_boxes", "009_pallet_boxes.sql"),
    ("shipments", "010_shipments.sql"),
    ("shipment_pallets", "011_shipment_pallets.sql"),
)


def _validate_identifier(name: str) -> str:
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
        raise ValueError(f"Invalid SQL identifier: {name}")
    return name


def _schema_exists(cursor, schema: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM sys.schemas WHERE name = ?",
        schema,
    )
    return cursor.fetchone() is not None


def _ensure_schema(cursor, schema: str) -> None:
    if _schema_exists(cursor, schema):
        return
    cursor.execute(f"CREATE SCHEMA [{schema}]")
    LOGGER.info("Created SQL Server schema: %s", schema)


def _table_exists(cursor, schema: str, table: str) -> bool:
    cursor.execute(
        """
        SELECT 1
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = ?
          AND TABLE_NAME = ?
        """,
        schema,
        table,
    )
    return cursor.fetchone() is not None


def _split_sql_batches(sql_text: str) -> list[str]:
    batches: list[str] = []
    current_batch: list[str] = []

    for line in sql_text.splitlines():
        if line.strip().upper() == "GO":
            batch = "\n".join(current_batch).strip()
            if batch:
                batches.append(batch)
            current_batch = []
            continue

        current_batch.append(line)

    final_batch = "\n".join(current_batch).strip()
    if final_batch:
        batches.append(final_batch)

    return batches


def _load_schema_script(script_name: str, schema: str) -> list[str]:
    script_path = SCHEMA_SCRIPT_DIR / script_name
    try:
        sql_text = script_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Could not read schema script: {script_path}") from exc

    rendered_sql = sql_text.replace("{{schema}}", schema)
    return _split_sql_batches(rendered_sql)


def _execute_schema_script(cursor, script_name: str, schema: str) -> None:
    for batch in _load_schema_script(script_name, schema):
        cursor.execute(batch)


def initialize_database(
    schema: str | None = None,
    *,
    config: SqlServerConfig | None = None,
) -> dict[str, list[str]]:
    schema_name = _validate_identifier(schema or (config.schema if config is not None else get_schema_name()))

    created: list[str] = []
    existing: list[str] = []

    connection = get_connection(config=config)
    try:
        cursor = connection.cursor()
        _ensure_schema(cursor, schema_name)

        for table_name, script_name in TABLE_PLAN:
            if _table_exists(cursor, schema_name, table_name):
                existing.append(table_name)
                if table_name == "pallets":
                    cursor.execute(
                        """
                        SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
                        WHERE TABLE_SCHEMA = ? AND TABLE_NAME = 'pallets' AND COLUMN_NAME = 'lot_code'
                        """,
                        schema_name,
                    )
                    if cursor.fetchone() is None:
                        cursor.execute(f"ALTER TABLE [{schema_name}].[pallets] ADD lot_code NVARCHAR(50) NULL")
                        LOGGER.info("Altered table %s.pallets to add lot_code column", schema_name)

                    cursor.execute(
                        """
                        SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
                        WHERE TABLE_SCHEMA = ? AND TABLE_NAME = 'pallets' AND COLUMN_NAME = 'variety'
                        """,
                        schema_name,
                    )
                    if cursor.fetchone() is None:
                        cursor.execute(f"ALTER TABLE [{schema_name}].[pallets] ADD variety NVARCHAR(120) NULL")
                        LOGGER.info("Altered table %s.pallets to add variety column", schema_name)

                    cursor.execute(
                        """
                        SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
                        WHERE TABLE_SCHEMA = ? AND TABLE_NAME = 'pallets' AND COLUMN_NAME = 'presentation_override'
                        """,
                        schema_name,
                    )
                    if cursor.fetchone() is None:
                        cursor.execute(f"ALTER TABLE [{schema_name}].[pallets] ADD presentation_override NVARCHAR(60) NULL")
                        LOGGER.info("Altered table %s.pallets to add presentation_override column", schema_name)

                    cursor.execute(
                        """
                        SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
                        WHERE TABLE_SCHEMA = ? AND TABLE_NAME = 'pallets' AND COLUMN_NAME = 'is_mixed'
                        """,
                        schema_name,
                    )
                    if cursor.fetchone() is None:
                        cursor.execute(f"ALTER TABLE [{schema_name}].[pallets] ADD is_mixed BIT NOT NULL DEFAULT (0)")
                        LOGGER.info("Altered table %s.pallets to add is_mixed column", schema_name)

                    cursor.execute(
                        """
                        SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
                        WHERE TABLE_SCHEMA = ? AND TABLE_NAME = 'pallets' AND COLUMN_NAME = 'is_active'
                        """,
                        schema_name,
                    )
                    if cursor.fetchone() is None:
                        cursor.execute(f"ALTER TABLE [{schema_name}].[pallets] ADD is_active BIT NOT NULL DEFAULT (1)")
                        LOGGER.info("Altered table %s.pallets to add is_active column", schema_name)

                    cursor.execute(
                        """
                        SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
                        WHERE TABLE_SCHEMA = ? AND TABLE_NAME = 'pallets' AND COLUMN_NAME = 'notes'
                        """,
                        schema_name,
                    )
                    if cursor.fetchone() is None:
                        cursor.execute(f"ALTER TABLE [{schema_name}].[pallets] ADD notes NVARCHAR(500) NULL")
                        LOGGER.info("Altered table %s.pallets to add notes column", schema_name)
                continue

            _execute_schema_script(cursor, script_name, schema_name)
            created.append(table_name)
            LOGGER.info("Created SQL Server table: %s.%s", schema_name, table_name)

        connection.commit()
    except Exception:
        connection.rollback()
        LOGGER.exception("SQL Server schema initialization failed for schema: %s", schema_name)
        raise
    finally:
        connection.close()

    return {
        "created": created,
        "existing": existing,
    }


def initialize_and_print(schema: str | None = None) -> None:
    result = initialize_database(schema=schema)

    print(f"Schema: {schema or get_schema_name()}")
    print(f"Created tables: {len(result['created'])}")
    for table_name in result["created"]:
        print(f"  + {table_name}")

    print(f"Existing tables: {len(result['existing'])}")
    for table_name in result["existing"]:
        print(f"  = {table_name}")


if __name__ == "__main__":
    initialize_and_print()
