FROM python:3.12-slim

LABEL maintainer="you"
LABEL description="Syncs Garmin Connect weight data into statistics-for-strava config YAML"

# Install cron + tini (for proper PID-1 signal handling)
RUN apt-get update && apt-get install -y --no-install-recommends \
        cron \
        tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy sync script
COPY src/sync_weight.py .

# Copy the cron entrypoint
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Default cron schedule env var (can be overridden at runtime)
# Default: every day at 03:00
ENV CRON_SCHEDULE="0 3 * * *"

# Garmin auth
ENV GARTH_TOKEN=""
ENV GARTH_HOME="/garth_session"
ENV GARMIN_EMAIL=""
ENV GARMIN_PASSWORD=""

# Sync config
ENV CONFIG_PATH="/config/config.yaml"
ENV LOOKBACK_DAYS="90"
ENV WEIGHT_UNIT="kg"
ENV DRY_RUN="false"

# Persisted garth session directory
VOLUME ["/garth_session"]

ENTRYPOINT ["/usr/bin/tini", "--", "/entrypoint.sh"]
