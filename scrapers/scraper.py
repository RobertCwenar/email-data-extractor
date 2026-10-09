import json
import logging
from datetime import date, datetime

from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)


class Scraper:
    def __init__(self):
        self.url = "https://www.pracuj.pl/praca/data%20analyst;kw?et=17%2C3"

    def get_text(self, card, selector):
        element = card.locator(selector).first
        if element.count() == 0:
            return None
        return element.inner_text(timeout=3000)

    def get_offers_from_page(self, url):
        print("1. Start Playwright", flush=True)
        with sync_playwright() as p:
            print("2. Uruchamiam Chromium", flush=True)
            browser = p.chromium.launch(headless=False)
            print("3. Chromium uruchomiony", flush=True)

            page = browser.new_page()
            print("4. Otwieram stronę", flush=True)
            response = page.goto(url, wait_until="commit", timeout=30000)
            print("5. HTTP:", response.status if response else None, flush=True)
            logger.info("Pracuj.pl HTTP status: %s", response.status if response else None)
            page.wait_for_timeout(5000)
            print("6. Sprawdzam karty ofert", flush=True)
            cards = page.locator("div[data-test='default-offer']")
            logger.info("Liczba kart ofert na stronie: %s", cards.count())
            print("7. Liczba kart:", cards.count(), flush=True)
            offers = []

            for i, card in enumerate(cards.all(), start=1):
                print(f"Pobieram ofertę {i}/50", flush=True)
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
                    print(f"Błąd przy ofercie {i}: {e}", flush=True)
                    raise
            print("8. Pobrano ofert:", len(offers), flush=True)
            return offers

        # finally:
        # browser.close()

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
