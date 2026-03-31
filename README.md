# 📋 health-to-sfs

A lightweight, containerized **FastAPI** ingest engine that bridges Apple Health data to a localized YAML configuration file. Designed specifically for tracking weight history and integrating with [Statistics for Strava](https://github.com/robiningelbrecht/statistics-for-strava)

## 🚀 Overview

This project provides a secure, internet-facing endpoint for Apple Shortcuts to "dump" health samples. It handles deduplication, data validation, and nested YAML updates while remaining invisible behind a Traefik reverse proxy.

* **Zero-Database:** Uses your existing config.yaml as the source of truth for weight.
* **Idempotent:** Safely send the last *n* days of data; only new dates are appended.
* **Secure:** Enforces header-based API keys and masks internal validation errors from the public.
* **Tiny Footprint:** Built on python:alpine (~50MB image).

---

## 🛠 Tech Stack

| Component | Technology |
| :--- | :--- |
| **Framework** | [FastAPI](https://fastapi.tiangolo.com/) |
| **Server** | [Uvicorn](https://www.uvicorn.org/) (ASGI) |
| **Parser** | [ruamel.yaml](https://yaml.readthedocs.io/en/latest/) |
| **Container** | Docker + Docker Compose |
| **Proxy** | Traefik (HTTPS/TLS Termination) |

---

## ⚙️ Setup & Installation

### 1. Environment Configuration
Create or update a .env file in the directory that you host statistics-for-strava, and add the following keys:

```sh
API_SECRET=your_secure_token_here
CONFIG_PATH=/config/config-athlete.yaml
```

### 2. Deployment
Add the health-to-sfs service to your existing `docker-compose` yaml.  Ensure you map the same `./config` volume to the new service:

```sh
...

services:
  app:
    image: robiningelbrecht/strava-statistics:v4.7.4
    container_name: statistics-for-strava
    restart: unless-stopped
    volumes:
      - ./config:/var/www/config/app
...

  health-to-sfs:
    image: ghcr.io/steveredden/health-to-sfs:v0.0.1
    container_name: health-to-sfs
    restart: unless-stopped
    volumes:
      - ./config:/config
    environment:
      API_SECRET: ${API_SECRET}
      CONFIG_PATH: "/config/config-athlete.yaml"
    networks:
      - frontend
    ports:
      - 9005:8080
...
```

---

## 📲 Shortcut Integration

The project relies on your weight being present in the Apple Health (HealthKit) application.

A shortcut has been created to get you started:

https://www.icloud.com/shortcuts/c5564d7df29b4454a6d9d7816fce8bc2

![shortcut-screenshot](docs/assets/images/screenshot-health-to-sfs.png)

Only the first two text fields need to be configured.  Fill them in your appropriate URL and chosen API Secret.

Make sure to retain the `/ingest` path in the URL
