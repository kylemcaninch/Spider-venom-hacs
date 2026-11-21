# Changelog

## v0.3.0 - 2026-11-21

### Changed

- Spider Grills disabled the anonymous AWS IoT (Cognito guest) access this integration used, so every shadow read returned HTTP 403. The integration now reads telemetry from the same `spidergrills.app` API the current mobile app uses (`/api/devices/{id}/graph-points/{start}/{end}`), authenticated with your Spider Grills account.
- Home Assistant stores the account's access and refresh tokens (never the password) and refreshes them automatically; if Spider Grills rejects them, Home Assistant asks you to log in again.
- Existing v0.2 entries are kept: after upgrading, Home Assistant shows a "Log in again" prompt.
- Device name, model, and MAC address come from your account's device list, so non-Venom devices (for example the Giant Huntsman) also work.
- New sensors: Displayed temperature, Last report, and a Reporting connectivity sensor (off when the device has not sent data for 5 minutes).

### Removed

- Controls (target temperature numbers, power/engaged/paused/high-temp switches, and the `set_target_temperature` service) are removed for now: the new cloud API for sending commands has not been identified yet.
- Sensors whose data the new API does not provide (Wi-Fi SSID/BSSID, flags, errors, door, heating, notification limits).

## v0.2.0 - 2026-07-25

### Added

- Add target temperature controls for Probe 1 and Probe 2.
- Add debug response-body logging for API discovery with token redaction.

### Notes

- Debug response logging is only emitted when `custom_components.spider_venom` is set to `debug`.
- Debug logs may include device and network metadata such as model, firmware version, Wi-Fi SSID, BSSID, and MAC address.
