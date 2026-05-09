import random
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

import httpx
from fake_useragent import UserAgent
from patchright.sync_api import sync_playwright


@dataclass
class Flight:
    flight_number: str
    departure_time: str
    arrival_time: str
    fare: float


@dataclass
class ScrapeResult:
    success: bool
    error_message: Optional[str] = None
    results: list[Flight] = field(default_factory=list)


def _parse_hkexpress_response(data: dict) -> ScrapeResult:
    journeys = [
        j
        for trip in data.get("trip", [])
        for j in trip.get("journey", [])
        if j.get("display_item_amount")
    ]

    if not journeys:
        return ScrapeResult(
            success=False, error_message="API returned no valid trip data."
        )

    results = []
    for j in journeys:
        dep, arr = j.get("departure_date_time", ""), j.get("arrival_date_time", "")
        results.append(
            Flight(
                fare=float(j["display_item_amount"]),
                flight_number=j.get("segment", [{}])[0].get("flight_number", ""),
                departure_time=dep[11:16] if len(dep) > 15 else dep,
                arrival_time=arr[11:16] if len(arr) > 15 else arr,
            )
        )

    return ScrapeResult(success=True, results=results)


def scrape_prices_advanced(
    origin: str, destination: str, flight_date: date
) -> ScrapeResult:
    try:
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=Path("patchright_profile").absolute(),
                channel="chrome",
                headless=False,
                no_viewport=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            try:
                page = ctx.new_page()
                page.goto("https://www.hkexpress.com/zh-HK", timeout=60000)
                page.locator("#__next").wait_for(state="attached", timeout=60000)

                for _ in range(random.randint(3, 7)):
                    page.mouse.move(
                        random.randint(0, 800),
                        random.randint(0, 600),
                        steps=random.randint(5, 15),
                    )
                    page.mouse.wheel(0, random.randint(-100, 100))
                    page.wait_for_timeout(random.randint(1500, 3000))

                ch = page.evaluate("""
                        () => navigator.userAgentData ? {
                            brands: navigator.userAgentData.brands.map(b => `"${b.brand}";v="${b.version}"`).join(', '),
                            mobile: navigator.userAgentData.mobile ? "?1" : "?0",
                            platform: `"${navigator.userAgentData.platform}"`
                        } : {}
                    """)

                resp = page.request.post(
                    "https://api.hkexpress.com/w/flt-booking-query/public/v1/availability/search",
                    headers={
                        "Accept": "*/*",
                        "Accept-Language": "zh-TW,zh;q=0.9",
                        "Content-Type": "application/json",
                        "Origin": "https://mybooking.hkexpress.com",
                        "Referer": "https://mybooking.hkexpress.com/",
                        "User-Agent": page.evaluate("navigator.userAgent"),
                        "sec-ch-ua": ch.get("brands", ""),
                        "sec-ch-ua-mobile": ch.get("mobile", ""),
                        "sec-ch-ua-platform": ch.get("platform", ""),
                        "Sec-Fetch-Dest": "empty",
                        "Sec-Fetch-Mode": "cors",
                        "Sec-Fetch-Site": "same-site",
                    },
                    data={
                        "application_code": "IBE",
                        "currency_code": "HKD",
                        "promotion_code": "",
                        "flights": [
                            {
                                "origin": origin,
                                "destination": destination,
                                "begin_date": flight_date.isoformat(),
                            }
                        ],
                        "passengers": {
                            "adult_count": 1,
                            "infant_count": 0,
                            "children_count": 0,
                        },
                    },
                )

                if not resp.ok:
                    return ScrapeResult(
                        success=False,
                        error_message=f"HTTP {resp.status}: {resp.text()[:200]}",
                    )
                return _parse_hkexpress_response(resp.json())

            finally:
                ctx.close()
    except Exception as exc:
        return ScrapeResult(success=False, error_message=f"Playwright Error: {exc}")


def scrape_prices(origin: str, destination: str, flight_date: date) -> ScrapeResult:
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                "https://api.hkexpress.com/flt-booking-query/public/v1/availability/search",
                json={
                    "application_code": "IBE",
                    "currency_code": "HKD",
                    "promotion_code": "",
                    "flights": [
                        {
                            "origin": origin,
                            "destination": destination,
                            "begin_date": flight_date.isoformat(),
                        }
                    ],
                    "passengers": {
                        "adult_count": 1,
                        "infant_count": 0,
                        "children_count": 0,
                    },
                },
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

        if resp.status_code != 200:
            return ScrapeResult(
                success=False,
                error_message=f"HTTP {resp.status_code}: {resp.text[:200]}",
            )
        return _parse_hkexpress_response(resp.json())

    except Exception as exc:
        return ScrapeResult(success=False, error_message=f"HTTPX Error: {exc}")
