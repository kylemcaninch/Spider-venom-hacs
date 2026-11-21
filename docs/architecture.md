# Architecture

## Overview

A Home Assistant custom integration under `custom_components/spider_venom/`:

- `config_flow.py` logs in (`POST /auth/login`), lists devices (`GET /api/devices`),
  and stores the chosen device plus tokens in the config entry. A reauth flow
  handles rejected tokens and v0.2 entries.
- `coordinator.py` polls every `scan_interval` seconds (default 30). Each poll
  fetches graph points for the last 5 minutes and keeps the newest one.
- `sensor.py` / `binary_sensor.py` read the flattened state from `normalize_point()`.

## Spider Grills cloud API (observed, undocumented)

Base URL `https://spidergrills.app`; JSON; `Authorization: Bearer <accessToken>`.

| Request | Response (observed 2026-11-21) |
|---|---|
| `POST /auth/login` `{email, password}` | `{accessToken, refreshToken, expiresIn: 3888000, tokenType: "Bearer"}` |
| `POST /auth/refresh` `{refreshToken}` | `{accessToken, refreshToken?, expiresIn}` (from the web app's code) |
| `GET /api/devices` | list of `{id, name, model, thingName, macAddress, alert*…, user{…}}` |
| `GET /api/devices/{thingName}/graph-points/{startEpoch}/{endEpoch}` | list of points, ~one per 5 s while running; `[]` when off; HTTP 400 for a 30-day window |

Graph point:

```json
{"timestamp": 1795265822, "fah": true,
 "pit": {"temp": 287, "trgt": 275, "min": 150, "max": 700, "intensity": 5, "disp": 286},
 "p1": {"temp": 165, "trgt": 203}, "p2": {"temp": 168, "trgt": 203},
 "rssi": -69, "vers": "02.01"}
```

Unauthorized requests return HTTP 401. The previous AWS IoT shadow endpoint
(`a1gzggdqzynf8-ats.iot.us-east-2.amazonaws.com`, Cognito guest pool) now returns
HTTP 403 for guest credentials.

## Data

Config entry data: `email`, `thing_name`, `scan_interval`, `device_name`, `model`,
`mac`, `access_token`, `refresh_token`. No other persistence.

## External dependencies

- Spider Grills cloud (`spidergrills.app`) — the only runtime dependency.

## Deployment

None. The integration folder is copied into Home Assistant's
`/config/custom_components/` (README). `make build` produces the zip.

## Security

- Password is used once at login and not stored; tokens live in HA's config entry
  storage (`.storage/core.config_entries`), as is normal for HA integrations.
- Tests use fake tokens and IDs only.
