import json
from unittest.mock import MagicMock, patch

from scrapers.scraper import Scraper


def test_get_offers_from_page():
    scraper = Scraper()

    with patch("scrapers.scraper.sync_playwright") as mock_playwright:
        browser = mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value
        page = browser.new_page.return_value

        card = MagicMock()

        def locator_side_effect(selector):
            elements = {
                "[data-test='offer-title']": "Data Analyst",
                "[data-test='link-company-profile']": "Jacumo",
                "[data-test='text-region']": "Wrocław",
                "[data-test='offer-additional-info-0']": "Junior",
                "[data-test='offer-additional-info-2']": "Umowa o pracę",
                "[data-test='offer-additional-info-3']": "Hybrydowo",
                "[data-test='offer-salary']": "8 000–10 000 zł",
                "[data-test='link-offer']": None,
            }

            locator = MagicMock()
            locator.inner_text.return_value = elements[selector]
            locator.get_attribute.return_value = "/praca/data-analyst"
            locator.count.return_value = 1

            return locator

        card.locator.side_effect = locator_side_effect
        page.locator.return_value.all.return_value = [card]

        offers = scraper.get_offers_from_page(scraper.url)

    assert len(offers) == 1
    assert offers[0]["title"] == "Data Analyst"
    assert offers[0]["company"] == "Jacumo"
    assert offers[0]["salary"] == "8 000–10 000 zł"
    assert offers[0]["url"] == "/praca/data-analyst"


def test_get_offers_without_salary():
    scraper = Scraper()

    with patch("scrapers.scraper.sync_playwright") as mock_playwright:
        browser = mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value
        page = browser.new_page.return_value

        card = MagicMock()

        def locator_side_effect(selector):
            locator = MagicMock()

            if selector == "[data-test='offer-salary']":
                locator.count.return_value = 0
            elif selector == "[data-test='link-offer']":
                locator.get_attribute.return_value = "/praca/data-analyst"
            else:
                locator.inner_text.return_value = "Test"

            return locator

        card.locator.side_effect = locator_side_effect
        page.locator.return_value.all.return_value = [card]

        offers = scraper.get_offers_from_page(scraper.url)

    assert len(offers) == 1
    assert offers[0]["salary"] is None


def test_run_scraper_saves_offers_to_json(tmp_path):
    scraper = Scraper()
    output_file = tmp_path / "filter_pracuj_offers.json"

    existing_offers = [
        {
            "title": "Python Developer",
            "company": "Jacumo",
            "url": "/praca/python-developer",
        }
    ]

    output_file.write_text(
        json.dumps(existing_offers, ensure_ascii=False),
        encoding="utf-8",
    )

    new_offers = [
        {
            "title": "Data Analyst",
            "company": "Jacumo",
            "salary": None,
            "url": "/praca/data-analyst",
        }
    ]

    with (
        patch.object(scraper, "get_offers_from_page", return_value=new_offers),
        patch("scrapers.scraper.open", create=True) as mock_open,
    ):
        mock_open.side_effect = [
            MagicMock(
                __enter__=lambda _: output_file.open("r", encoding="utf-8"),
                __exit__=lambda *_: None,
            ),
            MagicMock(
                __enter__=lambda _: output_file.open("w", encoding="utf-8"),
                __exit__=lambda *_: None,
            ),
        ]

        scraper.run_scraper()

    saved_offers = json.loads(output_file.read_text(encoding="utf-8"))

    assert len(saved_offers) == 2
    assert saved_offers[0]["title"] == "Python Developer"
    assert saved_offers[1]["title"] == "Data Analyst"
    assert "scraped_at" in saved_offers[1]
