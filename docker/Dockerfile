FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        cron \
        tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN apt update && apt install -y curl \
 && rm -rf /var/lib/apt/lists/*

RUN curl -Ls https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

COPY src/sync_weight.py .
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Cron schedule — default: every day at 03:00
ENV CRON_SCHEDULE="0 3 * * *"

# Sync settings
ENV CONFIG_PATH="/config/config.yaml"
ENV LOOKBACK_DAYS="2"
ENV WEIGHT_UNIT="kg"
ENV DRY_RUN="false"

ENTRYPOINT ["/usr/bin/tini", "--", "/entrypoint.sh"]