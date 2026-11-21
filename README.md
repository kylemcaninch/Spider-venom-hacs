# Spider Grills for Home Assistant

Custom Home Assistant integration for Spider Grills controllers (Venom, Giant
Huntsman, …). It logs in with your Spider Grills account, lets you pick a device,
and shows live pit and probe temperatures.

> **v0.3.0 is read-only.** Spider Grills' new app and firmware turned off the AWS IoT
> access older versions used. Temperatures work again through the `spidergrills.app`
> API the current app uses; target temperature and power controls will return once
> the app's command request is known.

Based on [brannonjames/spider-venom-home-assistant](https://github.com/brannonjames/spider-venom-home-assistant)
v0.2.0. All credit for the original integration goes to its author.

## Install with HACS

1. HACS → ⋮ → **Custom repositories** → add `https://github.com/kylemcaninch/spider-venom-hacs`, category **Integration**.
2. Install **Spider Grills Venom** and restart Home Assistant.
   If you had the original integration installed through HACS, remove that repository
   in HACS first (both use the `spider_venom` folder); your config entries are kept.
3. New install: Settings → Devices & services → Add integration → **Spider Grills Venom**.
   Upgrading from v0.2: a **Log in again** notice appears; enter your email and password.

Manual install: copy `custom_components/spider_venom` to `/config/custom_components/` and restart.

## Setup

Log in with your Spider Grills email and password and choose a device. Add the
integration again for each additional device.

Home Assistant stores the account's access and refresh tokens, not your password, and
renews them automatically. If Spider Grills rejects them, Home Assistant asks you to
log in again.

## Entities

Sensors: current temperature, displayed temperature, target temperature, probe 1/2
temperature and target, min/max target temperature, heat intensity, signal strength,
firmware version, last report, model, MAC address.

Binary sensors: **Reporting** (off when no data arrived in the last 5 minutes — the
grill is off or offline) and Fahrenheit mode.

After upgrading from v0.2, entities for removed controls and sensors become
unavailable; delete them from the device page.

## Troubleshooting

```yaml
logger:
  logs:
    custom_components.spider_venom: debug
```

Response bodies are logged with tokens and emails redacted; they still include
device IDs and MAC addresses, so review logs before sharing them.

## Development

```sh
make setup   # uv sync: Home Assistant test harness + ruff
make check   # lint + tests
```

How the cloud API works: [docs/architecture.md](docs/architecture.md).
