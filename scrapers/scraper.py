import json
import logging
from datetime import date, datetime

from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)


class Scraper:
    def __init__(self):
        self.url = "https://www.pracuj.pl/praca/data%20analyst;kw?et=17%2C3"

    def get_offers_from_page(self, url):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            try:
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=60_000)

                cards = page.locator("div[data-test='default-offer']")
                offers = []

                for card in cards.all():
                    offer = {
                        "title": card.locator("[data-test='offer-title']").inner_text(),
                        "company": card.locator("[data-test='link-company-profile']").inner_text(),
                        "location": card.locator("[data-test='text-region']").inner_text(),
                        "level": card.locator("[data-test='offer-additional-info-0']").inner_text(),
                        "contract": card.locator("[data-test='offer-additional-info-2']").inner_text(),
                        "work_mode": card.locator("[data-test='offer-additional-info-3']").inner_text(),
                        "salary": (
                            card.locator("[data-test='offer-salary']").inner_text()
                            if card.locator("[data-test='offer-salary']").count() > 0
                            else None
                        ),
                        "url": card.locator("[data-test='link-offer']").get_attribute("href"),
                    }

                    offers.append(offer)

                return offers

            finally:
                browser.close()

    def run_scraper(self):
        offers = self.get_offers_from_page(self.url)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for offer in offers:
            offer["scraped_at"] = timestamp

        try:
            with open("filter_pracuj_offers.json", "r", encoding="utf-8") as file:
                existing_offers = json.load(file)
        except FileNotFoundError:
            existing_offers = []

        existing_urls = {offer.get("url") for offer in existing_offers if offer.get("url")}

        new_offers = [offer for offer in offers if offer.get("url") and offer["url"] not in existing_urls]

        existing_offers.extend(new_offers)

        with open("filter_pracuj_offers.json", "w", encoding="utf-8") as file:
            json.dump(existing_offers, file, ensure_ascii=False, indent=2)

        logger.info(f"Liczba nowych ofert: {len(new_offers)}")
        logger.info(f"Liczba wszystkich ofert w JSON: {len(existing_offers)}")

        return new_offers

    def load_todays_offers(self) -> list[dict]:
        with open("filter_pracuj_offers.json", "r", encoding="utf-8") as file:
            offers = json.load(file)

        if not isinstance(offers, list):
            raise ValueError()

        today = date.today().isoformat()
        todays_offers: list[dict] = []

        for offer in offers:
            if not isinstance(offer, dict):
                continue

            scraped_at = offer.get("scraped_at")
            if isinstance(scraped_at, str) and scraped_at[:10] == today:
                todays_offers.append(offer)

        return todays_offers
