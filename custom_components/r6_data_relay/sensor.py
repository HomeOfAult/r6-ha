"""Sensor platform for R6 Data Relay: next match and last result per team."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, override

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import (
    R6DataRelayConfigEntry,
    R6DataRelayDataUpdateCoordinator,
    TeamData,
    match_end,
    match_start,
    opponent_of,
)
from .entity import R6DataRelayTeamEntity

RESULT_WIN = "win"
RESULT_LOSS = "loss"
RESULT_NO_RESULT = "no_result"


def match_attributes(match: dict[str, Any] | None, team_id: int) -> dict[str, Any]:
    """Describe a match from the point of view of `team_id`."""
    if match is None:
        return {}
    opponent = opponent_of(match, team_id) or {}
    return {
        "match_id": match.get("id"),
        "match_name": match.get("name"),
        "match_status": match.get("status"),
        "opponent": opponent.get("name"),
        "opponent_acronym": opponent.get("acronym"),
        "opponent_image_url": opponent.get("image_url"),
        "league": (match.get("league") or {}).get("name"),
        "serie": (match.get("serie") or {}).get("name"),
        "tournament": (match.get("tournament") or {}).get("name"),
    }


def _next_match_value(data: TeamData) -> datetime | None:
    return match_start(data.next_match) if data.next_match else None


def _last_result_value(data: TeamData) -> str | None:
    match = data.last_match
    if match is None:
        return None
    winner_id = match.get("winner_id")
    if winner_id is None:
        return RESULT_NO_RESULT
    return RESULT_WIN if winner_id == data.team["id"] else RESULT_LOSS


def _last_result_attributes(data: TeamData) -> dict[str, Any]:
    attrs = match_attributes(data.last_match, data.team["id"])
    if data.last_match is not None:
        ended = match_end(data.last_match)
        attrs["ended_at"] = ended.isoformat() if ended else None
    return attrs


@dataclass(frozen=True, kw_only=True)
class R6DataRelaySensorEntityDescription(SensorEntityDescription):
    """Describes a per-team relay sensor."""

    value_fn: Callable[[TeamData], datetime | str | None]
    attributes_fn: Callable[[TeamData], dict[str, Any]]


SENSORS: tuple[R6DataRelaySensorEntityDescription, ...] = (
    R6DataRelaySensorEntityDescription(
        key="next_match",
        translation_key="next_match",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_next_match_value,
        attributes_fn=lambda data: match_attributes(data.next_match, data.team["id"]),
    ),
    R6DataRelaySensorEntityDescription(
        key="last_result",
        translation_key="last_result",
        device_class=SensorDeviceClass.ENUM,
        options=[RESULT_WIN, RESULT_LOSS, RESULT_NO_RESULT],
        value_fn=_last_result_value,
        attributes_fn=_last_result_attributes,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: R6DataRelayConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up relay sensors for every enabled team, including ones enabled later."""
    coordinator = entry.runtime_data
    known_team_ids: set[int] = set()

    @callback
    def _async_add_new_entities() -> None:
        new_ids = set(coordinator.data) - known_team_ids
        if not new_ids:
            return
        known_team_ids.update(new_ids)
        async_add_entities(
            R6DataRelaySensor(coordinator, team_id, description)
            for team_id in new_ids
            for description in SENSORS
        )

    _async_add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(_async_add_new_entities))


class R6DataRelaySensor(R6DataRelayTeamEntity, SensorEntity):
    """A per-team sensor driven by an entity description."""

    entity_description: R6DataRelaySensorEntityDescription

    def __init__(
        self,
        coordinator: R6DataRelayDataUpdateCoordinator,
        team_id: int,
        description: R6DataRelaySensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, team_id)
        self.entity_description = description
        self._attr_unique_id = f"{team_id}_{description.key}"

    @property
    @override
    def native_value(self) -> datetime | str | None:
        """Return the sensor's current value."""
        return self.entity_description.value_fn(self.team_data)

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return details of the match behind the value."""
        return self.entity_description.attributes_fn(self.team_data)
