"""Diagnostics support for R6 Data Relay."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import CONF_API_TOKEN
from .coordinator import R6DataRelayConfigEntry

TO_REDACT = {CONF_API_TOKEN}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: R6DataRelayConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    return {
        "entry_data": async_redact_data(dict(entry.data), TO_REDACT),
        "teams": {
            str(team_id): asdict(team_data) for team_id, team_data in entry.runtime_data.data.items()
        },
    }
