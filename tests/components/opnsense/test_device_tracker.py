"""The tests for the opnsense device tracker platform."""

from unittest.mock import AsyncMock, patch

import pytest

from homeassistant import config_entries
from homeassistant.components.opnsense.const import (
    CONF_API_SECRET,
    CONF_TRACKER_INTERFACE,
    DOMAIN,
)
from homeassistant.const import CONF_API_KEY, CONF_URL, CONF_VERIFY_SSL
from homeassistant.setup import async_setup_component

ARP_RESPONSE = [
    {
        "hostname": "",
        "intf": "igb1",
        "intf_description": "LAN",
        "ip": "192.168.0.123",
        "mac": "ff:ff:ff:ff:ff:ff",
        "manufacturer": "",
    },
    {
        "hostname": "Desktop",
        "intf": "igb1",
        "intf_description": "LAN",
        "ip": "192.168.0.167",
        "mac": "ff:ff:ff:ff:ff:fe",
        "manufacturer": "OEM",
    },
]

INTERFACES_RESPONSE = {"igb0": "WAN", "igb1": "LAN"}


@pytest.fixture(name="mock_opnsense_client")
def mock_opnsense_client_fixture():
    """Mock OPNSenseClient."""
    with patch(
        "homeassistant.components.opnsense.OPNSenseClient", autospec=True
    ) as mock_cls:
        client = mock_cls.return_value
        client.get_arp = AsyncMock(return_value=ARP_RESPONSE)
        client.get_interfaces = AsyncMock(return_value=INTERFACES_RESPONSE)
        yield client


async def test_get_scanner(hass, mock_opnsense_client, mock_device_tracker_conf):
    """Test creating an opnsense scanner."""
    # Set up the config entry directly (bypass YAML import flow)
    entry = config_entries.ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="https://fake_host_fun/api",
        data={
            CONF_URL: "https://fake_host_fun/api",
            CONF_API_KEY: "fake_key",
            CONF_API_SECRET: "fake_secret",
            CONF_VERIFY_SSL: False,
            CONF_TRACKER_INTERFACE: "",
        },
        source=config_entries.SOURCE_IMPORT,
        connection_class=config_entries.CONN_CLASS_LOCAL_POLL,
        system_options={},
    )
    hass.config_entries._entries.append(entry)

    # Set up device tracker component first
    await async_setup_component(hass, "device_tracker", {})

    # Now trigger entry setup
    result = await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert result
    device_1 = hass.states.get("device_tracker.desktop")
    assert device_1 is not None
    assert device_1.state == "home"
    device_2 = hass.states.get("device_tracker.ff_ff_ff_ff_ff_ff")
    assert device_2.state == "home"
