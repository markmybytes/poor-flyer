import logging
import random
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import httpx
from fake_useragent import UserAgent
from patchright.sync_api import sync_playwright

logger = logging.getLogger(__name__)


@dataclass
class Flight:
    flight_number: str
    departure_at: datetime | None
    arrival_at: datetime | None
    fare: float
    currency: str


@dataclass
class FlightQuery:
    origin: str
    destination: str
    flight_date: date


@dataclass
class ScrapeResult:
    success: bool
    error_message: str | None = None
    results: list[Flight] = field(default_factory=list)


def _parse_hkexpress_response(data: dict) -> list[ScrapeResult]:
    """Parse the API response into one ScrapeResult per requested trip leg."""
    output: list[ScrapeResult] = []

    for trip in data.get('trip', []):
        journeys = [j for j in trip.get('journey', []) if j.get('display_item_amount')]
        if not journeys:
            output.append(
                ScrapeResult(
                    success=False,
                    error_message='API returned no valid journey data for leg.',
                )
            )
            continue

        output.append(
            ScrapeResult(
                success=True,
                results=[
                    Flight(
                        fare=float(j['display_item_amount']),
                        currency=j.get('fare', {}).get('currency_code', 'HKD'),
                        flight_number=((j.get('segment') or [{}])[0].get('flight_number', '')),
                        departure_at=datetime.fromisoformat(
                            f'{j["departure_date_time"]}'
                            f'{(j.get("segment") or [{}])[0].get("departure_timezone", "")}'
                        ),
                        arrival_at=datetime.fromisoformat(
                            f'{j["arrival_date_time"]}'
                            f'{(j.get("segment") or [{}])[0].get("arrival_timezone", "")}'
                        ),
                    )
                    for j in journeys
                ],
            )
        )

    if not output:
        return [ScrapeResult(success=False, error_message='API returned no trip data.')]

    return output


def scrape_prices_advanced(
    queries: list[FlightQuery], currency_code: str = 'HKD'
) -> list[ScrapeResult]:
    logger.info(
        'Starting advanced scrape for %d routes with currency=%s', len(queries), currency_code
    )
    try:
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=Path('patchright_profile').absolute(),
                channel='chrome',
                headless=False,
                no_viewport=True,
                args=['--disable-blink-features=AutomationControlled'],
            )
            try:
                page = ctx.new_page()
                page.goto('https://www.hkexpress.com/zh-HK', timeout=60000)
                page.locator('#__next').wait_for(state='attached', timeout=60000)

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
                            brands: navigator.userAgentData.brands
                                .map(b => `"${b.brand}";v="${b.version}"`).join(', '),
                            mobile: navigator.userAgentData.mobile ? "?1" : "?0",
                            platform: `"${navigator.userAgentData.platform}"`
                        } : {}
                    """)

                resp = page.request.post(
                    'https://api.hkexpress.com/w/flt-booking-query/public/v1/availability/search',
                    headers={
                        'Accept': '*/*',
                        'Accept-Language': 'zh-TW,zh;q=0.9',
                        'Content-Type': 'application/json',
                        'Origin': 'https://mybooking.hkexpress.com',
                        'Referer': 'https://mybooking.hkexpress.com/',
                        'User-Agent': page.evaluate('navigator.userAgent'),
                        'sec-ch-ua': ch.get('brands', ''),
                        'sec-ch-ua-mobile': ch.get('mobile', ''),
                        'sec-ch-ua-platform': ch.get('platform', ''),
                        'Sec-Fetch-Dest': 'empty',
                        'Sec-Fetch-Mode': 'cors',
                        'Sec-Fetch-Site': 'same-site',
                    },
                    data={
                        'application_code': 'IBE',
                        'currency_code': currency_code,
                        'promotion_code': '',
                        'flights': [
                            {
                                'origin': q.origin,
                                'destination': q.destination,
                                'begin_date': q.flight_date.isoformat(),
                            }
                            for q in queries
                        ],
                        'passengers': {
                            'adult_count': 1,
                            'infant_count': 0,
                            'children_count': 0,
                        },
                    },
                )

                if not resp.ok:
                    msg = f'HTTP {resp.status}: {resp.text()[:200]}'
                    return [ScrapeResult(success=False, error_message=msg)] * len(queries)

                results = _parse_hkexpress_response(resp.json())
                # Pad with error entries if the API returned fewer trips than expected
                while len(results) < len(queries):
                    results.append(
                        ScrapeResult(success=False, error_message='No data returned for leg.')
                    )
                return results[: len(queries)]

            finally:
                ctx.close()
    except Exception as exc:
        logger.exception('Advanced scrape failed: routes=%d', len(queries))
        return [ScrapeResult(success=False, error_message=f'Playwright Error: {exc}')] * len(
            queries
        )


def scrape_prices(queries: list[FlightQuery], currency_code: str = 'HKD') -> list[ScrapeResult]:
    logger.info(
        'Starting flight scrape for %d routes with currency %s', len(queries), currency_code
    )
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                'https://api.hkexpress.com/flt-booking-query/public/v1/availability/search',
                json={
                    'application_code': 'IBE',
                    'currency_code': currency_code,
                    'promotion_code': '',
                    'flights': [
                        {
                            'origin': q.origin,
                            'destination': q.destination,
                            'begin_date': q.flight_date.isoformat(),
                        }
                        for q in queries
                    ],
                    'passengers': {
                        'adult_count': 1,
                        'infant_count': 0,
                        'children_count': 0,
                    },
                },
                headers={
                    'accept': '*/*',
                    'accept-language': 'zh-TW,zh;q=0.9',
                    'content-type': 'application/json',
                    'origin': 'https://mybooking.hkexpress.com',
                    'referer': 'https://mybooking.hkexpress.com/',
                    'priority': 'u=1, i',
                    'sec-fetch-dest': 'empty',
                    'sec-fetch-mode': 'cors',
                    'sec-fetch-site': 'same-site',
                    'user-agent': UserAgent().chrome,
                    'x-signature': 'dummy',
                },
            )

        if resp.status_code != 200:
            msg = f'HTTP {resp.status_code}: {resp.text[:200]}'
            logger.warning('HKExpress API returned error: %s', msg)
            return [ScrapeResult(success=False, error_message=msg)] * len(queries)

        logger.debug('HKExpress API response received, parsing results')
        results = _parse_hkexpress_response(resp.json())
        # Pad with error entries if the API returned fewer trips than expected
        while len(results) < len(queries):
            results.append(ScrapeResult(success=False, error_message='No data returned for leg.'))

        successful_results = sum(1 for r in results if r.success)
        logger.info(
            'Flight scrape completed: %d/%d routes successful', successful_results, len(queries)
        )
        return results[: len(queries)]

    except Exception as exc:
        logger.exception('Flight scrape failed with exception')
        return [ScrapeResult(success=False, error_message=f'HTTPX Error: {exc}')] * len(queries)
