"""Config flow for Spider Grills Venom."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_SCAN_INTERVAL
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SpiderGrillsAccountClient, SpiderVenomApiError, SpiderVenomAuthError
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_DEVICE_NAME,
    CONF_MAC,
    CONF_MODEL,
    CONF_REFRESH_TOKEN,
    CONF_THING_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    TELEMETRY_WINDOW_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


class SpiderVenomConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Spider Grills config flow."""

    VERSION = 1
    _client: SpiderGrillsAccountClient
    _email: str
    _discovered_devices: dict[str, dict[str, Any]]
    _scan_interval: int

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        return await self.async_step_account(user_input)

    async def async_step_account(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Log in and discover devices."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                devices = await self._async_login(user_input)
            except SpiderVenomAuthError as err:
                _LOGGER.warning("Spider Grills login rejected: %s", err)
                errors["base"] = "invalid_auth"
            except SpiderVenomApiError as err:
                _LOGGER.warning("Unable to discover Spider Grills devices: %s", err)
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error discovering Spider Grills devices")
                errors["base"] = "unknown"
            else:
                self._scan_interval = user_input[CONF_SCAN_INTERVAL]
                self._discovered_devices = {
                    thing_name: device
                    for device in devices
                    if (thing_name := _device_thing_name(device)) is not None
                }
                if not self._discovered_devices:
                    errors["base"] = "no_devices"
                else:
                    return await self.async_step_select_device()

        return self.async_show_form(
            step_id="account",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=int(DEFAULT_SCAN_INTERVAL.total_seconds()),
                    ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
                }
            ),
            errors=errors,
        )

    async def async_step_select_device(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Select a discovered Spider Grills device."""
        errors: dict[str, str] = {}
        device_options = {
            thing_name: _device_label(device, thing_name)
            for thing_name, device in self._discovered_devices.items()
        }

        if user_input is not None:
            thing_name = user_input[CONF_THING_NAME]
            device = self._discovered_devices[thing_name]
            await self.async_set_unique_id(thing_name)
            self._abort_if_unique_id_configured()
            try:
                # Validates access to telemetry; an empty result just means the grill is off.
                await self._client.async_get_latest_point(thing_name, TELEMETRY_WINDOW_SECONDS)
            except SpiderVenomApiError as err:
                _LOGGER.warning("Unable to read Spider Grills telemetry: %s", err)
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=_device_label(device, thing_name),
                    data={
                        CONF_EMAIL: self._email,
                        CONF_THING_NAME: thing_name,
                        CONF_SCAN_INTERVAL: self._scan_interval,
                        **_device_metadata(device),
                        **self._token_data(),
                    },
                )

        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema({vol.Required(CONF_THING_NAME): vol.In(device_options)}),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> config_entries.ConfigFlowResult:
        """Start reauthentication when tokens expire or after upgrading from v0.2."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Ask for the account password again."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()

        if user_input is not None:
            try:
                devices = await self._async_login(user_input)
            except SpiderVenomAuthError:
                errors["base"] = "invalid_auth"
            except SpiderVenomApiError as err:
                _LOGGER.warning("Unable to log in to Spider Grills: %s", err)
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during Spider Grills reauth")
                errors["base"] = "unknown"
            else:
                thing_name = entry.data[CONF_THING_NAME]
                device = next((d for d in devices if _device_thing_name(d) == thing_name), None)
                if device is None:
                    errors["base"] = "device_missing"
                else:
                    data = {
                        key: value
                        for key, value in entry.data.items()
                        # Drop settings left over from the AWS IoT version.
                        if key not in ("endpoint", "identity_pool_id", "region")
                    }
                    data.update(
                        {
                            CONF_EMAIL: self._email,
                            **_device_metadata(device),
                            **self._token_data(),
                        }
                    )
                    return self.async_update_reload_and_abort(entry, data=data)

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL, default=entry.data.get(CONF_EMAIL, "")): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def _async_login(self, user_input: dict[str, Any]) -> list[dict[str, Any]]:
        self._email = user_input[CONF_EMAIL].strip()
        self._client = SpiderGrillsAccountClient(session=async_get_clientsession(self.hass))
        await self._client.async_login(email=self._email, password=user_input[CONF_PASSWORD])
        return await self._client.async_get_devices()

    def _token_data(self) -> dict[str, Any]:
        return {
            CONF_ACCESS_TOKEN: self._client.access_token,
            CONF_REFRESH_TOKEN: self._client.refresh_token,
        }


def _device_thing_name(device: dict[str, Any]) -> str | None:
    """Extract the device identifier used by the Spider Grills API."""
    for key in ("thingName", "thing_name", "externalId", "deviceId"):
        value = device.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _device_metadata(device: dict[str, Any]) -> dict[str, Any]:
    return {
        CONF_DEVICE_NAME: device.get("name") or device.get("deviceName"),
        CONF_MODEL: device.get("model"),
        CONF_MAC: device.get("macAddress"),
    }


def _device_label(device: dict[str, Any], thing_name: str) -> str:
    """Return a friendly device label."""
    for key in ("name", "deviceName", "model"):
        value = device.get(key)
        if isinstance(value, str) and value:
            return value
    return thing_name
