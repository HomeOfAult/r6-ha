"""Tests for the relay sensors, binary sensors, coordinator and setup."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.r6_data_relay.const import DOMAIN
from custom_components.r6_data_relay.diagnostics import async_get_config_entry_diagnostics

from .conftest import FAZE, G2, SPACESTATION, TEAMS_URL, make_match, mock_relay


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_next_match_is_the_earliest_upcoming(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, mock_config_entry: MockConfigEntry
) -> None:
    """Upcoming matches arrive unordered; the earliest one involving the team wins."""
    mock_relay(
        aioclient_mock,
        teams=[G2],
        upcoming=[
            make_match(2, FAZE, G2, scheduled_at="2026-10-09T18:00:00Z"),
            make_match(1, G2, SPACESTATION, scheduled_at="2026-10-05T18:00:00Z"),
            make_match(3, FAZE, SPACESTATION, scheduled_at="2026-10-03T18:00:00Z"),
        ],
    )
    await _setup(hass, mock_config_entry)

    state = hass.states.get("sensor.g2_esports_next_match")
    assert state is not None
    assert state.state == "2026-10-05T18:00:00+00:00"
    assert state.attributes["opponent"] == "Spacestation"
    assert state.attributes["opponent_acronym"] == "SSG"
    assert state.attributes["tournament"] == "Playoffs"
    assert state.attributes["match_id"] == 1


async def test_no_upcoming_match_is_unknown(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, mock_config_entry: MockConfigEntry
) -> None:
    """A team with nothing scheduled has an unknown next match and last result."""
    mock_relay(aioclient_mock, teams=[G2])
    await _setup(hass, mock_config_entry)

    assert hass.states.get("sensor.g2_esports_next_match").state == "unknown"
    assert hass.states.get("sensor.g2_esports_last_result").state == "unknown"
    assert hass.states.get("binary_sensor.g2_esports_playing_now").state == "off"


async def test_last_result_win_loss_and_no_result(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, mock_config_entry: MockConfigEntry
) -> None:
    """The most recently ended past match decides each team's result."""
    mock_relay(
        aioclient_mock,
        teams=[G2, FAZE, SPACESTATION],
        past=[
            make_match(
                1, G2, FAZE, status="finished", scheduled_at="2026-09-01T18:00:00Z",
                end_at="2026-09-01T20:00:00Z", winner_id=G2["id"],
            ),
            make_match(
                2, G2, SPACESTATION, status="finished", scheduled_at="2026-09-10T18:00:00Z",
                end_at="2026-09-10T20:00:00Z", winner_id=SPACESTATION["id"],
            ),
            make_match(
                3, FAZE, SPACESTATION, status="canceled", scheduled_at="2026-09-20T18:00:00Z",
            ),
        ],
    )
    await _setup(hass, mock_config_entry)

    g2 = hass.states.get("sensor.g2_esports_last_result")
    assert g2.state == "loss"
    assert g2.attributes["opponent"] == "Spacestation"
    assert g2.attributes["ended_at"] == "2026-09-10T20:00:00+00:00"
    assert hass.states.get("sensor.spacestation_last_result").state == "no_result"
    assert hass.states.get("sensor.faze_clan_last_result").state == "no_result"


async def test_playing_now(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, mock_config_entry: MockConfigEntry
) -> None:
    """Only teams in a running match have the binary sensor on."""
    mock_relay(
        aioclient_mock,
        teams=[G2, SPACESTATION],
        running=[make_match(5, G2, FAZE, status="running", scheduled_at="2026-10-02T11:00:00Z")],
    )
    await _setup(hass, mock_config_entry)

    live = hass.states.get("binary_sensor.g2_esports_playing_now")
    assert live.state == "on"
    assert live.attributes["opponent"] == "FaZe Clan"
    assert hass.states.get("binary_sensor.spacestation_playing_now").state == "off"


async def test_team_enabled_later_gets_entities_and_disabled_team_is_removed(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, mock_config_entry: MockConfigEntry
) -> None:
    """Teams come and go on the relay without reloading the integration."""
    mock_relay(aioclient_mock, teams=[G2])
    await _setup(hass, mock_config_entry)
    assert hass.states.get("sensor.faze_clan_next_match") is None

    aioclient_mock.clear_requests()
    mock_relay(aioclient_mock, teams=[G2, FAZE])
    await mock_config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("sensor.faze_clan_next_match") is not None

    aioclient_mock.clear_requests()
    mock_relay(aioclient_mock, teams=[G2])
    await mock_config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    registry = dr.async_get(hass)
    entry_id = mock_config_entry.entry_id
    assert registry.async_get_device_by_identifier((DOMAIN, str(FAZE["id"])), entry_id) is None
    assert registry.async_get_device_by_identifier((DOMAIN, str(G2["id"])), entry_id) is not None
    assert hass.states.get("sensor.faze_clan_next_match") is None


async def test_setup_retries_when_relay_unreachable(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, mock_config_entry: MockConfigEntry
) -> None:
    """A failing first refresh leaves the entry to retry."""
    aioclient_mock.get(TEAMS_URL, status=503)
    mock_config_entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_rejected_token_starts_reauth(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, mock_config_entry: MockConfigEntry
) -> None:
    """A 401 during setup puts the entry into reauth."""
    aioclient_mock.get(TEAMS_URL, status=401)
    mock_config_entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR
    assert any(mock_config_entry.async_get_active_flows(hass, {"reauth"}))


async def test_unload(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, mock_config_entry: MockConfigEntry
) -> None:
    """The entry unloads cleanly."""
    mock_relay(aioclient_mock, teams=[G2])
    await _setup(hass, mock_config_entry)

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_diagnostics_redacts_token(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, mock_config_entry: MockConfigEntry
) -> None:
    """Diagnostics include team data but never the token."""
    mock_relay(aioclient_mock, teams=[G2])
    await _setup(hass, mock_config_entry)

    result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    assert result["entry_data"]["api_token"] == "**REDACTED**"
    assert result["teams"]["1"]["team"]["name"] == "G2 Esports"
