from unittest.mock import MagicMock

from scrapers.scraper_offer_adapter import theprotocol_card_to_record


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
