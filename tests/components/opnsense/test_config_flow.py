"""Tests for the OPNsense config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp

from homeassistant import config_entries
from homeassistant.components.opnsense.const import (
    CONF_API_SECRET,
    CONF_TRACKER_INTERFACE,
    DOMAIN,
)
from homeassistant.const import CONF_API_KEY, CONF_URL, CONF_VERIFY_SSL

MOCK_USER_INPUT = {
    CONF_URL: "https://opnsense.local/api",
    CONF_API_KEY: "test_key",
    CONF_API_SECRET: "test_secret",
    CONF_VERIFY_SSL: False,
    CONF_TRACKER_INTERFACE: "",
}


def _mock_session_success():
    """Return a mock session that succeeds on get."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_session = MagicMock()
    mock_session.get = AsyncMock(return_value=mock_resp)
    return mock_session


async def test_user_form(hass):
    """Test we get the user form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {}


async def test_user_form_success(hass):
    """Test successful user config flow."""
    mock_session = _mock_session_success()

    with patch(
        "homeassistant.components.opnsense.config_flow.async_get_clientsession",
        return_value=mock_session,
    ), patch(
        "homeassistant.components.opnsense.OPNSenseClient", autospec=True
    ) as mock_client_cls, patch(
        "homeassistant.components.opnsense.async_load_platform",
    ):
        client = mock_client_cls.return_value
        client.get_arp = AsyncMock(return_value=[])

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data=MOCK_USER_INPUT,
        )
        await hass.async_block_till_done()

    assert result["type"] == "create_entry"
    assert result["title"] == "https://opnsense.local/api"
    assert result["data"][CONF_URL] == "https://opnsense.local/api"
    assert result["data"][CONF_API_KEY] == "test_key"
    assert result["data"][CONF_API_SECRET] == "test_secret"


async def test_user_form_invalid_auth(hass):
    """Test we handle invalid auth."""
    mock_session = MagicMock()
    mock_session.get = AsyncMock(
        side_effect=aiohttp.ClientResponseError(
            request_info=MagicMock(), history=(), status=403, message="Forbidden"
        )
    )

    with patch(
        "homeassistant.components.opnsense.config_flow.async_get_clientsession",
        return_value=mock_session,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data=MOCK_USER_INPUT,
        )

    assert result["type"] == "form"
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_form_cannot_connect(hass):
    """Test we handle connection error."""
    mock_session = MagicMock()
    mock_session.get = AsyncMock(side_effect=aiohttp.ClientError())

    with patch(
        "homeassistant.components.opnsense.config_flow.async_get_clientsession",
        return_value=mock_session,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data=MOCK_USER_INPUT,
        )

    assert result["type"] == "form"
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_form_already_configured(hass):
    """Test we abort if already configured."""
    entry = config_entries.ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="https://opnsense.local/api",
        data={
            CONF_URL: "https://opnsense.local/api",
            CONF_API_KEY: "test_key",
            CONF_API_SECRET: "test_secret",
            CONF_VERIFY_SSL: False,
        },
        source=config_entries.SOURCE_USER,
        connection_class=config_entries.CONN_CLASS_LOCAL_POLL,
        system_options={},
    )
    hass.config_entries._entries.append(entry)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data=MOCK_USER_INPUT,
    )

    assert result["type"] == "abort"
    assert result["reason"] == "already_configured"


async def test_import_flow(hass):
    """Test YAML import creates a config entry."""
    with patch(
        "homeassistant.components.opnsense.OPNSenseClient", autospec=True
    ) as mock_client_cls, patch(
        "homeassistant.components.opnsense.async_load_platform",
    ):
        client = mock_client_cls.return_value
        client.get_arp = AsyncMock(return_value=[])
        client.get_interfaces = AsyncMock(
            return_value={"igb0": "WAN", "igb1": "LAN"}
        )

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={
                CONF_URL: "https://opnsense.local/api",
                CONF_API_KEY: "test_key",
                CONF_API_SECRET: "test_secret",
                CONF_VERIFY_SSL: False,
                CONF_TRACKER_INTERFACE: ["LAN", "WAN"],
            },
        )
        await hass.async_block_till_done()

    assert result["type"] == "create_entry"
    assert result["data"][CONF_TRACKER_INTERFACE] == "LAN,WAN"
