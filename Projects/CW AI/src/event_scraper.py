from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List

import requests
from bs4 import BeautifulSoup

try:
    from .config import VENUE_TO_ZONE, PATHS, APIS
except ImportError:
    from config import VENUE_TO_ZONE, PATHS, APIS

log = logging.getLogger(__name__)

TIMEOUT: int   = int(APIS.get("request_timeout_sec", 10))
HEADERS        = {
    "User-Agent": (
        "Mozilla/5.0 (academic research — 7COSC013W.1 Foundations of AI, "
        "University of Westminster)"
    )
}

def geocode_venue_to_zone(venue_name: str) -> str:
    v = venue_name.lower()
    for keyword, zone_id in VENUE_TO_ZONE.items():
        if keyword in v:
            return zone_id
    return "UNKNOWN"

def _scrape_lankaevents(url: str) -> List[dict]:
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    events = []
    for card in soup.select(".event-card"):
        try:
            name     = card.select_one(".event-title").get_text(strip=True)
            venue    = card.select_one(".event-venue").get_text(strip=True)
            date_str = card.select_one(".event-date").get_text(strip=True)
            time_el  = card.select_one(".event-time")
            start_t  = time_el.get_text(strip=True) if time_el else "19:00"
            cap_el   = card.select_one(".event-capacity")
            crowd    = (
                int(cap_el.get_text(strip=True).replace(",", ""))
                if cap_el else 1000
            )
            etype_el = card.select_one(".event-category")
            etype    = etype_el.get_text(strip=True).lower() if etype_el else "general"

            events.append({
                "name":               name,
                "venue":              venue,
                "zone":               geocode_venue_to_zone(venue),
                "date":               date_str,
                "start_time":         start_t,
                "expected_end_time":  "",
                "event_type":         etype,
                "crowd_estimate":     crowd,
                "source":             "lankaevents",
                "scraped_at":         datetime.now().isoformat(),
            })
        except AttributeError:
            continue

    return events

def _scrape_eventbrite(url: str) -> List[dict]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        events = []
        for card in soup.select("[data-testid='event-card']"):
            try:
                name  = card.select_one("h3").get_text(strip=True)
                venue = card.select_one("[data-testid='venue-name']")
                venue_str = venue.get_text(strip=True) if venue else ""
                date_el = card.select_one("[data-testid='event-start-date']")
                date_str = date_el.get_text(strip=True) if date_el else ""
                events.append({
                    "name":           name,
                    "venue":          venue_str,
                    "zone":           geocode_venue_to_zone(venue_str),
                    "date":           date_str,
                    "start_time":     "19:00",
                    "expected_end_time": "",
                    "event_type":     "general",
                    "crowd_estimate": 500,
                    "source":         "eventbrite",
                    "scraped_at":     datetime.now().isoformat(),
                })
            except Exception:
                continue
        return events
    except Exception as exc:
        log.warning("[SCRAPER] Eventbrite failed: %s", exc)
        return []

def _load_fallback() -> List[dict]:
    path = Path(str(PATHS["fallback_events"]))
    with path.open() as fh:
        return json.load(fh)

def get_upcoming_events(use_fallback_only: bool = False) -> List[dict]:
    if use_fallback_only:
        log.info("[SCRAPER] Using offline fallback events.")
        return _load_fallback()

    all_events: List[dict] = []

    try:
        le_events = _scrape_lankaevents(APIS["lankaevents_upcoming"])
        all_events.extend(le_events)
        log.info("[SCRAPER] LankaEvents: %d events scraped.", len(le_events))
    except Exception as exc:
        log.warning("[SCRAPER] LankaEvents failed (%s). Trying Eventbrite.", exc)

    try:
        eb_events = _scrape_eventbrite(APIS["eventbrite_colombo"])
        all_events.extend(eb_events)
        log.info("[SCRAPER] Eventbrite: %d events scraped.", len(eb_events))
    except Exception as exc:
        log.warning("[SCRAPER] Eventbrite failed (%s).", exc)

    if not all_events:
        log.warning("[SCRAPER] All live sources failed — loading fallback_events.json.")
        all_events = _load_fallback()

    return all_events

def validate_geocoding_precision(groundtruth_csv: str | Path) -> dict:
    import pandas as pd
    df = pd.read_csv(groundtruth_csv)
    df["predicted_zone"] = df["venue_name"].apply(geocode_venue_to_zone)
    df["correct"]        = df["predicted_zone"] == df["correct_zone"]

    n_total   = len(df)
    n_correct = int(df["correct"].sum())
    precision = n_correct / n_total if n_total > 0 else 0.0

    return {
        "precision":  precision,
        "n_correct":  n_correct,
        "n_total":    n_total,
        "details":    df[["event_name", "venue_name", "correct_zone",
                          "predicted_zone", "correct"]].to_dict("records"),
    }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    events = get_upcoming_events(use_fallback_only=True)
    print(f"Loaded {len(events)} events (fallback mode).")
    for e in events[:5]:
        print(f"  {e['name'][:40]:<40}  zone={e['zone']}  type={e['event_type']}")
