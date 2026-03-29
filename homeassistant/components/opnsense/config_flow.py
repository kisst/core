"""Config flow for OPNsense."""

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_URL, CONF_VERIFY_SSL
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_API_SECRET, CONF_TRACKER_INTERFACE, DEFAULT_VERIFY_SSL, DOMAIN


class OPNSenseConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for OPNsense."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Check if already configured with same URL
            for entry in self._async_current_entries():
                if entry.data[CONF_URL] == user_input[CONF_URL]:
                    return self.async_abort(reason="already_configured")

            # Validate connection
            session = async_get_clientsession(
                self.hass,
                verify_ssl=user_input.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
            )
            url = user_input[CONF_URL].rstrip("/")
            auth = aiohttp.BasicAuth(
                user_input[CONF_API_KEY], user_input[CONF_API_SECRET]
            )

            try:
                resp = await session.get(
                    f"{url}/diagnostics/interface/get_arp",
                    auth=auth,
                    ssl=user_input.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
                )
                resp.raise_for_status()
            except aiohttp.ClientResponseError as err:
                if err.status in (401, 403):
                    errors["base"] = "invalid_auth"
                else:
                    errors["base"] = "cannot_connect"
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_URL],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_URL): str,
                    vol.Required(CONF_API_KEY): str,
                    vol.Required(CONF_API_SECRET): str,
                    vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
                    vol.Optional(CONF_TRACKER_INTERFACE, default=""): str,
                }
            ),
            errors=errors,
        )

    async def async_step_import(self, import_config):
        """Import OPNsense config from YAML."""
        # Convert tracker_interfaces list to comma-separated string for storage
        tracker_interfaces = import_config.get(CONF_TRACKER_INTERFACE, [])
        import_config[CONF_TRACKER_INTERFACE] = ",".join(tracker_interfaces)

        # Check if already configured
        for entry in self._async_current_entries():
            if entry.data[CONF_URL] == import_config[CONF_URL]:
                return self.async_abort(reason="already_configured")

        return self.async_create_entry(
            title=import_config[CONF_URL],
            data=import_config,
        )
