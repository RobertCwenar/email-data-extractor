import logging
import os
from typing import Any

from playwright.sync_api import sync_playwright

from config import scraper_config
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_offer_adapter import ROCKETJOBS_CARD_SELECTOR, rocketjobs_card_to_record

MAX_SCROLL_ROUNDS = 12
SCROLL_WAIT_MS = 1000
STABLE_ROUNDS_LIMIT = 2

logger = logging.getLogger(__name__)


class RocketJobsScraper(BaseScraper):
    output_file = "filter_rocketjobs_offers.json"
    source = "scraper_rocketjobs"

    def __init__(self) -> None:
        self.urls = scraper_config.get_list(["scraper_rocketjobs", "urls"])
        self.headless = os.getenv("PLAYWRIGHT_HEADLESS", "1").strip().lower() not in {"0", "false", "no"}

    def get_offers_from_page(self, url: str) -> list[dict[str, Any]]:
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=self.headless)
                page = browser.new_page(viewport={"width": 1440, "height": 1200})

                response = page.goto(url, wait_until="domcontentloaded", timeout=60000)
                logger.info("RocketJobs HTTP status: %s", response.status if response else None)
                if response and response.status >= 400:
                    raise RuntimeError(f"RocketJobs returned HTTP {response.status}: {url}")

                page.wait_for_selector(ROCKETJOBS_CARD_SELECTOR, timeout=30000)
                previous_count = stable_rounds = 0
                for _ in range(MAX_SCROLL_ROUNDS):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(SCROLL_WAIT_MS)
                    current_count = page.locator(ROCKETJOBS_CARD_SELECTOR).count()
                    if current_count == previous_count:
                        stable_rounds += 1
                        if stable_rounds >= STABLE_ROUNDS_LIMIT:
                            break
                    else:
                        stable_rounds = 0
                    previous_count = current_count

                cards = page.locator(ROCKETJOBS_CARD_SELECTOR)
                logger.info("RocketJobs cards found: %s", cards.count())
                offers: list[dict[str, Any]] = []
                seen_urls: set[str] = set()
                for index, link in enumerate(cards.all(), start=1):
                    try:
                        offer = rocketjobs_card_to_record(link, url)
                        if offer is None:
                            logger.warning("RocketJobs: missing required data for card %s", index)
                            continue
                        offer_url = offer.get("url")
                        if not offer_url:
                            logger.warning("RocketJobs: card %s has no URL", index)
                            continue
                        if offer_url not in seen_urls:
                            seen_urls.add(offer_url)
                            offers.append(offer)
                    except Exception:
                        logger.exception("RocketJobs: failed to process card %s", index)

                logger.info("RocketJobs offers retrieved: %s", len(offers))
                browser.close()
                return offers
        except Exception:
            logger.exception("RocketJobs: page scraping failed for %s", url)
            return []
