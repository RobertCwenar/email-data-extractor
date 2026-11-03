import logging
import os
from typing import Any

from playwright.sync_api import sync_playwright

from config import scraper_config
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_offer_adapter import THEPROTOCOL_CARD_SELECTOR, theprotocol_card_to_record

logger = logging.getLogger(__name__)


class TheProtocolScraper(BaseScraper):
    output_file = "filter_theprotocol_offers.json"
    source = "scraper_theprotocol"

    def __init__(self) -> None:
        self.urls = scraper_config.get_list(["scraper_theprotocolit", "urls"])
        self.headless = os.getenv("PLAYWRIGHT_HEADLESS", "1").strip().lower() not in {"0", "false", "no"}

    def get_offers_from_page(self, url: str) -> list[dict[str, Any]]:
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=self.headless)

                try:
                    context = browser.new_context(
                        viewport={"width": 1440, "height": 1200},
                        locale="pl-PL",
                        timezone_id="Europe/Warsaw",
                        user_agent=(
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/142.0.0.0 Safari/537.36"
                        ),
                    )

                    page = context.new_page()

                    response = page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=60000,
                    )
                    print("HTTP STATUS:", response.status if response else None)
                    print("FINAL URL:", page.url)
                    print("TITLE:", page.title())
                    print("USER AGENT:", page.evaluate("navigator.userAgent"))
                    print("CONTENT:", page.locator("body").inner_text()[:2000])
                    logger.info(
                        "theprotocol.it HTTP status: %s",
                        response.status if response else None,
                    )

                    if response and response.status >= 400:
                        raise RuntimeError(f"theprotocol.it returned HTTP {response.status}: {url}")

                    page.wait_for_selector(
                        THEPROTOCOL_CARD_SELECTOR,
                        timeout=30000,
                    )

                    previous_count = 0
                    stable_rounds = 0

                    for _ in range(12):
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        page.wait_for_timeout(1000)

                        current_count = page.locator(THEPROTOCOL_CARD_SELECTOR).count()

                        if current_count == previous_count:
                            stable_rounds += 1
                            if stable_rounds >= 2:
                                break
                        else:
                            stable_rounds = 0

                        previous_count = current_count

                    offers: list[dict[str, Any]] = []
                    seen_urls: set[str] = set()

                    cards = page.locator(THEPROTOCOL_CARD_SELECTOR)

                    for index, link in enumerate(cards.all(), start=1):
                        try:
                            offer = theprotocol_card_to_record(link, url)

                            if not offer:
                                logger.warning(
                                    "theprotocol.it: missing required data for card %s",
                                    index,
                                )
                                continue

                            if offer["url"] not in seen_urls:
                                seen_urls.add(offer["url"])
                                offers.append(offer)

                        except Exception:
                            logger.exception(
                                "theprotocol.it: failed to process card %s",
                                index,
                            )

                    logger.info(
                        "theprotocol.it offers retrieved: %s",
                        len(offers),
                    )

                    return offers

                finally:
                    browser.close()

        except Exception:
            logger.exception(
                "theprotocol.it: page scraping failed for %s",
                url,
            )
            return []


if __name__ == "__main__":
    scraper = TheProtocolScraper()
    scraper.run_scraper()
