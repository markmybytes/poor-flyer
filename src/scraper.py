from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx
from fake_useragent import UserAgent
from patchright.sync_api import sync_playwright

HKEXPRESS_URL = "https://www.hkexpress.com/"

HKEXPRESS_API_URL = (
    "https://api.hkexpress.com/w/flt-booking-query/public/v1/availability/search"
)


@dataclass
class Flight:
    flight_number: Optional[str] = None
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None
    fare: Optional[float] = None


@dataclass
class ScrapeResult:
    success: bool
    error_message: Optional[str] = None
    results: list[Flight] = field(default_factory=list)


def _get_cookie() -> dict:
    with sync_playwright() as playwright:
        browser_context = playwright.chromium.launch_persistent_context(
            user_data_dir=Path("patchright_profile").absolute(),
            channel="chromium",
            headless=True,
            no_viewport=True,
            args=["--disable-blink-features=AutomationControlled"],
        )

        try:
            page = browser_context.new_page()

            page.goto("https://www.hkexpress.com/zh-HK", timeout=60 * 1000)
            page.locator("#__next").wait_for(state="attached", timeout=60 * 1000)
            page.goto(HKEXPRESS_URL)
            page.locator("#hkexpress").wait_for(state="attached", timeout=60 * 1000)

            cookie_list = browser_context.cookies()
        finally:
            browser_context.close()

    def domain_matches(hostname: str, cookie_domain: str) -> bool:
        clean_domain = (cookie_domain or "").lstrip(".")
        if not clean_domain:
            return False
        return hostname == clean_domain or hostname.endswith(f".{clean_domain}")

    return {
        cookie.get("name"): cookie.get("value")
        for cookie in cookie_list
        if cookie.get("name")
        and domain_matches(
            urlparse(HKEXPRESS_URL).hostname or "", cookie.get("domain") or ""
        )
    }


def scrape_prices(origin: str, destination: str, flight_date: date) -> ScrapeResult:
    """Scrapes the lowest fare for a given route and date."""

    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                HKEXPRESS_API_URL,
                json={
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
                        "adult_count": 1,
                        "infant_count": 0,
                        "children_count": 0,
                    },
                },
                cookies=_get_cookie(),
                headers={
                    "accept": "*/*",
                    "accept-language": "zh-TW,zh;q=0.9",
                    "content-type": "application/json",
                    "origin": "https://mybooking.hkexpress.com",
                    "referer": "https://mybooking.hkexpress.com/",
                    "priority": "u=1, i",
                    "sec-fetch-dest": "empty",
                    "sec-fetch-mode": "cors",
                    "sec-fetch-site": "same-site",
                    "user-agent": UserAgent().chrome,
                    "x-signature": "dummy",
                },
            )

        if response.status_code != 200:
            return ScrapeResult(
                success=False,
                error_message=f"HTTP {response.status_code}: {response.text[:200]}",
            )

        trips = response.json().get("trip", [])

        if not trips:
            return ScrapeResult(
                success=False, error_message="API returned no trip data."
            )

        valid_journeys = [
            journey
            for journey in trips[0].get("journey", [])
            if journey.get("display_item_amount") is not None
        ]

        if not valid_journeys:
            return ScrapeResult(success=False, error_message="No valid journeys found.")

        results: list[Flight] = []
        for journey in valid_journeys:
            segments = journey.get("segment", [])
            departure = journey.get("departure_date_time", "")
            arrival = journey.get("arrival_date_time", "")

            results.append(
                Flight(
                    fare=float(journey["display_item_amount"]),
                    flight_number=segments[0]["flight_number"] if segments else "",
                    departure_time=(
                        departure[11:16] if len(departure) > 15 else departure
                    ),
                    arrival_time=arrival[11:16] if len(arrival) > 15 else arrival,
                )
            )
        return ScrapeResult(success=True, results=results)

    except Exception as exc:
        return ScrapeResult(success=False, error_message=f"Error occurred: {exc}")
