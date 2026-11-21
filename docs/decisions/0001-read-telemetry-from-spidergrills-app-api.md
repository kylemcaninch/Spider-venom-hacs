# 0001. Read telemetry from the spidergrills.app API instead of AWS IoT

- Status: accepted
- Date: 2026-11-21
- Deciders: owner, Claude (developer)
- Task: Hummingways PR #6 (task record restore-telemetry)

## Context

Upstream v0.2.0 obtained Cognito guest credentials and read the AWS IoT device
shadow directly. After Spider Grills' new app and firmware, guest credentials get
HTTP 403 from the IoT data endpoint, while `spidergrills.app` login and device
listing still work. A traffic capture of the iOS app showed it now reads
telemetry from `GET /api/devices/{thingName}/graph-points/{start}/{end}` with the
account's bearer token. Login returns no token usable for authenticated Cognito access.

The project is a Home Assistant custom integration, not a service, so the
repository's default Python service stack (Postgres, Docker, Coolify) does not apply.

## Decision

- Use the `spidergrills.app` API with the account's access token for all reads,
  taking the newest graph point from the last 5 minutes as the current state.
- Store access and refresh tokens (not the password) in the config entry; refresh
  on 401 and fall back to Home Assistant's reauth flow.
- Ship read-only until the command request is captured; remove the controls rather
  than leave them broken.
- Project shape: no Dockerfile, compose file or deploy script; `make docker-build`
  and `make deploy` are documented no-ops; `make build` zips the integration;
  `make typecheck` is a no-op (HA's mypy setup is out of scope for now).

## Consequences

- Temperatures work again for Venom and Giant Huntsman, with ~5 s data latency.
- Depends on an undocumented API that may change without notice.
- Fields only present in the old shadow (Wi-Fi SSID, door, errors, flags) are gone.
- Users of v0.2 must log in again once.
- Controls remain a follow-up task.
