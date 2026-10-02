"""Base entity for per-team R6 Data Relay entities."""

from __future__ import annotations

from typing import override

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import R6DataRelayDataUpdateCoordinator, TeamData


class R6DataRelayTeamEntity(CoordinatorEntity[R6DataRelayDataUpdateCoordinator]):
    """Base for entities backed by one enabled team, grouped as one device per team."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: R6DataRelayDataUpdateCoordinator, team_id: int) -> None:
        """Initialize the entity for the given PandaScore team id."""
        super().__init__(coordinator)
        self.team_id = team_id

    @property
    def team_data(self) -> TeamData:
        """Return the latest data for this entity's team."""
        return self.coordinator.data[self.team_id]

    @property
    @override
    def available(self) -> bool:
        """Return True while the team is still enabled in the latest refresh."""
        return super().available and self.team_id in self.coordinator.data

    @property
    @override
    def device_info(self) -> DeviceInfo:
        """Return device info, recomputed so a renamed team's device follows."""
        return DeviceInfo(
            identifiers={(DOMAIN, str(self.team_id))},
            name=self.team_data.team["name"],
            manufacturer="PandaScore",
            model="R6 Siege team",
        )
