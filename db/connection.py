"""Backward-compatible import surface for SQL Server connections."""

from __future__ import annotations

from db.connection_manager import (
    DEFAULT_SQLSERVER_CONFIG,
    SqlServerConfig,
    build_connection_string,
    database_config_file_path,
    get_connection,
    load_sqlserver_config,
    normalize_sqlserver_config,
    reload_sqlserver_config,
    save_sqlserver_config,
    sqlserver_config_to_dict,
    test_sqlserver_connection,
    validate_sqlserver_config,
)


__all__ = [
    "DEFAULT_SQLSERVER_CONFIG",
    "SqlServerConfig",
    "build_connection_string",
    "database_config_file_path",
    "get_connection",
    "load_sqlserver_config",
    "normalize_sqlserver_config",
    "reload_sqlserver_config",
    "save_sqlserver_config",
    "sqlserver_config_to_dict",
    "test_sqlserver_connection",
    "validate_sqlserver_config",
]
