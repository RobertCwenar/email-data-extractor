from unittest.mock import MagicMock

import pytest

from config import scraper_config
from scrapers.rocketjobs_scraper import RocketJobsScraper
from scrapers.scraper_offer_adapter import (
    _contract,
    _level,
    _location,
    _salary,
    _text,
)


def test_scraper_uses_its_configured_urls(monkeypatch) -> None:
    urls = ["https://rocketjobs.example/jobs"]
    get_list = MagicMock(return_value=urls)
    monkeypatch.setattr(scraper_config, "get_list", get_list)

    scraper = RocketJobsScraper()

    assert scraper.urls == urls
    assert scraper.source == "scraper_rocketjobs"
    get_list.assert_called_once_with(["scraper_rocketjobs", "urls"])


def test_get_offers_from_page_extracts_card_and_normalizes_url(monkeypatch) -> None:
    context, browser, page, card, link = (MagicMock() for _ in range(5))
    context.__enter__.return_value.chromium.launch.return_value = browser
    browser.new_page.return_value = page
    page.goto.return_value.status = 200
    monkeypatch.setattr("scrapers.rocketjobs_scraper.sync_playwright", lambda: context)

    selectors = {
        name: MagicMock()
        for name in (
            "a.offer_list_offer_title_link",
            "img[alt]",
            "svg.lucide-map-pin + div",
            "span",
            "p",
        )
    }
    card.locator.side_effect = selectors.__getitem__
    link.locator.return_value = card
    link.get_attribute.return_value = "/oferta-pracy/bi-analyst"
    selectors["a.offer_list_offer_title_link"].first.count.return_value = 1
    selectors["a.offer_list_offer_title_link"].first.inner_text.return_value = "BI Analyst"
    selectors["img[alt]"].first.count.return_value = 1
    selectors["img[alt]"].first.get_attribute.return_value = "Image: Acme"
    selectors["svg.lucide-map-pin + div"].all_inner_texts.return_value = ["Wroc\u0142aw, +2 Lokalizacje"]
    selectors["span"].all_inner_texts.return_value = ["12 000 - 15 000", "PLN / month", "Mid", "B2B"]
    selectors["p"].all_inner_texts.return_value = ["Hybrydowo"]
    page.locator.return_value.count.return_value = 1
    page.locator.return_value.all.return_value = [link]

    offers = RocketJobsScraper().get_offers_from_page("https://rocketjobs.pl/oferty-pracy/wroclaw/bi-data")

    assert len(offers) == 1 and isinstance(offers[0], dict)
    assert offers[0]["company"] == "Acme"
    assert offers[0]["location"] == "Wroc\u0142aw"
    assert offers[0]["level"] == "Mid"
    assert offers[0]["contract"] == "B2B"
    assert offers[0]["work_mode"] == "Hybrydowo"
    assert offers[0]["salary"] == "12 000 - 15 000 PLN / month"
    assert offers[0]["url"] == "https://rocketjobs.pl/oferta-pracy/bi-analyst"
    browser.close.assert_called_once_with()


def test_get_offers_from_page_deduplicates_cards_by_url(monkeypatch) -> None:
    context, browser, page, card, link = (MagicMock() for _ in range(5))
    context.__enter__.return_value.chromium.launch.return_value = browser
    browser.new_page.return_value = page
    page.goto.return_value.status = 200
    monkeypatch.setattr("scrapers.rocketjobs_scraper.sync_playwright", lambda: context)

    selectors = {
        name: MagicMock()
        for name in (
            "a.offer_list_offer_title_link",
            "img[alt]",
            "svg.lucide-map-pin + div",
            "span",
            "p",
        )
    }
    card.locator.side_effect = selectors.__getitem__
    link.locator.return_value = card
    link.get_attribute.side_effect = lambda name: {
        "href": "/oferta-pracy/bi-analyst",
        "title": "Zobacz ofertę BI Analyst",
    }[name]
    selectors["a.offer_list_offer_title_link"].first.count.return_value = 1
    selectors["a.offer_list_offer_title_link"].first.inner_text.return_value = "BI Analyst"
    selectors["img[alt]"].first.count.return_value = 1
    selectors["img[alt]"].first.get_attribute.return_value = "Acme"
    selectors["svg.lucide-map-pin + div"].all_inner_texts.return_value = []
    selectors["span"].all_inner_texts.return_value = []
    selectors["p"].all_inner_texts.return_value = []
    page.locator.return_value.count.return_value = 2
    page.locator.return_value.all.return_value = [link, link]

    offers = RocketJobsScraper().get_offers_from_page("https://rocketjobs.pl/jobs")

    assert len(offers) == 1
    assert offers[0]["title"] == "BI Analyst"
    assert offers[0]["location"] == "Nie podano"
    assert offers[0]["url"] == "https://rocketjobs.pl/oferta-pracy/bi-analyst"


def test_text_returns_none_for_missing_or_empty_element() -> None:
    card = MagicMock()
    card.locator.return_value.first.count.return_value = 0
    assert _text(card, ".missing") is None

    card.locator.return_value.first.count.return_value = 1
    card.locator.return_value.first.inner_text.return_value = "  "
    assert _text(card, ".empty") is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("Wroc\u0142aw, +4 Lokalizacje", "Wroc\u0142aw"), ("Remote", "Remote")],
)
def test_location_cleans_extra_locations(raw: str, expected: str) -> None:
    card = MagicMock()
    card.locator.return_value.all_inner_texts.return_value = [raw]

    assert _location(card) == expected


def test_location_ignores_company_profile_button() -> None:
    card = MagicMock()
    card.locator.return_value.all_inner_texts.return_value = [
        "Poka\u017c profil firmy",
        "Wroc\u0142aw, +2 Lokalizacje",
    ]

    assert _location(card) == "Wroc\u0142aw"


def test_level_and_contract_only_accept_complete_values() -> None:
    assert _level(["Google Tag Manager", "Mid Data Engineer", "Specjalista / Mid"]) == "Specjalista / Mid"
    assert _contract(["B2B marketing"]) is None
    assert _contract(["B2B marketing", "B2B, Umowa zlecenie"]) == "B2B, Umowa zlecenie"


@pytest.mark.parametrize(
    ("spans", "expected"),
    [
        (["12 000 - 15 000", "PLN / month"], "12 000 - 15 000 PLN / month"),
        (["12 000 \u2013 15 000", "z\u0142 / mies."], "12 000 \u2013 15 000 z\u0142 / mies."),
        (["15 000 PLN/mies."], "15 000 PLN/mies."),
        (["Competitive salary"], None),
    ],
)
def test_salary_reads_supported_formats(spans: list[str], expected: str | None) -> None:
    card = MagicMock()
    card.locator.return_value.all_inner_texts.return_value = spans

    assert _salary(card) == expected
