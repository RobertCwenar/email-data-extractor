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
    assert scraper.source == "scraper_justjoinit"
    get_list.assert_called_once_with(["scraper_justjoinit", "urls"])


def test_adapter_extracts_fields_from_current_card_structure() -> None:
    link, card = MagicMock(), MagicMock()
    link.locator.return_value = card
    link.get_attribute.return_value = "/job-offer/acme-senior-analyst-123abc"
    link.inner_text.return_value = "Senior Data Analyst"

    company = MagicMock()
    company.first.count.return_value = 1
    company.first.inner_text.return_value = "Acme"

    location_icon = MagicMock()
    location_icon.first.count.return_value = 1

    location_element = location_icon.first.locator.return_value.locator.return_value.first
    location_element.count.return_value = 1
    location_element.inner_text.return_value = "Wroclaw"

    mode_icon = MagicMock()
    mode_icon.first.count.return_value = 1

    mode_element = mode_icon.first.locator.return_value.locator.return_value.first
    mode_element.count.return_value = 1
    mode_element.inner_text.return_value = "Remote"

    spans = MagicMock()
    spans.all_inner_texts.return_value = [
        "Mid",
        "B2B",
        "17 - 21k PLN / month",
    ]

    card.locator.side_effect = {
        "p": company,
        "svg.lucide-map-pin": location_icon,
        "svg.lucide-building2": mode_icon,
        "span": spans,
    }.__getitem__
    offer = justjoin_card_to_record(
        link,
        "https://justjoin.it/job-offers/wroclaw/data",
    )

    assert offer == {
        "title": "Senior Data Analyst",
        "company": "Acme",
        "location": "Wroclaw",
        "level": "Mid",
        "contract": "B2B",
        "work_mode": "Remote",
        "salary": "17 - 21k PLN / month",
        "url": "https://justjoin.it/job-offer/acme-senior-analyst-123abc",
        "offer_id": "123abc",
    }


def test_get_offers_from_page_waits_for_cards_deduplicates_and_closes_browser(monkeypatch) -> None:
    context, browser, page = MagicMock(), MagicMock(), MagicMock()
    context.__enter__.return_value.chromium.launch.return_value = browser
    browser.new_page.return_value = page
    cards = MagicMock()
    page.locator.return_value = cards
    cards.all.return_value = [MagicMock(), MagicMock()]
    monkeypatch.setattr("scrapers.justjoin_scraper.sync_playwright", lambda: context)

    offer = {
        "title": "Data Analyst",
        "company": "Acme",
        "location": "Wroclaw",
        "url": "https://justjoin.it/job-offer/acme-data-analyst-123abc",
        "offer_id": "123abc",
    }
    parse = MagicMock(return_value=offer)
    monkeypatch.setattr("scrapers.justjoin_scraper.justjoin_card_to_record", parse)

    result = JustJoinScraper().get_offers_from_page("https://justjoin.it/job-offers/wroclaw/data")

    assert result == [offer]
    cards.first.wait_for.assert_called_once_with(state="attached", timeout=30000)
    assert parse.call_count == 2
    browser.close.assert_called_once_with()
