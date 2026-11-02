import logging
import os
from typing import Any

from playwright.sync_api import sync_playwright

from config import scraper_config
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_offer_adapter import (
    JUSTJOIN_CARD_SELECTOR,
    justjoin_card_to_record,
    justjoin_offer_id_from_url,
)

logger = logging.getLogger(__name__)


class JustJoinScraper(BaseScraper):
    output_file = "filter_justjoin_offers.json"
    source = "scraper_justjoinit"

    def __init__(self) -> None:
        self.urls = scraper_config.get_list(["scraper_justjoinit", "urls"])
        self.headless = os.getenv("PLAYWRIGHT_HEADLESS", "1").strip().lower() not in {"0", "false", "no"}

    def get_offer_id(self, offer: dict[str, Any]) -> str | None:
        return offer.get("offer_id") or justjoin_offer_id_from_url(offer.get("url"))

    def get_offers_from_page(self, url: str) -> list[dict[str, Any]]:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=self.headless,
            )
            page = browser.new_page(viewport={"width": 1440, "height": 1200})

            try:
                logger.info("Opening JustJoin.it: %s", url)

                page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=60000,
                )

                cards = page.locator(JUSTJOIN_CARD_SELECTOR)
                cards.first.wait_for(state="attached", timeout=30000)
                logger.info("JustJoin.it URL: %s", page.url)
                logger.info("JustJoin.it title: %s", page.title())
                logger.info("JustJoin.it cards found: %s", cards.count())

                if cards.count():
                    logger.info(
                        "JUSTJOIN CARD HTML:\n%s",
                        cards.first.evaluate("""
                            el => {
                                let node = el;
                                const result = [];
                                for (let i = 0; node && i < 6; i++, node = node.parentElement) {
                                    result.push(node.outerHTML.slice(0, 5000));
                                }
                                return result.join("\\n\\n--- PARENT ---\\n\\n");
                            }
                        """),
                    )
                offers = []
                seen_urls = set()

                for index, link in enumerate(cards.all(), start=1):
                    offer = justjoin_card_to_record(link, url)

                    if not offer:
                        continue

                    if offer["url"] in seen_urls:
                        continue

                    seen_urls.add(offer["url"])
                    offers.append(offer)

                return offers

            finally:
                browser.close()


if __name__ == "__main__":
    scraper = JustJoinScraper()
    scraper.run_scraper()
