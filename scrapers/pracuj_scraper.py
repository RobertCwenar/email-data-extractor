import logging
import re
from typing import Any

from playwright.sync_api import sync_playwright

from config import scraper_config
from offer import StructureScraper
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


def extract_offer_id(url: str | None) -> str | None:
    if not url:
        return None
    match = re.search(r",oferta,(\d+)", url)
    return match.group(1) if match else None


class Scraper(BaseScraper):
    output_file = "filter_pracuj_offers.json"

    def __init__(self) -> None:
        self.urls = scraper_config.get_list(["scraper", "urls"])

    def get_offer_id(self, offer: dict[str, Any]) -> str | None:
        return offer.get("offer_id") or extract_offer_id(offer.get("url"))

    def get_offers_from_page(self, url: str) -> list[dict[str, Any]]:
        print("1. Start Playwright", flush=True)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)

            page = browser.new_page()
            response = page.goto(url, wait_until="commit", timeout=30000)
            logger.info("Pracuj.pl HTTP status: %s", response.status if response else None)
            page.wait_for_timeout(5000)
            print("6. Checking offer cards", flush=True)
            cards = page.locator("div[data-test='default-offer']")
            logger.info("Number of offer cards on the page: %s", cards.count())
            print("7. Number of cards:", cards.count(), flush=True)
            offers: list[dict[str, Any]] = []

            for i, card in enumerate(cards.all(), start=1):
                try:
                    offer = StructureScraper(
                        title=self.get_text(card, "[data-test='offer-title']"),
                        company=self.get_text(card, "[data-test='link-company-profile']"),
                        location=self.get_text(card, "[data-test='text-region']"),
                        level=self.get_text(card, "[data-test='offer-additional-info-0']"),
                        contract=self.get_text(card, "[data-test='offer-additional-info-2']"),
                        work_mode=self.get_text(card, "[data-test='offer-additional-info-3']"),
                        salary=self.get_text(card, "[data-test='offer-salary']"),
                        url=(
                            card.locator("a[href*='/praca/']").first.get_attribute("href", timeout=3000)
                            if card.locator("a[href*='/praca/']").count() > 0
                            else None
                        ),
                    )
                    offers.append(vars(offer))
                except Exception as e:
                    print(f"Error processing offer {i}: {e}", flush=True)
                    raise
            print("8. Offers retrieved:", len(offers), flush=True)
            return offers
