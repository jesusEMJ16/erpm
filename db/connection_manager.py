"""Central SQL Server configuration and connection manager."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import pyodbc
from dotenv import load_dotenv


load_dotenv()


_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_CONFIG_CACHE: "SqlServerConfig | None" = None


@dataclass(frozen=True)
class SqlServerConfig:
    driver: str
    host: str
    port: int | None
    instance: str
    database: str
    schema: str
    user: str
    password: str
    trusted_connection: bool
    encrypt: bool
    trust_server_certificate: bool
    timeout: int


DEFAULT_SQLSERVER_CONFIG = SqlServerConfig(
    driver="ODBC Driver 18 for SQL Server",
    host="localhost",
    port=None,
    instance="",
    database="EMINENTERP",
    schema="erp",
    user="sa",
    password="change-me",
    trusted_connection=False,
    encrypt=True,
    trust_server_certificate=True,
    timeout=30,
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def database_config_file_path() -> Path:
    override = os.getenv("BLACKERP_DB_CONFIG_PATH", "").strip()
    if override:
        override_path = Path(override).expanduser()
        if override_path.is_absolute():
            return override_path
        return _project_root() / override_path

    return _project_root() / "tmp" / "database_settings.json"


def _parse_bool(raw_value: Any, default: bool) -> bool:
    if raw_value is None:
        return default

    normalized = str(raw_value).strip().lower()
    if normalized in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "f", "no", "n", "off"}:
        return False
    return default


def _parse_optional_port(raw_value: Any, default: int | None) -> int | None:
    if raw_value is None:
        return default

    text = str(raw_value).strip()
    if not text:
        return None

    try:
        return int(text)
    except (TypeError, ValueError):
        return default


def _parse_positive_int(raw_value: Any, default: int) -> int:
    if raw_value is None:
        return default

    try:
        parsed = int(str(raw_value).strip())
    except (TypeError, ValueError):
        return default

    return parsed if parsed > 0 else default


def _non_empty_string(raw_value: Any, default: str) -> str:
    text = str(raw_value or "").strip()
    return text or default


def _optional_string(raw_value: Any, default: str = "") -> str:
    if raw_value is None:
        return default
    return str(raw_value).strip()


def _first_value(payload: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in payload:
            return payload[key]
    return default


def _config_from_env(base: SqlServerConfig) -> SqlServerConfig:
    return SqlServerConfig(
        driver=_non_empty_string(os.getenv("SQLSERVER_DRIVER"), base.driver),
        host=_non_empty_string(os.getenv("SQLSERVER_HOST"), base.host),
        port=_parse_optional_port(os.getenv("SQLSERVER_PORT"), base.port),
        instance=_optional_string(os.getenv("SQLSERVER_INSTANCE"), base.instance),
        database=_non_empty_string(os.getenv("SQLSERVER_DATABASE"), base.database),
        schema=_non_empty_string(os.getenv("SQLSERVER_SCHEMA"), base.schema),
        user=_optional_string(os.getenv("SQLSERVER_USER"), base.user),
        password=_optional_string(os.getenv("SQLSERVER_PASSWORD"), base.password),
        trusted_connection=_parse_bool(os.getenv("SQLSERVER_TRUSTED_CONNECTION"), base.trusted_connection),
        encrypt=_parse_bool(os.getenv("SQLSERVER_ENCRYPT"), base.encrypt),
        trust_server_certificate=_parse_bool(
            os.getenv("SQLSERVER_TRUST_SERVER_CERTIFICATE"),
            base.trust_server_certificate,
        ),
        timeout=_parse_positive_int(os.getenv("SQLSERVER_CONNECTION_TIMEOUT"), base.timeout),
    )


def _read_json_payload(path: Path) -> Mapping[str, Any]:
    if not path.exists():
        return {}

    try:
        raw_payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {}

    if not isinstance(raw_payload, Mapping):
        return {}

    nested_payload = raw_payload.get("sql_server") or raw_payload.get("database")
    if isinstance(nested_payload, Mapping):
        return nested_payload

    return raw_payload


def normalize_sqlserver_config(
    payload: Mapping[str, Any] | SqlServerConfig | None,
    *,
    base: SqlServerConfig | None = None,
) -> SqlServerConfig:
    if isinstance(payload, SqlServerConfig):
        return payload

    source = base or DEFAULT_SQLSERVER_CONFIG
    if not isinstance(payload, Mapping):
        return source

    auth_type = str(_first_value(payload, "auth_type", "authentication", default="")).strip().lower()
    if auth_type in {"windows", "windows_auth", "trusted", "trusted_connection"}:
        trusted_connection = True
    elif auth_type in {"sql", "sql_server", "sql_auth", "sql_server_authentication"}:
        trusted_connection = False
    else:
        trusted_connection = _parse_bool(
            _first_value(payload, "trusted_connection", "windows_authentication", default=None),
            source.trusted_connection,
        )

    return SqlServerConfig(
        driver=_non_empty_string(_first_value(payload, "driver", default=None), source.driver),
        host=_non_empty_string(_first_value(payload, "host", "server", default=None), source.host),
        port=_parse_optional_port(_first_value(payload, "port", default=None), source.port),
        instance=_optional_string(_first_value(payload, "instance", default=None), source.instance),
        database=_non_empty_string(_first_value(payload, "database", "database_name", default=None), source.database),
        schema=_non_empty_string(_first_value(payload, "schema", default=None), source.schema),
        user=_optional_string(_first_value(payload, "user", "username", default=None), source.user),
        password=_optional_string(_first_value(payload, "password", default=None), source.password),
        trusted_connection=trusted_connection,
        encrypt=_parse_bool(_first_value(payload, "encrypt", default=None), source.encrypt),
        trust_server_certificate=_parse_bool(
            _first_value(payload, "trust_server_certificate", default=None),
            source.trust_server_certificate,
        ),
        timeout=_parse_positive_int(_first_value(payload, "timeout", "connection_timeout", default=None), source.timeout),
    )


def _load_sqlserver_config_from_sources() -> SqlServerConfig:
    env_config = _config_from_env(DEFAULT_SQLSERVER_CONFIG)
    return normalize_sqlserver_config(_read_json_payload(database_config_file_path()), base=env_config)


def load_sqlserver_config(*, use_cache: bool = True) -> SqlServerConfig:
    global _CONFIG_CACHE

    if use_cache and _CONFIG_CACHE is not None:
        return _CONFIG_CACHE

    config = _load_sqlserver_config_from_sources()
    if use_cache:
        _CONFIG_CACHE = config
    return config


def reload_sqlserver_config() -> SqlServerConfig:
    global _CONFIG_CACHE
    _CONFIG_CACHE = _load_sqlserver_config_from_sources()
    return _CONFIG_CACHE


def sqlserver_config_to_dict(config: SqlServerConfig, *, include_password: bool = True) -> dict[str, Any]:
    return {
        "driver": config.driver,
        "host": config.host,
        "instance": config.instance,
        "port": config.port,
        "database": config.database,
        "schema": config.schema,
        "auth_type": "windows" if config.trusted_connection else "sql_server",
        "user": "" if config.trusted_connection else config.user,
        "password": ("" if config.trusted_connection else config.password) if include_password else "",
        "encrypt": config.encrypt,
        "trust_server_certificate": config.trust_server_certificate,
        "timeout": config.timeout,
    }


def validate_sqlserver_config(config: SqlServerConfig) -> list[str]:
    errors: list[str] = []

    if not config.driver.strip():
        errors.append("ODBC driver is required.")
    if not config.host.strip():
        errors.append("SQL Server host is required.")
    if config.port is not None and not 1 <= int(config.port) <= 65535:
        errors.append("SQL Server port must be between 1 and 65535.")
    if not config.database.strip():
        errors.append("Database name is required.")
    if not _IDENTIFIER_RE.match(config.schema.strip()):
        errors.append("Schema must be a valid SQL identifier.")
    if config.timeout <= 0:
        errors.append("Connection timeout must be greater than zero.")
    if not config.trusted_connection:
        if not config.user.strip():
            errors.append("SQL Server user is required for SQL authentication.")
        if not config.password:
            errors.append("SQL Server password is required for SQL authentication.")

    return errors


def save_sqlserver_config(payload: Mapping[str, Any] | SqlServerConfig) -> Path:
    current_disk_config = load_sqlserver_config(use_cache=False)
    config = normalize_sqlserver_config(payload, base=current_disk_config)
    errors = validate_sqlserver_config(config)
    if errors:
        raise ValueError(" ".join(errors))

    path = database_config_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(sqlserver_config_to_dict(config), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


def _server_candidates(config: SqlServerConfig) -> list[str]:
    candidates: list[str] = []

    if config.instance:
        candidates.append(f"{config.host}\\{config.instance}")

    if config.port is not None:
        candidates.append(f"{config.host},{config.port}")

    candidates.append(config.host)

    unique_candidates: list[str] = []
    seen: set[str] = set()
    for server in candidates:
        token = server.strip()
        if not token or token in seen:
            continue
        seen.add(token)
        unique_candidates.append(token)

    return unique_candidates


def build_connection_string(config: SqlServerConfig | None = None, *, server: str | None = None) -> str:
    cfg = config or load_sqlserver_config()

    resolved_server = server or cfg.host
    parts = [
        f"DRIVER={{{cfg.driver}}}",
        f"SERVER={resolved_server}",
        f"DATABASE={cfg.database}",
        f"Encrypt={'yes' if cfg.encrypt else 'no'}",
        f"TrustServerCertificate={'yes' if cfg.trust_server_certificate else 'no'}",
    ]

    if cfg.trusted_connection:
        parts.append("Trusted_Connection=yes")
    else:
        parts.append(f"UID={cfg.user}")
        parts.append(f"PWD={cfg.password}")

    return ";".join(parts)


def _open_connection(
    config: SqlServerConfig | None = None,
    *,
    autocommit: bool = False,
) -> tuple[pyodbc.Connection, str]:
    cfg = config or load_sqlserver_config()
    last_error: Exception | None = None

    for server in _server_candidates(cfg):
        connection_string = build_connection_string(cfg, server=server)
        try:
            return (
                pyodbc.connect(
                    connection_string,
                    timeout=cfg.timeout,
                    autocommit=autocommit,
                ),
                server,
            )
        except pyodbc.Error as exc:
            last_error = exc

    if last_error is not None:
        raise last_error

    raise RuntimeError("No SQL Server endpoint candidates were generated")


def get_connection(
    *,
    autocommit: bool = False,
    config: SqlServerConfig | None = None,
) -> pyodbc.Connection:
    connection, _server = _open_connection(config=config, autocommit=autocommit)
    return connection


def test_sqlserver_connection(config: SqlServerConfig | None = None) -> dict[str, Any]:
    connection, server = _open_connection(config=config)
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT DB_NAME() AS database_name, @@SERVERNAME AS server_name")
        row = cursor.fetchone()
        return {
            "server": server,
            "database": None if row is None else row[0],
            "server_name": None if row is None else row[1],
        }
    finally:
        connection.close()

