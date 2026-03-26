# garmin-health-to-sfs

A Docker sidecar that syncs your **Garmin Connect weight history** into the
[statistics-for-strava](https://github.com/robiningelbrecht/statistics-for-strava)
`config.yaml` on a cron schedule.

Uses [garth](https://github.com/matin/garth) for Garmin authentication.

---


## Quick start

### 1. Configure your environment

Copy `.env.example` to `.env` and fill in the non-auth values:

```bash
cp docker/.env.example docker/.env
```

Leave `GARTH_TOKEN` blank for now — you'll fill it in after step 3.

### 2. Start the container

```bash
make dev
```

The container will start successfully even without a token. It will print a
warning and skip the initial sync until a token is provided.

### 3. Authenticate with Garmin Connect

```bash
make auth
# or directly:
docker compose exec garmin-health-to-sfs auth
```

This runs an interactive prompt inside the running container:

```
=== Garmin Connect Authentication ===

Garmin email: you@example.com
Garmin password:
MFA code (if prompted): 123456

✅  Authentication successful!

Copy the token below and set it as GARTH_TOKEN in your docker/.env file:

GARTH_TOKEN=eyJvYXV0aF90b2tlbi...
```

Copy the `GARTH_TOKEN=...` line into `docker/.env`, then restart:

```bash
docker compose -f docker/docker-compose.yml restart garmin-health-to-sfs
```

### 4. Trigger a manual sync to verify

```bash
make sync
```

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `GARTH_TOKEN` | *(required)* | Token from `make auth`. Valid ~1 year. |
| `CONFIG_PATH` | `/config/config.yaml` | Path to statistics-for-strava config inside container |
| `LOOKBACK_DAYS` | `2` | Days of weight history to fetch each run |
| `WEIGHT_UNIT` | `kg` | `kg` or `lbs` — must match statistics-for-strava's `unitSystem` |
| `CRON_SCHEDULE` | `0 3 * * *` | Standard cron expression (default: 3am daily) |
| `DRY_RUN` | `false` | Log what would change without writing the file |
| `SKIP_INITIAL_SYNC` | `false` | Skip the sync that runs on container startup |

---

## What the YAML looks like after a sync

```yaml
general:
  athlete:
    weightHistory:
      "2025-06-06": 59.19
      "2025-06-07": 59.19
```

---

## Token expiry

garth OAuth tokens last approximately one year. When yours expires, re-run:

```bash
make auth
```

Update `GARTH_TOKEN` in `docker/.env` and restart the container.

---

## Troubleshooting

**429 Too Many Requests during `make auth`**
Garmin rate-limits SSO login attempts. Wait 15–30 minutes and try again.

**`No weight data returned`**
Garmin only returns entries that were explicitly logged (via the Garmin app,
a connected scale, or a wearable). Check that you have entries in the
Garmin Connect app for the lookback window.

**statistics-for-strava doesn't reflect new weights**
The app reads `config.yaml` during its next import/build cycle. Trigger one
manually or wait for the next scheduled run.