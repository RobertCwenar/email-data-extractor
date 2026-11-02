import json
from unittest.mock import MagicMock, patch

from scrapers.linkedin_scraper import LinkedInScraper
from scrapers.scraper_offer_adapter import linkedin_card_to_record


def test_get_text_returns_text() -> None:
    scraper = LinkedInScraper()
    card = MagicMock()
    card.locator.return_value.first.count.return_value = 1
    card.locator.return_value.first.inner_text.return_value = "Analityk danych"

    result = scraper.get_text(card, "p span[aria-hidden='true']")

    assert result == "Analityk danych"


def test_get_text_returns_none_when_element_missing() -> None:
    scraper = LinkedInScraper()
    card = MagicMock()
    card.locator.return_value.first.count.return_value = 0

    result = scraper.get_text(card, "p span[aria-hidden='true']")

    assert result is None


def test_linkedin_card_adapter_extracts_common_offer_record() -> None:
    card = MagicMock()
    paragraphs = MagicMock()
    paragraphs.count.return_value = 3
    company = MagicMock()
    company.inner_text.return_value = "Jacumo"
    location = MagicMock()
    location.inner_text.return_value = "Warszawa (Praca hybrydowa)"
    paragraphs.nth.side_effect = lambda index: {1: company, 2: location}[index]
    title = MagicMock()
    title.first.count.return_value = 1
    title.first.inner_text.return_value = "Analityk danych"
    card.get_attribute.return_value = "job-card-component-ref-123"
    card.locator.side_effect = lambda selector: paragraphs if selector == "p" else title

    offer = linkedin_card_to_record(card)

    assert offer == {
        "title": "Analityk danych",
        "company": "Jacumo",
        "location": "Warszawa",
        "work_mode": "Praca hybrydowa",
        "url": "https://www.linkedin.com/jobs/view/123",
        "offer_id": "123",
    }


@patch("scrapers.linkedin_scraper.sync_playwright")
def test_get_offers_scrolls_until_no_new_linkedin_cards(mock_sync_playwright) -> None:
    playwright = mock_sync_playwright.return_value.__enter__.return_value
    context = playwright.chromium.launch_persistent_context.return_value
    context.pages = []
    page = context.new_page.return_value
    cards = page.locator.return_value
    first_key = "job-card-component-ref-123"
    second_key = "job-card-component-ref-456"
    cards.evaluate_all.side_effect = [
        [first_key],
        [first_key, second_key],
        [first_key, second_key],
        [first_key, second_key],
        [first_key, second_key],
        [first_key, second_key],
    ]
    cards.count.return_value = 2
    cards.all.return_value = []
    page.evaluate.return_value = {"at_bottom": True}
    page.get_by_role.return_value.first.count.return_value = 0

    scraper = LinkedInScraper()

    assert scraper.get_offers_from_page("https://example.com/jobs") == []
    assert page.evaluate.call_count == 4
    scroll_script = page.evaluate.call_args_list[0].args[0]
    assert "target.scrollTop + step" in scroll_script
    assert "left-results" in scroll_script


@patch.object(LinkedInScraper, "get_offers_from_page")
def test_run_scraper_saves_new_offers(mock_get_offers, tmp_path) -> None:
    mock_get_offers.return_value = [
        {
            "title": "Analityk danych",
            "company": "Przykładowa firma",
            "location": "Wrocław",
            "work_mode": "Praca hybrydowa",
            "url": "https://www.linkedin.com/jobs/view/123456",
            "offer_id": "123456",
        }
    ]

    scraper = LinkedInScraper()
    scraper.urls = ["https://example.com/jobs"]
    output_file = tmp_path / "filter_linkedin_offers.json"
    scraper.output_file = str(output_file)

    result = scraper.run_scraper()

    assert len(result) == 1
    assert result[0]["offer_id"] == "123456"
    assert "scraped_at" in result[0]

    saved_offers = json.loads(output_file.read_text(encoding="utf-8"))

    assert len(saved_offers) == 1
    assert saved_offers[0]["title"] == "Analityk danych"
    mock_get_offers.assert_called_once_with("https://example.com/jobs")


@patch.object(LinkedInScraper, "get_offers_from_page")
def test_run_scraper_skips_offer_already_saved_today(
    mock_get_offers,
    tmp_path,
) -> None:
    mock_get_offers.return_value = [
        {
            "title": "Analityk danych",
            "company": "Przykładowa firma",
            "location": "Wrocław",
            "work_mode": None,
            "url": "https://www.linkedin.com/jobs/view/123456",
            "offer_id": "123456",
        }
    ]

    scraper = LinkedInScraper()
    scraper.urls = ["https://example.com/jobs"]
    scraper.output_file = str(tmp_path / "filter_linkedin_offers.json")
    first_result = scraper.run_scraper()
    second_result = scraper.run_scraper()

    assert len(first_result) == 1
    assert second_result == []
