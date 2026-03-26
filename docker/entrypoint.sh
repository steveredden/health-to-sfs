#!/bin/sh
set -e

# ---------------------------------------------------------------------------
# Dispatch: allow `docker compose exec ... auth` to drop straight into the
# interactive auth flow without starting cron at all.
# ---------------------------------------------------------------------------
if [ "$1" = "auth" ]; then
    exec /usr/local/bin/python /app/sync_weight.py auth
fi

# ---------------------------------------------------------------------------
# Normal startup — run the cron daemon
# ---------------------------------------------------------------------------
echo "=== garmin-health-to-sfs starting ==="
echo "Cron schedule : ${CRON_SCHEDULE}"
echo "Config path   : ${CONFIG_PATH}"
echo "Weight unit   : ${WEIGHT_UNIT}"
echo "Lookback days : ${LOOKBACK_DAYS}"

# Warn clearly if no token is configured, but don't block startup —
# the cron job itself will print the instructions when it first runs.
if [ -z "${GARTH_TOKEN}" ]; then
    echo ""
    echo "⚠️  WARNING: GARTH_TOKEN is not set."
    echo "   The sync will not work until you authenticate."
    echo "   Run the following command to generate a token:"
    echo ""
    echo "       docker compose exec garmin-health-to-sfs auth"
    echo ""
    echo "   Then copy the printed GARTH_TOKEN into your .env file."
    echo ""
fi

# Write environment to file so cron inherits it (cron strips env by default)
printenv | grep -v "^_=" > /etc/cron_env

CRON_JOB="${CRON_SCHEDULE} . /etc/cron_env; /usr/local/bin/python /app/sync_weight.py sync >> /proc/1/fd/1 2>> /proc/1/fd/2"
echo "${CRON_JOB}" > /etc/cron.d/garmin-sync
chmod 0644 /etc/cron.d/garmin-sync
crontab /etc/cron.d/garmin-sync

echo "Crontab installed: ${CRON_SCHEDULE}"

# Run once immediately on startup (skip with SKIP_INITIAL_SYNC=true)
if [ "${SKIP_INITIAL_SYNC}" != "true" ] && [ -n "${GARTH_TOKEN}" ]; then
    echo "Running initial sync..."
    /usr/local/bin/python /app/sync_weight.py sync || echo "Initial sync failed — check logs"
fi

echo "Starting cron daemon..."
exec cron -f