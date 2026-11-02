import logging
import os
from typing import Any

from playwright.sync_api import sync_playwright

from config import scraper_config
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_offer_adapter import JUSTJOIN_CARD_SELECTOR, justjoin_card_to_record

logger = logging.getLogger(__name__)


class JustJoinScraper(BaseScraper):
    output_file = "filter_justjoin_offers.json"
    source = "scraper_justjoin"

    def __init__(self) -> None:
        self.urls = scraper_config.get_list(["scraper_justjoin", "urls"])
        self.headless = os.getenv("PLAYWRIGHT_HEADLESS", "1").strip().lower() not in {"0", "false", "no"}

    def get_offer_id(self, offer: dict[str, Any]) -> str | None:
        return offer.get("offer_id") or super().get_offer_id(offer)

    def get_offers_from_page(self, url: str) -> list[dict[str, Any]]:
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=self.headless)
                page = browser.new_page(viewport={"width": 1440, "height": 1200})
                response = page.goto(url, wait_until="domcontentloaded", timeout=60000)
                logger.info("JustJoin.it HTTP status: %s", response.status if response else None)
                if response and response.status >= 400:
                    raise RuntimeError(f"JustJoin.it returned HTTP {response.status}: {url}")

                page.wait_for_selector(JUSTJOIN_CARD_SELECTOR, timeout=30000)
                previous_count = stable_rounds = 0
                for _ in range(12):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(1000)
                    current_count = page.locator(JUSTJOIN_CARD_SELECTOR).count()
                    if current_count == previous_count:
                        stable_rounds += 1
                        if stable_rounds >= 2:
                            break
                    else:
                        stable_rounds = 0
                    previous_count = current_count

                offers: list[dict[str, Any]] = []
                seen_urls: set[str] = set()
                cards = page.locator(JUSTJOIN_CARD_SELECTOR)
                for index, link in enumerate(cards.all(), start=1):
                    try:
                        offer = justjoin_card_to_record(link, url)
                        if not offer:
                            logger.warning("JustJoin.it: missing required data for card %s", index)
                            continue
                        if offer["url"] not in seen_urls:
                            seen_urls.add(offer["url"])
                            offers.append(offer)
                    except Exception:
                        logger.exception("JustJoin.it: failed to process card %s", index)
                logger.info("JustJoin.it offers retrieved: %s", len(offers))
                browser.close()
                return offers
        except Exception:
            logger.exception("JustJoin.it: page scraping failed for %s", url)
            return []
