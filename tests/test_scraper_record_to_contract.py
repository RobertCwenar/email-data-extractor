import pytest

from scrapers.scraper_offer_adapter import scraper_record_to_contract


@pytest.mark.parametrize(
    ("record", "expected_type", "expected_min", "expected_max", "expected_period"),
    [
        (
            {
                "salary": "9 000–12 500 zł brutto / mies.",
                "contract": "Umowa o pracę",
            },
            "UoP",
            9000,
            12500,
            "monthly",
        ),
        (
            {
                "salary": "70–120 zł netto (+ VAT) / godz.",
                "contract": "Kontrakt B2B",
            },
            "B2B",
            70,
            120,
            "hourly",
        ),
        (
            {
                "salary": "5 500–6 500 zł brutto / mies.",
                "contract": "Permanent",
            },
            "UoP",
            5500,
            6500,
            "monthly",
        ),
        (
            {
                "salary": "5 000–7 000 zł brutto / mies.",
                "contract": "Umowa zlecenie",
            },
            "UZ",
            5000,
            7000,
            "monthly",
        ),
    ],
)
def test_scraper_record_to_contract(
    record,
    expected_type,
    expected_min,
    expected_max,
    expected_period,
):
    contract = scraper_record_to_contract(record)

    assert contract.contract_type == expected_type
    assert contract.salary_min_offer == expected_min
    assert contract.salary_max_offer == expected_max
    assert contract.salary_period == expected_period
    assert contract.salary_currency == "PLN"


def test_missing_salary_returns_contract_without_salary():
    record = {
        "salary": None,
        "contract": "Permanent",
    }

    contract = scraper_record_to_contract(record)

    assert contract.contract_type == "UoP"
    assert contract.salary_min_offer is None
    assert contract.salary_max_offer is None


def test_salary_depending_on_contract_is_not_parsed():
    record = {
        "salary": "32–7 000 zł / mies. (zal. od umowy)",
        "contract": "Umowa o pracę, Umowa zlecenie",
    }

    contract = scraper_record_to_contract(record)

    assert contract.salary_min_offer is None
    assert contract.salary_max_offer is None


def test_salary_without_supported_period_is_not_parsed():
    record = {
        "salary": "9 000–12 500 zł brutto",
        "contract": "Umowa o pracę",
    }

    contract = scraper_record_to_contract(record)

    assert contract.contract_type == "UoP"
    assert contract.salary_min_offer is None
    assert contract.salary_max_offer is None
