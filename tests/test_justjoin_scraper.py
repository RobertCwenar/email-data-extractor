from unittest.mock import MagicMock

from config import scraper_config
from scrapers.justjoin_scraper import JustJoinScraper
from scrapers.scraper_offer_adapter import justjoin_card_to_record


def test_scraper_uses_its_configured_urls(monkeypatch) -> None:
    urls = ["https://justjoin.it/job-offers/wroclaw/data"]
    get_list = MagicMock(return_value=urls)
    monkeypatch.setattr(scraper_config, "get_list", get_list)

    scraper = JustJoinScraper()

    assert scraper.urls == urls
    assert scraper.source == "scraper_justjoin"
    get_list.assert_called_once_with(["scraper_justjoin", "urls"])


def test_adapter_extracts_offer_fields_and_normalizes_url() -> None:
    link, card = MagicMock(), MagicMock()
    link.locator.return_value = card
    link.get_attribute.return_value = "/job-offer/acme-senior-analyst-123abc"

    values = {
        "h3": "Senior Data Analyst",
        "img[alt]": "",
        "[data-testid*='location']": "Wrocław",
    }
    elements = {}

    def locator(selector: str) -> MagicMock:
        if selector not in elements:
            element = MagicMock()
            element.first.count.return_value = int(selector in values)
            element.first.inner_text.return_value = values.get(selector, "")
            element.first.get_attribute.return_value = "Acme" if selector == "img[alt]" else None
            elements[selector] = element
        return elements[selector]

    card.locator.side_effect = locator
    card.inner_text.return_value = "Senior Data Analyst\nMid\nB2B\nRemote\n17 - 21k PLN / month"

    offer = justjoin_card_to_record(link, "https://justjoin.it/job-offers/wroclaw/data")

    assert offer == {
        "title": "Senior Data Analyst",
        "company": "Acme",
        "location": "Wrocław",
        "level": "Mid",
        "contract": "B2B",
        "work_mode": "Remote",
        "salary": "17 - 21k PLN / month",
        "url": "https://justjoin.it/job-offer/acme-senior-analyst-123abc",
        "offer_id": "123abc",
    }


def test_get_offers_from_page_deduplicates_cards_by_url(monkeypatch) -> None:
    context, browser, page = MagicMock(), MagicMock(), MagicMock()
    context.__enter__.return_value.chromium.launch.return_value = browser
    browser.new_page.return_value = page
    page.goto.return_value.status = 200
    cards = MagicMock()
    page.locator.return_value = cards
    cards.count.return_value = 1
    cards.all.return_value = [MagicMock(), MagicMock()]
    monkeypatch.setattr("scrapers.justjoin_scraper.sync_playwright", lambda: context)

    offer = {
        "title": "Data Analyst",
        "company": "Acme",
        "location": "Wrocław",
        "url": "https://justjoin.it/job-offer/acme-data-analyst-123abc",
        "offer_id": "123abc",
    }
    parse = MagicMock(return_value=offer)
    monkeypatch.setattr("scrapers.justjoin_scraper.justjoin_card_to_record", parse)

    result = JustJoinScraper().get_offers_from_page("https://justjoin.it/job-offers/wroclaw/data")

    assert result == [offer]
    assert parse.call_count == 2
    browser.close.assert_called_once_with()
