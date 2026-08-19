"""Local persistence for BLACKERP settings profiles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

DEFAULT_SETTINGS: dict[str, Any] = {
    "company_name": "EMINENT ERP",
    "site_code": "MAIN-HQ",
    "timezone": "America/Hermosillo",
    "language": "es-MX",
    "currency": "MXN",
    "startup_page": "dashboard",
    "chart_color_preset": "navy_forest",
    "table_density": "standard",
    "rows_per_page": 25,
    "live_refresh": True,
    "show_tooltips": True,
    "show_activity_badges": True,
    "auto_refresh_seconds": 30,
    "require_signoff": True,
    "strict_validation": True,
    "default_document": "embarque",
    "auto_generate_pdf": False,
    "session_timeout_minutes": 30,
    "lockout_attempts": 5,
    "allow_multi_session": False,
    "mask_sensitive_data": True,
    "desktop_alerts": True,
    "sound_alerts": False,
    "escalation_minutes": 20,
}


def default_settings() -> dict[str, Any]:
    return dict(DEFAULT_SETTINGS)


def settings_file_path() -> Path:
    project_root = Path(__file__).resolve().parents[2]
    return project_root / "tmp" / "settings.json"


def _coerce_value(key: str, value: Any) -> Any:
    default = DEFAULT_SETTINGS[key]

    if isinstance(default, bool):
        if isinstance(value, bool):
            return value
        return default

    if isinstance(default, int):
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        return default

    if isinstance(default, str):
        if isinstance(value, str) and value.strip():
            return value.strip()
        return default

    return default


def normalize_settings(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    normalized = default_settings()
    if not isinstance(payload, Mapping):
        return normalized

    for key in normalized:
        normalized[key] = _coerce_value(key, payload.get(key, normalized[key]))
    return normalized


def load_settings() -> dict[str, Any]:
    path = settings_file_path()
    if not path.exists():
        return default_settings()

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return default_settings()

    if not isinstance(payload, dict):
        return default_settings()
    return normalize_settings(payload)


def save_settings(payload: Mapping[str, Any]) -> Path:
    normalized = normalize_settings(payload)
    path = settings_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(normalized, indent=2, sort_keys=True), encoding="utf-8")
    return path