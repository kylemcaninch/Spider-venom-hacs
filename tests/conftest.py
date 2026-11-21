"""Fixtures for Spider Grills tests."""

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom_components in every test."""
    yield


@pytest.fixture(autouse=True)
def us_units(hass):
    """Use Fahrenheit so temperatures are not converted in assertions."""
    from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM

    hass.config.units = US_CUSTOMARY_SYSTEM
