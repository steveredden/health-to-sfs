#!/bin/sh
set -e

echo "=== Garmin Weight Sync container starting ==="
echo "Cron schedule: ${CRON_SCHEDULE}"
echo "Config path  : ${CONFIG_PATH}"
echo "Weight unit  : ${WEIGHT_UNIT}"
echo "Lookback days: ${LOOKBACK_DAYS}"

# Write environment variables to a file so cron can pick them up.
# (cron does not inherit the container's environment by default)
printenv | grep -v "^_=" > /etc/cron_env

# Build the crontab. We source /etc/cron_env before running the script so
# all env vars are available, and we redirect output to Docker's stdout/stderr.
CRON_JOB="${CRON_SCHEDULE} . /etc/cron_env; /usr/local/bin/python /app/sync_weight.py >> /proc/1/fd/1 2>> /proc/1/fd/2"

echo "${CRON_JOB}" > /etc/cron.d/garmin-sync
chmod 0644 /etc/cron.d/garmin-sync
crontab /etc/cron.d/garmin-sync

echo "Crontab installed:"
crontab -l

# Run the sync once immediately on startup so you don't have to wait for the
# first scheduled execution. Set SKIP_INITIAL_SYNC=true to disable this.
if [ "${SKIP_INITIAL_SYNC}" != "true" ]; then
    echo "Running initial sync on startup..."
    /usr/local/bin/python /app/sync_weight.py || echo "Initial sync failed — check logs"
fi

echo "Starting cron daemon..."
exec cron -f
