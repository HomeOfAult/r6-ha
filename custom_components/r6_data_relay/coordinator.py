"""Data update coordinator for the R6 Data Relay integration."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, override

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import (
    R6DataRelayApiClient,
    R6DataRelayApiClientAuthError,
    R6DataRelayApiClientCommunicationError,
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, LOGGER

type R6DataRelayConfigEntry = ConfigEntry[R6DataRelayDataUpdateCoordinator]

_FAR_FUTURE = datetime.max.replace(tzinfo=dt_util.UTC)
_LONG_AGO = datetime.min.replace(tzinfo=dt_util.UTC)


@dataclass(frozen=True, slots=True)
class TeamData:
    """Everything the entities need to know about one enabled team."""

    team: dict[str, Any]
    next_match: dict[str, Any] | None
    running_match: dict[str, Any] | None
    last_match: dict[str, Any] | None


def parse_time(value: str | None) -> datetime | None:
    """Parse an RFC3339 timestamp from the relay, or None if absent/invalid."""
    return dt_util.parse_datetime(value) if value else None


def match_start(match: dict[str, Any]) -> datetime | None:
    """Return when a match is (or was) scheduled to start."""
    return parse_time(match.get("scheduled_at")) or parse_time(match.get("begin_at"))


def match_end(match: dict[str, Any]) -> datetime | None:
    """Return when a match ended, falling back to its start time."""
    return parse_time(match.get("end_at")) or match_start(match)


def opponent_of(match: dict[str, Any], team_id: int) -> dict[str, Any] | None:
    """Return the team facing `team_id` in a match, if known."""
    for entry in match.get("opponents") or []:
        opponent = entry.get("opponent") or {}
        if opponent.get("id") is not None and opponent["id"] != team_id:
            return opponent
    return None


def _involves(match: dict[str, Any], team_id: int) -> bool:
    return any(
        (entry.get("opponent") or {}).get("id") == team_id
        for entry in match.get("opponents") or []
    )


class R6DataRelayDataUpdateCoordinator(DataUpdateCoordinator[dict[int, TeamData]]):
    """Polls the relay and splits its match lists per enabled team."""

    config_entry: R6DataRelayConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: R6DataRelayConfigEntry,
        client: R6DataRelayApiClient,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass=hass,
            logger=LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.client = client

    @override
    async def _async_update_data(self) -> dict[int, TeamData]:
        """Fetch teams plus upcoming/running/past matches, keyed by team id."""
        try:
            teams, upcoming, running, past = await asyncio.gather(
                self.client.async_list_teams(),
                self.client.async_list_matches("upcoming"),
                self.client.async_list_matches("running"),
                self.client.async_list_matches("past"),
            )
        except R6DataRelayApiClientAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except R6DataRelayApiClientCommunicationError as err:
            raise UpdateFailed(str(err)) from err

        new_data: dict[int, TeamData] = {}
        for team in teams:
            team_id = team["id"]
            new_data[team_id] = TeamData(
                team=team,
                next_match=min(
                    (m for m in upcoming if _involves(m, team_id)),
                    key=lambda m: match_start(m) or _FAR_FUTURE,
                    default=None,
                ),
                running_match=next((m for m in running if _involves(m, team_id)), None),
                last_match=max(
                    (m for m in past if _involves(m, team_id)),
                    key=lambda m: match_end(m) or _LONG_AGO,
                    default=None,
                ),
            )

        LOGGER.debug(
            "Refreshed relay data: teams=%d upcoming=%d running=%d past=%d",
            len(teams),
            len(upcoming),
            len(running),
            len(past),
        )

        removed_ids = set(self.data or {}) - new_data.keys()
        if removed_ids:
            self._async_remove_stale_devices(removed_ids)
        return new_data

    def _async_remove_stale_devices(self, removed_team_ids: set[int]) -> None:
        """Remove the device (and its entities) for teams no longer enabled.

        A team drops out of GET /teams when it's disabled on the relay; there
        is no separate event, so each refresh is diffed against the last one.
        """
        device_registry = dr.async_get(self.hass)
        for team_id in removed_team_ids:
            device = device_registry.async_get_device_by_identifier(
                (DOMAIN, str(team_id)), self.config_entry.entry_id
            )
            if device is not None:
                LOGGER.info("Removing device for team %s: no longer enabled on the relay", team_id)
                device_registry.async_remove_device(device.id)
