# garmin-weight-sync

A lightweight Docker sidecar that syncs your **Garmin Connect weight history**
into the [statistics-for-strava](https://github.com/robiningelbrecht/statistics-for-strava)
`config.yaml` on a configurable cron schedule.

It uses [garth](https://github.com/matin/garth) for Garmin authentication and
the `garth.WeightData` API to pull measurements.

---

## How it works

1. On startup (and then on the cron schedule) the container:
   - Authenticates with Garmin Connect via garth
   - Fetches weight entries for the past `LOOKBACK_DAYS` days
   - Reads your `config.yaml`
   - Merges the entries into `general.athlete.weightHistory` (new dates are
     added; existing dates are updated)
   - Writes the file back

2. statistics-for-strava will pick up the updated `weightHistory` the next
   time it runs its import/build cycle.

---

## Quick start

### 1. Set your Garmin credentials in your .env file to be consumed by you docker-compose.yml

```yaml
GARMIN_EMAIL: "you@example.com"
GARMIN_PASSWORD: "yourpassword"
```

The key requirement is that both services share the same `./config` volume so
the sync container can write to the same `config.yaml` that statistics-for-strava reads.

### 3. Set your environment variables

At minimum you need one auth method:

| Variable | Description |
|---|---|
| `GARTH_TOKEN` | **Recommended.** Base64 token from `garth.client.dumps()` |
| `GARMIN_EMAIL` + `GARMIN_PASSWORD` | Alternative; garth saves OAuth session to `GARTH_HOME` |

Other variables:

| Variable | Default | Description |
|---|---|---|
| `CONFIG_PATH` | `/config/config.yaml` | Path to the statistics-for-strava config file inside the container |
| `LOOKBACK_DAYS` | `2` | Days of weight history to fetch |
| `WEIGHT_UNIT` | `kg` | `kg` or `lbs` — must match what statistics-for-strava expects |
| `CRON_SCHEDULE` | `0 3 * * *` | Standard cron expression |

### 4. Build and run

```bash
docker compose -f docker-compose.addon.yml build
docker compose -f docker-compose.addon.yml up -d
docker compose logs -f garmin-weight-sync
```

---

## What the YAML looks like after sync

```yaml
general:
  athlete:
    weightHistory:
      "2025-01-05": 83.4
      "2025-01-12": 82.9
      "2025-02-01": 82.1
```

This is the exact format statistics-for-strava uses for `general.athlete.weightHistory`
(date strings as keys, weight in kg as values).

---

## Troubleshooting

**`No weight entries returned from Garmin`**
Garmin Connect only returns weight entries that were explicitly logged (via
the Garmin app, a Garmin scale, or a connected device). If you haven't logged
weight in the lookback window, this is expected.

**statistics-for-strava doesn't pick up new weights**
The app reads `config.yaml` during its import/build run. Trigger a new build
(`docker compose exec app bin/console app:strava:build-files`) or wait for
the next scheduled import.
