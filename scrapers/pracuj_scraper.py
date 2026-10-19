import logging
from typing import Any

from playwright.sync_api import sync_playwright

from config import scraper_config
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_offer_adapter import (
    PRACUJ_CARD_SELECTOR,
    pracuj_card_to_record,
    pracuj_offer_id_from_url,
)

logger = logging.getLogger(__name__)


class Scraper(BaseScraper):
    output_file = "filter_pracuj_offers.json"

    def __init__(self) -> None:
        self.urls = scraper_config.get_list(["scraper", "urls"])

    def get_offer_id(self, offer: dict[str, Any]) -> str | None:
        return offer.get("offer_id") or pracuj_offer_id_from_url(offer.get("url"))

    def get_offers_from_page(self, url: str) -> list[dict[str, Any]]:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)

            page = browser.new_page()
            response = page.goto(url, wait_until="commit", timeout=30000)
            logger.info("Pracuj.pl HTTP status: %s", response.status if response else None)
            page.wait_for_timeout(5000)
            cards = page.locator(PRACUJ_CARD_SELECTOR)
            logger.info("Number of offer cards on the page: %s", cards.count())
            offers: list[dict[str, Any]] = []

            for card in cards.all():
                offers.append(pracuj_card_to_record(card))
            return offers
