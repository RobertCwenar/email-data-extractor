from unittest.mock import MagicMock

from scrapers.scraper_offer_adapter import theprotocol_card_to_record
from scrapers.theprotocol_scraper import TheProtocolScraper


def test_adapter_extracts_fields_from_card(monkeypatch) -> None:
    link = MagicMock()
    link.locator.return_value = MagicMock()
    link.get_attribute.return_value = "/praca/analyst,oferta,12345"

    fields = {
        "[data-test='offer-title']": "Data Analyst",
        "[data-test='link-company-profile']": "Acme",
        "[data-test='text-region']": "Wrocław",
        "[data-test='offer-additional-info-2']": "B2B",
        "[data-test='offer-additional-info-3']": "Remote",
        "[data-test='offer-salary']": "15 000 PLN / month",
    }

    monkeypatch.setattr(
        "scrapers.scraper_offer_adapter._text",
        lambda element, selector: fields.get(selector),
    )

    offer = theprotocol_card_to_record(
        link,
        "https://theprotocol.it",
    )

    assert offer == {
        "title": "Data Analyst",
        "company": "Acme",
        "location": "Wrocław",
        "contract": "B2B",
        "work_mode": "Remote",
        "salary": "15 000 PLN / month",
        "url": "https://theprotocol.it/praca/analyst,oferta,12345",
        "offer_id": "12345",
    }


def test_adapter_returns_none_when_required_data_is_missing(monkeypatch) -> None:
    link = MagicMock()
    link.locator.return_value = MagicMock()
    link.get_attribute.return_value = "/praca/analyst,oferta,12345"

    fields = {
        "[data-test='offer-title']": "Data Analyst",
        "[data-test='link-company-profile']": None,
    }

    monkeypatch.setattr(
        "scrapers.scraper_offer_adapter._text",
        lambda element, selector: fields.get(selector),
    )

    offer = theprotocol_card_to_record(link, "https://theprotocol.it")

    assert offer is None


def test_scraper_returns_no_offers_and_closes_browser_on_http_error(monkeypatch) -> None:
    playwright_context, browser, page = MagicMock(), MagicMock(), MagicMock()
    playwright_context.__enter__.return_value.chromium.launch.return_value = browser
    browser.new_page.return_value = page
    page.goto.return_value.status = 403
    monkeypatch.setattr(
        "scrapers.theprotocol_scraper.sync_playwright",
        lambda: playwright_context,
    )

    offers = TheProtocolScraper().get_offers_from_page("https://theprotocol.it/praca")

    assert offers == []
    page.wait_for_selector.assert_not_called()
    browser.close.assert_called_once_with()
