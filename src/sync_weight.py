#!/usr/bin/env python3
"""
Garmin Connect → Statistics for Strava health (weight) sync

Usage:
  python sync_weight.py          # run the sync (default)
  python sync_weight.py auth     # interactive auth — generates a GARTH_TOKEN

Authentication is exclusively via GARTH_TOKEN (env var).
If GARTH_TOKEN is not set the sync exits with instructions to run `auth`.

Garmin returns weight in grams (e.g. 59189 = 59.189 kg).
"""

import logging
import os
import sys
from datetime import date, timedelta
from getpass import getpass
from pathlib import Path

import garth
import yaml
from garth.exc import GarthException, GarthHTTPError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration — driven by environment variables
# ---------------------------------------------------------------------------

CONFIG_PATH   = Path(os.environ.get("CONFIG_PATH", "/config/config.yaml"))
GARTH_TOKEN   = os.environ.get("GARTH_TOKEN", "")
LOOKBACK_DAYS = int(os.environ.get("LOOKBACK_DAYS", "2"))
WEIGHT_UNIT   = os.environ.get("WEIGHT_UNIT", "kg").lower()  # "kg" or "lbs"
DRY_RUN       = os.environ.get("DRY_RUN", "false").lower() == "true"


# ---------------------------------------------------------------------------
# Auth subcommand
# ---------------------------------------------------------------------------

def cmd_auth() -> None:
    """
    Interactive auth flow invoked by:
        docker compose exec garmin-health-to-sfs auth

    Handles standard login and MFA. Prints the resulting GARTH_TOKEN to
    stdout so the user can copy it into their .env file.
    """
    print("\n=== Garmin Connect Authentication ===")
    print("This will generate a GARTH_TOKEN for use in your .env file.\n")

    email    = input("Garmin email: ").strip()
    password = getpass("Garmin password: ")

    def mfa_prompt() -> str:
        return input("MFA code (check your phone / authenticator app): ").strip()

    print("\nLogging in to Garmin Connect...")
    try:
        garth.login(email, password, prompt=mfa_prompt)
    except GarthHTTPError as exc:
        if "429" in str(exc):
            print(
                "\n❌  Rate limited by Garmin (429 Too Many Requests).\n"
                "    Wait 15-30 minutes before trying again."
            )
        else:
            print(f"\n❌  Login failed: {exc}")
        sys.exit(1)
    except GarthException as exc:
        print(f"\n❌  Auth error: {exc}")
        sys.exit(1)

    token = garth.client.dumps()

    print("\n✅  Authentication successful!\n")
    print("Copy the token below and set it as GARTH_TOKEN in your docker/.env file:\n")
    print(f"GARTH_TOKEN={token}")
    print(
        "\nNote: this token is valid for approximately one year.\n"
        "Re-run `docker compose exec garmin-health-to-sfs auth` when it expires."
    )


# ---------------------------------------------------------------------------
# Sync — authenticate via GARTH_TOKEN
# ---------------------------------------------------------------------------

def authenticate() -> None:
    """Load and validate the GARTH_TOKEN from the environment."""
    if not GARTH_TOKEN:
        log.error(
            "GARTH_TOKEN is not set.\n\n"
            "Run the auth command to generate one:\n\n"
            "    docker compose exec garmin-health-to-sfs auth\n\n"
            "Then copy the printed token into your docker/.env file as GARTH_TOKEN=<token>"
        )
        sys.exit(1)

    log.info("Authenticating via GARTH_TOKEN")
    try:
        garth.client.loads(GARTH_TOKEN)
        _ = garth.client.username
        log.info("Token is valid")
    except GarthException as exc:
        log.error(
            "GARTH_TOKEN is invalid or expired (%s).\n\n"
            "Re-run the auth command to generate a new token:\n\n"
            "    docker compose exec garmin-health-to-sfs auth\n",
            exc,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Weight fetch
# ---------------------------------------------------------------------------

def grams_to_kg(grams: int | float) -> float:
    return round(grams / 1000.0, 2)


def kg_to_lbs(kg: float) -> float:
    return round(kg * 2.20462, 2)


def fetch_weight_entries(days: int) -> dict[str, float]:
    """
    Pull weight entries from Garmin Connect for the past `days` days.
    Returns {date_str: weight_value} in the unit specified by WEIGHT_UNIT.
    """
    start_date = date.today() - timedelta(days=days)
    log.info("Fetching weight data from %s (%d days back)", start_date.isoformat(), days)

    try:
        records = garth.WeightData.list(start_date.isoformat(), days)
    except Exception as exc:
        log.error("Garmin API error: %s", exc)
        raise

    entries: dict[str, float] = {}
    for r in records:
        if r.weight is None:
            continue

        weight_kg = grams_to_kg(r.weight)
        weight_value = kg_to_lbs(weight_kg) if WEIGHT_UNIT == "lbs" else weight_kg

        day_str = (
            r.calendar_date.isoformat()
            if hasattr(r.calendar_date, "isoformat")
            else str(r.calendar_date)
        )
        entries[day_str] = weight_value

    log.info("Retrieved %d weight entries from Garmin", len(entries))
    return entries


# ---------------------------------------------------------------------------
# YAML helpers
# ---------------------------------------------------------------------------

def load_config(path: Path) -> dict:
    if not path.exists():
        log.error("config.yaml not found at %s", path)
        sys.exit(1)
    with path.open("r") as fh:
        return yaml.safe_load(fh) or {}


def save_config(path: Path, config: dict) -> None:
    with path.open("w") as fh:
        yaml.dump(config, fh, default_flow_style=False, allow_unicode=True, sort_keys=False)
    log.info("Config saved to %s", path)


def merge_weight_history(
    config: dict,
    new_entries: dict[str, float],
) -> tuple[dict, int, int]:
    config.setdefault("general", {})
    config["general"].setdefault("athlete", {})
    existing: dict = dict(config["general"]["athlete"].get("weightHistory") or {})

    added = updated = 0
    for day, weight in new_entries.items():
        if day not in existing:
            added += 1
        elif existing[day] != weight:
            updated += 1
        existing[day] = weight

    config["general"]["athlete"]["weightHistory"] = dict(sorted(existing.items()))
    return config, added, updated


# ---------------------------------------------------------------------------
# Sync entry point
# ---------------------------------------------------------------------------

def cmd_sync() -> None:
    log.info("=== garmin-weight-sync starting ===")
    log.info("config  : %s", CONFIG_PATH)
    log.info("lookback: %d days", LOOKBACK_DAYS)
    log.info("unit    : %s", WEIGHT_UNIT)
    log.info("dry_run : %s", DRY_RUN)

    authenticate()

    entries = fetch_weight_entries(LOOKBACK_DAYS)
    if not entries:
        log.info("No weight data returned — nothing to write")
        return

    config = load_config(CONFIG_PATH)
    config, added, updated = merge_weight_history(config, entries)

    total = len(config["general"]["athlete"]["weightHistory"])
    log.info(
        "weightHistory: %d total entries (%d new, %d updated this run)",
        total, added, updated,
    )

    if DRY_RUN:
        log.info("[DRY RUN] Changes that would be written:")
        for day, weight in sorted(entries.items()):
            log.info("  %s -> %s %s", day, weight, WEIGHT_UNIT)
        log.info("[DRY RUN] config.yaml NOT modified")
    else:
        save_config(CONFIG_PATH, config)
        log.info("Sync complete")


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "sync"

    if command == "auth":
        cmd_auth()
    elif command == "sync":
        cmd_sync()
    else:
        print(f"Unknown command: {command!r}")
        print("Usage: sync_weight.py [auth|sync]")
        sys.exit(1)