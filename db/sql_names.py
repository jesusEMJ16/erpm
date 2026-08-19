"""Safe SQL identifier helpers for schema-qualified table names."""

from __future__ import annotations

import os
import re

from db.connection_manager import load_sqlserver_config


_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def validate_identifier(value: str, *, label: str) -> str:
    token = str(value or "").strip()
    if not _IDENTIFIER_RE.match(token):
        raise ValueError(f"Invalid {label}: {value}")
    return token


def get_schema_name() -> str:
    return validate_identifier(load_sqlserver_config().schema or os.getenv("SQLSERVER_SCHEMA", "erp"), label="schema")


def qn(table: str, schema: str | None = None) -> str:
    schema_name = validate_identifier(schema or get_schema_name(), label="schema")
    table_name = validate_identifier(table, label="table")
    return f"[{schema_name}].[{table_name}]"
