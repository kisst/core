"""Support for OPNSense Routers."""

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import CONF_API_KEY, CONF_URL, CONF_VERIFY_SSL
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.discovery import async_load_platform

from .const import (
    CONF_API_SECRET,
    CONF_TRACKER_INTERFACE,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    LOGGER,
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_URL): cv.url,
                vol.Required(CONF_API_KEY): cv.string,
                vol.Required(CONF_API_SECRET): cv.string,
                vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): cv.boolean,
                vol.Optional(CONF_TRACKER_INTERFACE, default=[]): vol.All(
                    cv.ensure_list, [cv.string]
                ),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


class OPNSenseClient:
    """Client for the OPNsense API."""

    def __init__(self, url, api_key, api_secret, session, verify_ssl):
        """Initialize the OPNsense client."""
        self._url = url.rstrip("/")
        self._auth = aiohttp.BasicAuth(api_key, api_secret)
        self._session = session
        self._verify_ssl = verify_ssl

    async def get_arp(self):
        """Get the ARP table from OPNsense."""
        return await self._get("diagnostics/interface/get_arp")

    async def get_interfaces(self):
        """Get available network interfaces from OPNsense."""
        return await self._get("diagnostics/networkinsight/get_interfaces")

    async def _get(self, endpoint):
        """Make a GET request to the OPNsense API."""
        url = f"{self._url}/{endpoint}"
        resp = await self._session.get(
            url, auth=self._auth, ssl=self._verify_ssl
        )
        resp.raise_for_status()
        return await resp.json()


async def async_setup(hass, config):
    """Import OPNsense configuration from YAML."""
    if DOMAIN in config:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=config[DOMAIN]
            )
        )
    return True


async def async_setup_entry(hass, config_entry):
    """Set up OPNsense from a config entry."""
    data = config_entry.data
    url = data[CONF_URL]
    api_key = data[CONF_API_KEY]
    api_secret = data[CONF_API_SECRET]
    verify_ssl = data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
    tracker_interfaces_str = data.get(CONF_TRACKER_INTERFACE, "")

    # Parse tracker interfaces from comma-separated string
    if isinstance(tracker_interfaces_str, list):
        tracker_interfaces = tracker_interfaces_str
    elif tracker_interfaces_str:
        tracker_interfaces = [
            i.strip() for i in tracker_interfaces_str.split(",") if i.strip()
        ]
    else:
        tracker_interfaces = []

    session = async_get_clientsession(hass, verify_ssl=verify_ssl)
    client = OPNSenseClient(url, api_key, api_secret, session, verify_ssl)

    try:
        await client.get_arp()
    except aiohttp.ClientError:
        LOGGER.exception("Failure while connecting to OPNsense API endpoint")
        return False

    if tracker_interfaces:
        try:
            interfaces_resp = await client.get_interfaces()
        except aiohttp.ClientError:
            LOGGER.exception(
                "Failure while retrieving OPNsense network interfaces"
            )
            return False
        interfaces = list(interfaces_resp.values())
        for interface in tracker_interfaces:
            if interface not in interfaces:
                LOGGER.error(
                    "Specified OPNsense tracker interface %s is not found",
                    interface,
                )
                return False

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = {
        "client": client,
        CONF_TRACKER_INTERFACE: tracker_interfaces,
    }

    hass.async_create_task(
        async_load_platform(
            hass, "device_tracker", DOMAIN, tracker_interfaces, {DOMAIN: data}
        )
    )
    return True


async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""
    hass.data[DOMAIN].pop(config_entry.entry_id)
    return True
