import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.sync_api import Locator

from offer import StructureScraper

logger = logging.getLogger(__name__)


class BaseScraper:
    urls: list[str]
    output_file: str

    def get_text(self, card: Locator, selector: str) -> str | None:
        element = card.locator(selector).first
        if element.count() == 0:
            return None
        return element.inner_text(timeout=3000).strip()

    def get_offer_id(self, offer: dict[str, Any]) -> str | None:
        offer_id = offer.get("offer_id")
        return str(offer_id) if offer_id is not None else None

    def get_offers_from_page(self, url: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    def run_scraper(self) -> list[dict[str, Any]]:
        offers: list[dict[str, Any]] = []
        for url in self.urls:
            offers.extend(self.get_offers_from_page(url))

        timestamp = datetime.now().strftime("%Y-%m-%d")
        normalized_offers: list[dict[str, Any]] = []
        for raw_offer in offers:
            offer = StructureScraper.model_validate(raw_offer).model_dump()
            offer["scraped_at"] = timestamp
            offer_id = self.get_offer_id(offer)
            if offer_id is not None:
                offer["offer_id"] = offer_id
            normalized_offers.append(offer)
        offers = normalized_offers

        output_path = Path(self.output_file)
        try:
            with output_path.open("r", encoding="utf-8") as file:
                existing_offers = json.load(file)
                if not isinstance(existing_offers, list):
                    existing_offers = []
        except FileNotFoundError, json.JSONDecodeError:
            existing_offers = []

        existing_keys = {
            (self._offer_key(offer), offer.get("scraped_at")) for offer in existing_offers if isinstance(offer, dict)
        }

        new_offers: list[dict[str, Any]] = []
        for offer in offers:
            key = (self._offer_key(offer), offer["scraped_at"])
            if key[0] is None or key not in existing_keys:
                new_offers.append(offer)
                if key[0] is not None:
                    existing_keys.add(key)

        existing_offers.extend(new_offers)
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(existing_offers, file, ensure_ascii=False, indent=2)

        logger.info("New offers saved to %s: %s", output_path, len(new_offers))
        return new_offers

    def load_saved_offers(self) -> list[dict[str, Any]]:
        output_path = Path(self.output_file)
        try:
            with output_path.open("r", encoding="utf-8") as file:
                saved_offers = json.load(file)
        except FileNotFoundError, json.JSONDecodeError:
            return []

        if not isinstance(saved_offers, list):
            logger.warning("Ignoring scraper output with unexpected format: %s", output_path)
            return []

        offers: list[dict[str, Any]] = []
        today = datetime.now().strftime("%Y-%m-%d")
        for raw_offer in saved_offers:
            if not isinstance(raw_offer, dict):
                continue
            if raw_offer.get("scraped_at") != today:
                continue
            try:
                offers.append(StructureScraper.model_validate(raw_offer).model_dump())
            except Exception:
                logger.exception("Ignoring invalid saved scraper record in %s", output_path)

        logger.info("Loaded %s saved offers from %s without scraping", len(offers), output_path)
        return offers

    def _offer_key(self, offer: dict[str, Any]) -> tuple[str, str]:
        company = offer.get("company")
        title = offer.get("title")
        return str(company or "").strip(), str(title or "").strip()
