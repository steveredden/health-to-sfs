#!/usr/bin/env python3
"""
Garmin Connect → Statistics for Strava weight sync

Fetches recent weight entries from Garmin Connect via garth and merges
them into the statistics-for-strava config.yaml under:

    general:
      athlete:
        weightHistory:
          "YYYY-MM-DD": <weight_in_kg_or_lbs>

Garmin returns weight in **grams** (e.g. 59189 = 59.189 kg).
"""

import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import garth
import yaml
from garth.exc import GarthException

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration — all driven by environment variables
# ---------------------------------------------------------------------------

CONFIG_PATH     = Path(os.environ.get("CONFIG_PATH", "/config/config.yaml"))
GARTH_HOME      = os.environ.get("GARTH_HOME", "/garth_session")
GARMIN_EMAIL    = os.environ.get("GARMIN_EMAIL", "")
GARMIN_PASSWORD = os.environ.get("GARMIN_PASSWORD", "")

LOOKBACK_DAYS   = int(os.environ.get("LOOKBACK_DAYS", "2"))
# "kg" or "lbs" — must match the unitSystem in statistics-for-strava
WEIGHT_UNIT     = os.environ.get("WEIGHT_UNIT", "kg").lower()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def authenticate() -> None:
    """
    Authenticate with Garmin Connect.

    Priority order:
      1. Saved session on disk at GARTH_HOME  (from a previous login)
      3. GARMIN_EMAIL + GARMIN_PASSWORD  (credentials, saves session to disk)
    """

    # 1. Saved session
    session_path = Path(GARTH_HOME)
    if session_path.exists() and any(session_path.iterdir()):
        log.info("Resuming saved session from %s", GARTH_HOME)
        try:
            garth.resume(GARTH_HOME)
            # Use connectapi instead of .username — less likely to false-fail
            garth.connectapi("/userprofile-service/userprofile/personal-information")
            log.info("Saved session is valid")
            return
        except GarthException:
            log.warning("Saved session expired")

    # 2. Credentials
    if GARMIN_EMAIL and GARMIN_PASSWORD:
        log.info("Logging in with GARMIN_EMAIL credentials")
        garth.login(GARMIN_EMAIL, GARMIN_PASSWORD)
        session_path.mkdir(parents=True, exist_ok=True)
        garth.save(GARTH_HOME)
        log.info("Login successful; session saved to %s for future runs", GARTH_HOME)
        return

    log.error(
        "No authentication method available. "
        "Set GARMIN_EMAIL + GARMIN_PASSWORD"
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Weight fetch
# ---------------------------------------------------------------------------

def grams_to_kg(grams: int | float) -> float:
    """Convert Garmin's gram value to kilograms, rounded to 2dp."""
    return round(grams / 1000.0, 2)


def kg_to_lbs(kg: float) -> float:
    return round(kg * 2.20462, 2)


def fetch_weight_entries(days: int) -> dict[str, float]:
    """
    Pull weight entries from Garmin Connect for the past `days` days.

    Returns {date_str: weight_value} where weight_value is in the unit
    specified by WEIGHT_UNIT ("kg" or "lbs").

    Garmin WeightData fields used:
      - calendar_date  : datetime.date  → used as the dict key
      - weight         : int (grams)    → converted to kg / lbs
    """
    start_date = date.today() - timedelta(days=days)
    log.info(
        "Fetching weight data from %s (%d days back)",
        start_date.isoformat(),
        days,
    )

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

        # calendar_date is a datetime.date object; guard against string variants
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
        yaml.dump(
            config,
            fh,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
    log.info("Config saved to %s", path)


def merge_weight_history(
    config: dict,
    new_entries: dict[str, float],
) -> tuple[dict, int, int]:
    """
    Merge new_entries into config['general']['athlete']['weightHistory'].

    New dates are added; existing dates are overwritten with the fresh value.
    Returns (updated_config, added_count, updated_count).
    """
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

    # Keep sorted by date for readability
    config["general"]["athlete"]["weightHistory"] = dict(sorted(existing.items()))
    return config, added, updated


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    log.info("=== garmin-weight-sync starting ===")
    log.info("config  : %s", CONFIG_PATH)
    log.info("lookback: %d days", LOOKBACK_DAYS)
    log.info("unit    : %s", WEIGHT_UNIT)

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
        total,
        added,
        updated,
    )

    save_config(CONFIG_PATH, config)
    log.info("Sync complete")


if __name__ == "__main__":
    main()
