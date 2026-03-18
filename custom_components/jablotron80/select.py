from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.select import SelectEntity
from .jablotron import JA80CentralUnit, JablotronModeSelect, JablotronState
from .jablotronHA import JablotronEntity
from .const import (
	DATA_JABLOTRON,
	DOMAIN)

import logging
import voluptuous as vol
from homeassistant.helpers import config_validation as cv

LOGGER = logging.getLogger(__package__)

SERVICE_ENTER_SERVICE_MODE = "enter_service_mode"

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities) -> None:
	cu = hass.data[DOMAIN][config_entry.entry_id][DATA_JABLOTRON] # type: JA80CentralUnit
	async_add_entities([JablotronModeSelectEntity(cu.mode_select, cu)], True)

	async def handle_enter_service_mode(call):
		code = call.data.get("code")
		if not JablotronState.is_disarmed_state(cu._last_state):
			LOGGER.error("Can only enter service mode when the system is disarmed")
			return
		cu.enter_elevated_mode(code)

	hass.services.async_register(
		DOMAIN,
		SERVICE_ENTER_SERVICE_MODE,
		handle_enter_service_mode,
		schema=vol.Schema({
			vol.Required("code"): cv.string,
		}),
	)


class JablotronModeSelectEntity(JablotronEntity, SelectEntity):

	_attr_options = ["Operating", "Maintenance", "Service"]

	def __init__(self, select: JablotronModeSelect, cu: JA80CentralUnit) -> None:
		super().__init__(cu, select)

	@property
	def current_option(self) -> str:
		return self._object.value

	async def async_select_option(self, option: str) -> None:
		current = self._object.value
		if option == current:
			return
		if option == "Maintenance":
			if current != "Operating":
				LOGGER.error("Can only enter maintenance mode from operating mode")
				return
			self._cu.enter_elevated_mode(self._cu._master_code)
		elif option == "Service":
			raise ValueError(
				"Use the jablotron80.enter_service_mode service with the service code. "
				"Call: service jablotron80.enter_service_mode with data: {code: 'your_service_code'}"
			)
		elif option == "Operating":
			self._cu.return_mode()
