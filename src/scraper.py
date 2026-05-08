import logging
from dataclasses import dataclass
from datetime import date
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

HKEXPRESS_API_URL = (
    "https://api.hkexpress.com/flt-booking-query/public/v1/availability/search"
)

BASE_HEADERS = {
    "accept": "*/*",
    "accept-language": "zh-TW,zh;q=0.9",
    "content-type": "application/json",
    "origin": "https://mybooking.hkexpress.com",
    "referer": "https://mybooking.hkexpress.com/",
    "priority": "u=1, i",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/147.0.0.0 Safari/537.36"
    ),
    "x-signature": "dummy",
}


@dataclass
class ScrapeResult:
    success: bool
    fare: Optional[float] = None
    flight_number: Optional[str] = None
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None
    error_message: Optional[str] = None


def _parse_cheapest_journey(journeys: list) -> Optional[dict]:
    valid = [j for j in journeys if j.get("display_item_amount") is not None]
    if not valid:
        return None
    best = min(valid, key=lambda j: j["display_item_amount"])
    segments = best.get("segment", [])
    flight_number = segments[0]["flight_number"] if segments else ""
    departure = best.get("departure_date_time", "")
    arrival = best.get("arrival_date_time", "")
    dep_time = departure[11:16] if len(departure) >= 16 else departure
    arr_time = arrival[11:16] if len(arrival) >= 16 else arrival
    return {
        "fare": float(best["display_item_amount"]),
        "flight_number": flight_number,
        "departure_time": dep_time,
        "arrival_time": arr_time,
    }


def scrape_prices(
    origin: str,
    destination: str,
    flight_date: date,
    adult_count: int,
    child_count: int,
    infant_count: int,
) -> ScrapeResult:
    payload = {
        "application_code": "IBE",
        "flights": [
            {
                "origin": origin,
                "destination": destination,
                "begin_date": flight_date.isoformat(),
            }
        ],
        "currency_code": "HKD",
        "promotion_code": "",
        "passengers": {
            "adult_count": adult_count,
            "infant_count": infant_count,
            "children_count": child_count,
        },
    }

    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                HKEXPRESS_API_URL, json=payload, headers=BASE_HEADERS
            )
    except httpx.RequestError as exc:
        return ScrapeResult(success=False, error_message=f"Request failed: {exc}")

    if response.status_code != 200:
        return ScrapeResult(
            success=False,
            error_message=f"HTTP {response.status_code}: {response.text[:200]}",
        )

    try:
        data = response.json()
    except Exception as exc:
        return ScrapeResult(success=False, error_message=f"JSON parse error: {exc}")

    trips = data.get("trip", [])
    if not trips:
        return ScrapeResult(success=False, error_message="API returned no trip data")

    journey_result = _parse_cheapest_journey(trips[0].get("journey", []))
    if journey_result is None:
        return ScrapeResult(success=False, error_message="No valid journeys found")

    return ScrapeResult(success=True, **journey_result)
