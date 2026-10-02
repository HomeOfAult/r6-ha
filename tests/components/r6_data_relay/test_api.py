"""Tests for the relay API client."""

from __future__ import annotations

import aiohttp
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.r6_data_relay.api import (
    R6DataRelayApiClient,
    R6DataRelayApiClientAuthError,
    R6DataRelayApiClientCommunicationError,
)

from .conftest import BASE_URL, G2, MATCHES_URL, TEAMS_URL, TOKEN, envelope


async def test_list_teams_sends_bearer_token_and_unwraps_envelope(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """The bearer token is sent and the data envelope is unwrapped."""
    aioclient_mock.get(TEAMS_URL, json=envelope([G2]))
    client = R6DataRelayApiClient(BASE_URL + "/", TOKEN, async_get_clientsession(hass))

    assert await client.async_list_teams() == [G2]
    assert aioclient_mock.mock_calls[0][3]["Authorization"] == f"Bearer {TOKEN}"


async def test_list_matches_passes_status(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """The status filter is sent as a query parameter; null data becomes []."""
    aioclient_mock.get(f"{MATCHES_URL}?status=past", json={"data": None})
    client = R6DataRelayApiClient(BASE_URL, TOKEN, async_get_clientsession(hass))

    assert await client.async_list_matches("past") == []


@pytest.mark.parametrize("status", [401, 403])
async def test_auth_failure(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, status: int
) -> None:
    """401/403 raise the auth error."""
    aioclient_mock.get(TEAMS_URL, status=status)
    client = R6DataRelayApiClient(BASE_URL, TOKEN, async_get_clientsession(hass))

    with pytest.raises(R6DataRelayApiClientAuthError):
        await client.async_list_teams()


async def test_server_error_is_communication_error(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Other 4xx/5xx responses raise the communication error."""
    aioclient_mock.get(TEAMS_URL, status=503)
    client = R6DataRelayApiClient(BASE_URL, TOKEN, async_get_clientsession(hass))

    with pytest.raises(R6DataRelayApiClientCommunicationError):
        await client.async_list_teams()


async def test_connection_error_is_communication_error(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Transport failures raise the communication error."""
    aioclient_mock.get(TEAMS_URL, exc=aiohttp.ClientConnectionError("boom"))
    client = R6DataRelayApiClient(BASE_URL, TOKEN, async_get_clientsession(hass))

    with pytest.raises(R6DataRelayApiClientCommunicationError):
        await client.async_list_teams()
