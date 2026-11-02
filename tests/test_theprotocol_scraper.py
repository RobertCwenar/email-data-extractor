from unittest.mock import MagicMock

from config import scraper_config
from scrapers.scraper_offer_adapter import theprotocol_card_to_record
from scrapers.theprotocol_scraper import TheProtocolScraper


def test_scraper_uses_its_configured_urls(monkeypatch) -> None:
    urls = ["https://theprotocol.it/praca/filtry/data"]
    get_list = MagicMock(return_value=urls)
    monkeypatch.setattr(scraper_config, "get_list", get_list)

    scraper = TheProtocolScraper()

    assert scraper.urls == urls
    assert scraper.source == "scraper_theprotocol"
    get_list.assert_called_once_with(["scraper_theprotocol", "urls"])


def test_adapter_extracts_offer_fields_and_percent_encoded_offer_id() -> None:
    link, card = MagicMock(), MagicMock()
    link.locator.return_value = card
    link.get_attribute.return_value = "/praca/data-analyst-wroclaw%2Coferta%2C01000000-cbf7-2508-d3ce-08df2e9878f3"

    values = {
        "[data-test='offer-title']": "Data Analyst",
        "[data-test='link-company-profile']": "Acme Sp. z o.o.",
        "[data-test='text-region']": "Wrocław",
        "[data-test='offer-additional-info-2']": "B2B",
        "[data-test='offer-additional-info-3']": "hybrydowa",
        "[data-test='offer-salary']": "15k–20k zł / mies.",
    }

    def locator(selector: str) -> MagicMock:
        element = MagicMock()
        element.first.count.return_value = int(selector in values)
        element.first.inner_text.return_value = values.get(selector, "")
        element.first.get_attribute.return_value = None
        return element

    card.locator.side_effect = locator
    card.inner_text.return_value = "Data Analyst\nAcme Sp. z o.o.\nWrocław"

    offer = theprotocol_card_to_record(link, "https://theprotocol.it/praca")

    assert offer == {
        "title": "Data Analyst",
        "company": "Acme Sp. z o.o.",
        "location": "Wrocław",
        "contract": "B2B",
        "work_mode": "hybrydowa",
        "salary": "15k–20k zł / mies.",
        "url": "https://theprotocol.it/praca/data-analyst-wroclaw%2Coferta%2C01000000-cbf7-2508-d3ce-08df2e9878f3",
        "offer_id": "01000000-cbf7-2508-d3ce-08df2e9878f3",
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
    monkeypatch.setattr("scrapers.theprotocol_scraper.sync_playwright", lambda: context)

    offer = {
        "title": "Data Analyst",
        "company": "Acme",
        "location": "Wrocław",
        "url": "https://theprotocol.it/praca/data-analyst%2Coferta%2C123",
        "offer_id": "123",
    }
    parse = MagicMock(return_value=offer)
    monkeypatch.setattr("scrapers.theprotocol_scraper.theprotocol_card_to_record", parse)

    result = TheProtocolScraper().get_offers_from_page("https://theprotocol.it/praca")

    assert result == [offer]
    assert parse.call_count == 2
    browser.close.assert_called_once_with()


def test_get_offers_from_page_returns_empty_on_http_error(monkeypatch) -> None:
    context, browser, page = MagicMock(), MagicMock(), MagicMock()
    context.__enter__.return_value.chromium.launch.return_value = browser
    browser.new_page.return_value = page
    page.goto.return_value.status = 503
    monkeypatch.setattr("scrapers.theprotocol_scraper.sync_playwright", lambda: context)

    result = TheProtocolScraper().get_offers_from_page("https://theprotocol.it/praca")

    assert result == []
    page.wait_for_selector.assert_not_called()
