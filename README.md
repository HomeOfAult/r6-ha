# r6-ha

A Home Assistant custom integration for [r6-data-relay](https://github.com/thault/r6-data-relay), which caches Rainbow Six Siege pro esports data from PandaScore. It polls the relay's read-only API (see its [`openapi.yaml`](https://github.com/thault/r6-data-relay/blob/main/openapi.yaml)) and exposes each tracked team as a device.

## What it adds

One device per team that is **enabled on the relay** (`PATCH /api/v1/admin/teams/{id}`), each with:

| Entity | State | Attributes |
| --- | --- | --- |
| `sensor.<team>_next_match` (`timestamp`) | scheduled start of the team's earliest upcoming match | `match_id`, `match_name`, `match_status`, `opponent`, `opponent_acronym`, `opponent_image_url`, `league`, `serie`, `tournament` |
| `sensor.<team>_last_result` (`enum`) | `win`, `loss` or `no_result` (canceled, or no winner recorded) for the most recently ended match | same as above, plus `ended_at` |
| `binary_sensor.<team>_playing_now` | on while the team has a running match | details of the running match |

Sensors are `unknown` when there is nothing to report (no upcoming match yet, no past match). All entities go `unavailable` if the relay can't be reached.

- Polls every 3 minutes (the relay's own match refresh cadence), using four cheap requests regardless of how many teams are tracked: `/teams` and `/matches` for `upcoming`, `running` and `past`.
- Enabling a team on the relay adds its device on the next poll; disabling it removes the device. No reload needed.
- The relay's match payload carries no scores, so results are win/loss only.

## Install

**Via HACS:** HACS → ⋮ → **Custom repositories** → add this repo, category **Integration**, install **R6 Data Relay**, restart Home Assistant.

**Manually:** copy `custom_components/r6_data_relay` into `<config>/custom_components/` and restart.

## Set up

Settings → **Devices & Services** → **Add Integration** → **R6 Data Relay**:

- **Base URL**: your relay, e.g. `https://r6-data-relay.ault`.
- **API token**: the relay's `API_SHARED_TOKEN`.
- **Verify SSL certificate**: turn this off if the relay's certificate comes from a CA Home Assistant doesn't trust (e.g. the internal `.ault` CA).

A wrong URL or token is reported on the form (`cannot_connect` / `invalid_auth`). If the token is rotated later, Home Assistant prompts for the new one.

Example automation:

```yaml
trigger:
  - trigger: state
    entity_id: binary_sensor.g2_esports_playing_now
    to: "on"
action:
  - action: notify.mobile_app_your_phone
    data:
      message: "G2 are live vs {{ state_attr(trigger.entity_id, 'opponent') }}"
```

## Development

Requires Python 3.14+ (matches current Home Assistant core).

```
python3 -m venv .venv
.venv/bin/pip install -r requirements_test.txt
.venv/bin/pytest tests/ -v
```

CI runs the tests, [hassfest](https://developers.home-assistant.io/docs/creating_integration_manifest/#validating-the-manifest), and (on pushes to `main`) the HACS validator.

Logging uses Home Assistant's standard `logging` (logger `custom_components.r6_data_relay`). Enable debug output with:

```yaml
logger:
  logs:
    custom_components.r6_data_relay: debug
```

The token is never logged and is redacted from diagnostics.
