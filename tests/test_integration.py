"""Tests for the Spider Grills cloud integration."""

import re
import time

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.spider_venom.const import DOMAIN

BASE = "https://spidergrills.app"
THING = "0123456789abcdef0123456789abcdef"
DEVICES = [
    {"name": "Venom", "model": "Venom", "thingName": THING, "macAddress": "aabbccddeeff"},
]
GRAPH = re.compile(rf"^{BASE}/api/devices/{THING}/graph-points/\d+/\d+$")


def _point(temp=287):
    return {
        "timestamp": int(time.time()) - 3,
        "fah": True,
        "pit": {"temp": temp, "trgt": 275, "min": 150, "max": 700, "intensity": 5, "disp": 286},
        "p1": {"temp": 165, "trgt": 203},
        "p2": {"temp": 168, "trgt": 203},
        "rssi": -69,
        "vers": "02.01",
    }


def _entry(**data):
    base = {
        CONF_EMAIL: "user@example.com",
        "thing_name": THING,
        CONF_SCAN_INTERVAL: 30,
        "device_name": "Venom",
        "model": "Venom",
        "mac": "aabbccddeeff",
        "access_token": "access-1",
        "refresh_token": "refresh-1",
    }
    base.update(data)
    return MockConfigEntry(domain=DOMAIN, unique_id=THING, data=base, title="Venom")


async def test_user_flow_creates_entry(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.post(f"{BASE}/auth/login", json={"accessToken": "a", "refreshToken": "r", "expiresIn": 10})
    aioclient_mock.get(f"{BASE}/api/devices", json=DEVICES)
    aioclient_mock.get(GRAPH, json=[])

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_EMAIL: " user@example.com ", CONF_PASSWORD: "pw", CONF_SCAN_INTERVAL: 30}
    )
    assert result["step_id"] == "select_device"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"thing_name": THING})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["access_token"] == "a"
    assert result["data"]["refresh_token"] == "r"
    assert result["data"]["model"] == "Venom"
    assert CONF_PASSWORD not in result["data"]


async def test_user_flow_invalid_auth(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.post(f"{BASE}/auth/login", status=401, text="")
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_EMAIL: "user@example.com", CONF_PASSWORD: "bad", CONF_SCAN_INTERVAL: 30}
    )
    assert result["errors"] == {"base": "invalid_auth"}


async def test_setup_reads_latest_point(hass: HomeAssistant, aioclient_mock) -> None:
    older = _point(280)
    older["timestamp"] -= 10
    aioclient_mock.get(GRAPH, json=[older, _point(287)])
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.venom_current_temperature").state == "287"
    assert hass.states.get("sensor.venom_target_temperature").state == "275"
    assert hass.states.get("sensor.venom_probe_1_temperature").state == "165"
    assert hass.states.get("binary_sensor.venom_reporting").state == "on"
    assert aioclient_mock.mock_calls[-1][3]["Authorization"] == "Bearer access-1"


async def test_setup_device_off(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(GRAPH, json=[])
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.venom_current_temperature").state == "unknown"
    assert hass.states.get("binary_sensor.venom_reporting").state == "off"


async def test_expired_token_is_refreshed_and_saved(hass: HomeAssistant, aioclient_mock) -> None:
    calls = {"n": 0}

    async def graph(method, url, data):
        from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMockResponse

        calls["n"] += 1
        status = 401 if calls["n"] == 1 else 200
        return AiohttpClientMockResponse(method, url, status=status, json=[_point()])

    aioclient_mock.get(GRAPH, side_effect=graph)
    aioclient_mock.post(f"{BASE}/auth/refresh", json={"accessToken": "access-2", "expiresIn": 10})
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.data["access_token"] == "access-2"
    assert entry.data["refresh_token"] == "refresh-1"
    assert hass.states.get("sensor.venom_current_temperature").state == "287"


async def test_old_v02_entry_triggers_reauth(hass: HomeAssistant, aioclient_mock) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=THING,
        title="Venom",
        data={
            "endpoint": "x.iot.us-east-2.amazonaws.com",
            "identity_pool_id": "us-east-2:abc",
            "region": "us-east-2",
            "thing_name": THING,
            CONF_SCAN_INTERVAL: 30,
        },
    )
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    flows = hass.config_entries.flow.async_progress()
    assert len(flows) == 1 and flows[0]["step_id"] == "reauth_confirm"

    aioclient_mock.post(f"{BASE}/auth/login", json={"accessToken": "a", "refreshToken": "r"})
    aioclient_mock.get(f"{BASE}/api/devices", json=DEVICES)
    aioclient_mock.get(GRAPH, json=[_point()])
    result = await hass.config_entries.flow.async_configure(
        flows[0]["flow_id"], {CONF_EMAIL: "user@example.com", CONF_PASSWORD: "pw"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert "endpoint" not in entry.data
    assert entry.data["access_token"] == "a"
    await hass.async_block_till_done()
    assert hass.states.get("sensor.venom_current_temperature").state == "287"
