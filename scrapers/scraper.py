import json
import logging
import re
from datetime import datetime

from playwright.sync_api import Locator, sync_playwright

from config import scraper_config

logger = logging.getLogger(__name__)


def extract_offer_id(url: str | None) -> str | None:
    if not url:
        return None
    match = re.search(r",oferta,(\d+)", url)
    return match.group(1) if match else None


class Scraper:
    def __init__(self) -> None:
        self.urls = scraper_config.get_list(["scraper", "urls"])

    def get_text(self, card: Locator, selector: str) -> str | None:
        element = card.locator(selector).first
        if element.count() == 0:
            return None
        return element.inner_text(timeout=3000)

    def get_offers_from_page(self, url: str) -> list[dict]:
        print("1. Start Playwright", flush=True)
        with sync_playwright() as p:
            print("2. Launching Chromium", flush=True)
            browser = p.chromium.launch(headless=False)
            print("3. Chromium launched", flush=True)

            page = browser.new_page()
            print("4. Opening page", flush=True)
            response = page.goto(url, wait_until="commit", timeout=30000)
            print("5. HTTP:", response.status if response else None, flush=True)
            logger.info("Pracuj.pl HTTP status: %s", response.status if response else None)
            page.wait_for_timeout(5000)
            print("6. Checking offer cards", flush=True)
            cards = page.locator("div[data-test='default-offer']")
            logger.info("Number of offer cards on the page: %s", cards.count())
            print("7. Number of cards:", cards.count(), flush=True)
            offers: list[dict] = []

            for i, card in enumerate(cards.all(), start=1):
                try:
                    offer = {
                        "title": self.get_text(card, "[data-test='offer-title']"),
                        "company": self.get_text(card, "[data-test='link-company-profile']"),
                        "location": self.get_text(card, "[data-test='text-region']"),
                        "level": self.get_text(card, "[data-test='offer-additional-info-0']"),
                        "contract": self.get_text(card, "[data-test='offer-additional-info-2']"),
                        "work_mode": self.get_text(card, "[data-test='offer-additional-info-3']"),
                        "salary": self.get_text(card, "[data-test='offer-salary']"),
                        "url": (
                            card.locator("a[href*='/praca/']").first.get_attribute("href", timeout=3000)
                            if card.locator("a[href*='/praca/']").count() > 0
                            else None
                        ),
                    }

                    offers.append(offer)
                except Exception as e:
                    print(f"Error processing offer {i}: {e}", flush=True)
                    raise
            print("8. Offers retrieved:", len(offers), flush=True)
            return offers

    def run_scraper(self) -> list[dict]:
        offers: list[dict] = []
        for url in self.urls:
            offers.extend(self.get_offers_from_page(url))

        timestamp = datetime.now().strftime("%Y-%m-%d")

        for offer in offers:
            offer["scraped_at"] = timestamp
            offer["offer_id"] = extract_offer_id(offer["url"])

        try:
            with open("filter_pracuj_offers.json", "r", encoding="utf-8") as file:
                existing_offers = json.load(file)
        except FileNotFoundError:
            existing_offers = []

        existing_keys = {
            (
                offer.get("offer_id") or extract_offer_id(offer.get("url")) or offer.get("url"),
                offer.get("scraped_at"),
            )
            for offer in existing_offers
        }

        new_offers = [
            offer
            for offer in offers
            if (
                offer.get("offer_id") or extract_offer_id(offer.get("url")) or offer.get("url"),
                offer["scraped_at"],
            )
            not in existing_keys
        ]

        existing_offers.extend(new_offers)

        with open("filter_pracuj_offers.json", "w", encoding="utf-8") as file:
            json.dump(existing_offers, file, ensure_ascii=False, indent=2)

        logger.info("Number of new offers: %s", len(new_offers))

        return new_offers
