# 📋 health-to-sfs

> [!NOTE]
> This app was mostly vibe coded

A lightweight, containerized **FastAPI** ingest engine that bridges Apple Health data to a localized YAML configuration file. Designed specifically for tracking weight history and integrating with [Statistics for Strava](https://github.com/robiningelbrecht/statistics-for-strava)

> [!NOTE]
> This app is in no way affiliated with or part of the official Strava software suite, nor [Statistics for Strava](https://github.com/robiningelbrecht/statistics-for-strava)

## 🚀 Overview

This project provides a secure, internet-facing endpoint for Apple Shortcuts to "dump" health samples. It handles deduplication, data validation, and nested YAML updates while remaining invisible behind a Traefik reverse proxy.

* **Zero-Database:** Uses your existing config.yaml as the source of truth for weight.
* **Idempotent:** Safely send the last *n* days of data; only new dates are appended.
* **Secure:** Enforces header-based API keys and masks internal validation errors from the public.
* **Tiny Footprint:** Built on python:alpine (~50MB image).

---

## 📲 Shortcut Integration

The project relies on your weight being present in the Apple Health (HealthKit) application.  Firstly, you'll need an iPhone.  Secondly, you'll need a smart scale or application (e.g. Garmin) that writes to the Apple Health app.

Start with this shortcut (open it on your iPhone) to start retrieving health data from the Health app, and `POST` it to a URL:

https://www.icloud.com/shortcuts/7dde7305c41a4a1f90e1817e5d12f37f

![shortcut-screenshot](docs/assets/images/screenshot-health-to-sfs.png)

This project, running as a container, opens a port and listens for new weight data...

## ⚙️ Setup & Installation

### 1. Environment Configuration
Create or update a .env file in the directory that you host statistics-for-strava, and add the following keys:

```sh
AUTH_USER: admin  #feel free to change
API_SECRET: your_secure_token_here  #feel free to change
CONFIG_PATH: /config/config-weight.yaml  #consider breaking out your weight into a separate yaml
CONFLICT_RESOLUTION: MIN  #MIN, MAX, or AVG - What to do when multiple weights are found for the same day
OUTLIER_THRESHOLD: 0.15   #warning mechanism to warn if the data is this % (0-1) different than other values
```

### 2. Deployment
Add the health-to-sfs service to your existing `docker-compose` yaml.  Ensure you map the same `./config` volume to the new service:

```sh
...

services:
  app:
    image: robiningelbrecht/strava-statistics:v4.7.5
    container_name: statistics-for-strava
    restart: unless-stopped
    volumes:
      - ./config:/var/www/config/app    #LOCAL MOUNT NEEDS TO MATCH BELOW
...

  health-to-sfs:
    image: ghcr.io/steveredden/health-to-sfs:latest
    container_name: health-to-sfs
    restart: unless-stopped
    volumes:
      - ./config:/config                #LOCAL MOUNT NEEDS OT MATCH ABOVE
    env_file:
      - .env
    environment:
      AUTH_USER: ${AUTH_USER}
      API_SECRET: ${API_SECRET}
      CONFIG_PATH: "/config/config-athlete.yaml"
      CONFLICT_RESOLUTION: MIN
      OUTLIER_THRESHOLD: 0.15
    networks:
      - frontend
    ports:
      - 9005:8080
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://127.0.0.1:8080/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
...
```

---

## Pangolin

Set up your Pangolin instance to allow basic auth, using the `AUTH_USER` and `API_SECRET` from your configuration

![pangolin-screenshot](docs/assets/images/pangolin-auth.png)
