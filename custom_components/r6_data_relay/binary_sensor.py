"""Binary sensor platform for R6 Data Relay: whether a team is playing right now."""

from __future__ import annotations

from typing import Any, override

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import R6DataRelayConfigEntry, R6DataRelayDataUpdateCoordinator
from .entity import R6DataRelayTeamEntity
from .sensor import match_attributes


async def async_setup_entry(
    hass: HomeAssistant,
    entry: R6DataRelayConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the live-match binary sensor for every enabled team."""
    coordinator = entry.runtime_data
    known_team_ids: set[int] = set()

    @callback
    def _async_add_new_entities() -> None:
        new_ids = set(coordinator.data) - known_team_ids
        if not new_ids:
            return
        known_team_ids.update(new_ids)
        async_add_entities(R6DataRelayLiveSensor(coordinator, team_id) for team_id in new_ids)

    _async_add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(_async_add_new_entities))


class R6DataRelayLiveSensor(R6DataRelayTeamEntity, BinarySensorEntity):
    """On while the team has a running match."""

    _attr_translation_key = "playing_now"

    def __init__(self, coordinator: R6DataRelayDataUpdateCoordinator, team_id: int) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, team_id)
        self._attr_unique_id = f"{team_id}_playing_now"

    @property
    @override
    def is_on(self) -> bool:
        """Return True if the team is currently in a running match."""
        return self.team_data.running_match is not None

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return details of the running match, if any."""
        return match_attributes(self.team_data.running_match, self.team_id)
