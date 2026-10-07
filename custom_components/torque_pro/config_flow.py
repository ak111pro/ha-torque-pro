"""Config flow for Torque Pro."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.core import callback
from homeassistant.helpers.network import NoURLAvailableError, get_url
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    API_PATH,
    CONF_DRIVING_TIMEOUT,
    CONF_EMAIL,
    DATA_LEGACY_ALIAS,
    DEFAULT_DRIVING_TIMEOUT,
    DOMAIN,
    LEGACY_API_PATH,
)

EMAIL_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.EMAIL))


class TorqueProConfigFlow(ConfigFlow, domain=DOMAIN):
    """One entry receives the uploads of all phones and vehicles."""

    VERSION = 1

    def _placeholders(self) -> dict[str, str]:
        try:
            base = get_url(self.hass, prefer_external=True, allow_internal=True)
        except NoURLAvailableError:
            base = "https://<your-home-assistant>"
        legacy = self.hass.data.get(DATA_LEGACY_ALIAS, False)
        return {
            "url": f"{base}{API_PATH}",
            "legacy_url": f"{base}{LEGACY_API_PATH}" if legacy else "—",
        }

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        if user_input is not None:
            email = (user_input.get(CONF_EMAIL) or "").strip()
            return self.async_create_entry(title="Torque Pro", data={CONF_EMAIL: email})
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Optional(CONF_EMAIL): EMAIL_SELECTOR}),
            description_placeholders=self._placeholders(),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> TorqueProOptionsFlow:
        return TorqueProOptionsFlow()


class TorqueProOptionsFlow(OptionsFlowWithReload):
    """E-mail filter and driving timeout."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current_email = self.config_entry.options.get(
            CONF_EMAIL, self.config_entry.data.get(CONF_EMAIL, "")
        )
        schema = vol.Schema(
            {
                vol.Optional(CONF_EMAIL, description={"suggested_value": current_email}): EMAIL_SELECTOR,
                vol.Required(
                    CONF_DRIVING_TIMEOUT,
                    default=self.config_entry.options.get(CONF_DRIVING_TIMEOUT, DEFAULT_DRIVING_TIMEOUT),
                ): NumberSelector(
                    NumberSelectorConfig(min=15, max=3600, step=5, unit_of_measurement="s", mode=NumberSelectorMode.BOX)
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
