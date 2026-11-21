"""Constants for the Spider Grills Venom integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "spider_venom"

CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_THING_NAME = "thing_name"
CONF_DEVICE_NAME = "device_name"
CONF_MODEL = "model"
CONF_MAC = "mac"

DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)

# A device is considered offline when no telemetry point arrived in this window.
TELEMETRY_WINDOW_SECONDS = 300

PLATFORMS = ["sensor", "binary_sensor"]
