"""Shared chart color presets for dashboard and production modules."""

from __future__ import annotations

import os
from typing import Any

from app.services.settings_store import load_settings

DEFAULT_CHART_PRESET = "navy_forest"

CHART_COLOR_PRESETS: dict[str, dict[str, Any]] = {
    "navy_forest": {
        "label": "Navy Forest (Premium)",
        "bars": ["#8B0000", "#0A3D91", "#0B6B36", "#6D7583"],
        "bar_alpha": 232,
        "trend": "#0F8D43",
        "trend_top_alpha": 85,
        "trend_mid_alpha": 45,
        "presentations": {
            "Jumbo": "#8B0000",
            "Medium": "#0A3D91",
            "Small": "#0B6B36",
        },
    },
    "deep_contrast": {
        "label": "Deep Contrast (Strong)",
        "bars": ["#A10000", "#123A78", "#0A5A2D", "#5C636E"],
        "bar_alpha": 236,
        "trend": "#0C7A39",
        "trend_top_alpha": 92,
        "trend_mid_alpha": 50,
        "presentations": {
            "Jumbo": "#A10000",
            "Medium": "#123A78",
            "Small": "#0A5A2D",
        },
    },
}

CHART_PRESET_OPTIONS = [
    ("navy_forest", CHART_COLOR_PRESETS["navy_forest"]["label"]),
    ("deep_contrast", CHART_COLOR_PRESETS["deep_contrast"]["label"]),
]


def normalize_chart_preset(value: str | None) -> str:
    token = str(value or "").strip().lower()
    if token in CHART_COLOR_PRESETS:
        return token
    return DEFAULT_CHART_PRESET


def resolve_chart_preset(preferred: str | None = None) -> str:
    env_preset = os.getenv("BLACKERP_DASHBOARD_CHART_PRESET", "").strip().lower()
    if env_preset in CHART_COLOR_PRESETS:
        return env_preset

    if preferred is not None and str(preferred).strip():
        return normalize_chart_preset(preferred)

    settings = load_settings()
    return normalize_chart_preset(settings.get("chart_color_preset", DEFAULT_CHART_PRESET))


def get_chart_palette(preferred: str | None = None) -> dict[str, Any]:
    preset_name = resolve_chart_preset(preferred)
    palette = dict(CHART_COLOR_PRESETS[preset_name])
    palette["name"] = preset_name
    return palette
