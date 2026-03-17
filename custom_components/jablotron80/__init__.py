"""The Detailed Hello World Push integration."""
import asyncio
from homeassistant.components.alarm_control_panel import DOMAIN as PLATFORM_ALARM_CONTROL_PANEL
from homeassistant.components.binary_sensor import DOMAIN as PLATFORM_BINARY_SENSOR
from homeassistant.components.sensor import DOMAIN as PLATFORM_SENSOR
from homeassistant.components.button import DOMAIN as PLATFORM_BUTTON
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, config_validation as cv
#from . import hub
from .const import (DOMAIN,DATA_JABLOTRON,	DATA_OPTIONS_UPDATE_UNSUBSCRIBER, NAME,CABLE_MODEL,MANUFACTURER,CABLE_MODELS)
from .jablotron import JA80CentralUnit
# List of platforms to support. There should be a matching .py file for each,
# eg <cover.py> and <sensor.py>
PLATFORMS = [PLATFORM_ALARM_CONTROL_PANEL,PLATFORM_BINARY_SENSOR,PLATFORM_SENSOR, PLATFORM_BUTTON]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

async def async_setup(hass: HomeAssistant, config: dict):
    # Ensure our name space for storing objects is a known type. A dict is
    # common/preferred as it allows a separate instance of your class for each
    # instance that has been created in the UI.
    hass.data.setdefault(DOMAIN, {})

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Store an instance of the "connecting" class that does the work of speaking
    # with your actual devices.
   # hass.data[DOMAIN][entry.entry_id] = hub.Hub(hass, entry.data["host"])

    # This creates each HA object for each platform your device requires.
    # It's done by calling the `async_setup_entry` function in each platform module.
    
    cu =  JA80CentralUnit(hass, entry.data, entry.options)
    await cu.initialize()

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
		config_entry_id=entry.entry_id,
		identifiers={(DOMAIN, cu.serial_port)},
		name="Cable",
        model=CABLE_MODELS[entry.data[CABLE_MODEL]],
        manufacturer=MANUFACTURER
	)

    # Migrate old device identifiers so that each config entry gets its
    # own devices instead of merging zones across panels.
    # Old formats: (DOMAIN, int) or (DOMAIN, "jablotron_panel_N")
    # New formats: (DOMAIN, "{serial_port}_{int}") or (DOMAIN, "{serial_port}_panel_{N}")
    # Also remove stale config entry associations from devices that
    # belong to a different serial port.
    serial_prefix = cu.serial_port + "_"
    for device in list(dr.async_entries_for_config_entry(device_registry, entry.entry_id)):
        migrated = False
        for ident in device.identifiers:
            if ident[0] != DOMAIN:
                continue
            val = ident[1]
            new_val = None
            if isinstance(val, int):
                new_val = f"{cu.serial_port}_{val}"
            elif isinstance(val, str) and val.startswith("jablotron_panel_"):
                zone = val.removeprefix("jablotron_panel_")
                new_val = f"{cu.serial_port}_panel_{zone}"
            elif isinstance(val, str) and not val.startswith(serial_prefix) and val != cu.serial_port:
                # Device identifier belongs to a different serial port —
                # remove this config entry's stale association.
                device_registry.async_update_device(
                    device.id, remove_config_entry_id=entry.entry_id
                )
                migrated = True
                break
            if new_val is not None:
                device_registry.async_update_device(
                    device.id, new_identifiers={(DOMAIN, new_val)}
                )
                migrated = True
                break

    hass.data[DOMAIN][entry.entry_id] = {
		DATA_JABLOTRON: cu,
	    DATA_OPTIONS_UPDATE_UNSUBSCRIBER: entry.add_update_listener(options_update_listener),
	}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    # This is called when an entry/configured device is to be removed. The class
    # needs to unload itself, and remove callbacks. See the classes for further
    # details
    options_update_unsubscriber = hass.data[DOMAIN][entry.entry_id][DATA_OPTIONS_UPDATE_UNSUBSCRIBER]
    options_update_unsubscriber()
    cu = hass.data[DOMAIN][entry.entry_id][DATA_JABLOTRON]
    cu.shutdown()
    hass.data[DOMAIN].pop(entry.entry_id)
    return True

async def options_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
	cu = hass.data[DOMAIN][entry.entry_id][DATA_JABLOTRON]
	cu.update_options(entry.options)
