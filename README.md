# 📋 health-to-sfs

A lightweight, containerized **FastAPI** ingest engine that bridges Apple Health data to a localized YAML configuration file. Designed specifically for tracking weight history and integrating with Strava-related statistics.

## 🚀 Overview

This project provides a secure, internet-facing endpoint for Apple Shortcuts to "dump" health samples. It handles deduplication, data validation, and nested YAML updates while remaining invisible behind a Traefik reverse proxy.

* **Zero-Database:** Uses your existing strava_stats.yaml as the source of truth.
* **Idempotent:** Safely send the last 7 days of data; only new dates are appended.
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
Create a .env file in the root directory:

```sh
APP_PORT=9055
API_SECRET=your_secure_token_here
CONFIG_PATH=/config/strava_stats.yaml
```

### 2. Deployment
Ensure your target YAML file exists on the host machine, then fire up the stack:

```sh
docker compose up -d --build
```

### 3. Traefik Integration
The docker-compose.yml includes labels for automatic routing. Ensure you have a Docker network named traefik_network.

---

## 📲 Shortcut Integration

To send data from your iPhone, configure a **Get Contents of URL** action in Apple Shortcuts:

* **Method:** POST
* **Headers:** x-api-key: your_secure_token_here
* **Request Body:** JSON
* **Data Structure:**
{
  "data": {
    "2026-03-31": "185.2",
    "2026-03-30": "184.8"
  }
}

---

## 🔒 Security Features

* **Generic Errors:** Returns a flat 400 Bad Request for data errors to prevent leaking Pydantic model structures.
* **Header Shield:** Rejects any request without a valid x-api-key with a 401 Unauthorized.
* **No Docs:** Swagger (/docs) and ReDoc (/redoc) are disabled in production.

---

## 📄 License
MIT