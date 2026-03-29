"""Device tracker support for OPNSense routers."""

from homeassistant.components.device_tracker import DeviceScanner

from .const import CONF_TRACKER_INTERFACE, DOMAIN, LOGGER


async def async_get_scanner(hass, config, discovery_info=None):
    """Configure the OPNSense device_tracker."""
    # Find the config entry data - use the first (and typically only) entry
    for entry_data in hass.data.get(DOMAIN, {}).values():
        client = entry_data["client"]
        tracker_interfaces = entry_data[CONF_TRACKER_INTERFACE]
        return OPNSenseDeviceScanner(client, tracker_interfaces)
    return None


class OPNSenseDeviceScanner(DeviceScanner):
    """This class queries a router running OPNsense."""

    def __init__(self, client, interfaces):
        """Initialize the scanner."""
        self.last_results = {}
        self.client = client
        self.interfaces = interfaces

    def _get_mac_addrs(self, devices):
        """Create dict with mac address keys from list of devices."""
        out_devices = {}
        for device in devices:
            if not self.interfaces:
                out_devices[device["mac"]] = device
            elif device["intf_description"] in self.interfaces:
                out_devices[device["mac"]] = device
        return out_devices

    async def async_scan_devices(self):
        """Scan for new devices and return a list with found device IDs."""
        await self.async_update_info()
        return list(self.last_results)

    def get_device_name(self, device):
        """Return the name of the given device or None if we don't know."""
        if device not in self.last_results:
            return None
        hostname = self.last_results[device].get("hostname") or None
        return hostname

    async def async_update_info(self):
        """Ensure the information from the OPNSense router is up to date.

        Return boolean if scanning successful.
        """
        devices = await self.client.get_arp()
        self.last_results = self._get_mac_addrs(devices)

    def get_extra_attributes(self, device):
        """Return the extra attrs of the given device."""
        if device not in self.last_results:
            return None
        mfg = self.last_results[device].get("manufacturer")
        if mfg:
            return {"manufacturer": mfg}
        return {}
