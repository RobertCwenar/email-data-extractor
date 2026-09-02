from unittest.mock import MagicMock

import pytest

from modules.ai_service import AIService


@pytest.mark.asyncio
async def test_validate_salary_api_with_hourly_salary():
    ai_service = AIService(api_key="fake_key")
    ai_service.client = MagicMock()

    ai_service.client.models.generate_content.return_value.parsed = {
        "title": "QA Tester (m/f/d)",
        "contracts": [
            {
                "offer_id": None,
                "contract_type": None,
                "salary_currency": "PLN",
                "salary_period": "hourly",
                "salary_min_offer": 60,
                "salary_max_offer": 90,
                "salary_min_monthly": None,
                "salary_max_monthly": None,
            }
        ],
    }

    salary_text = """
    QA Tester (m/f/d)

    60-90 zł netto (+ VAT) / godz.

    Next Technology Professionals Sp. z o.o.
    Warszawa
    """

    contracts = await ai_service.validate_salary_api(salary_text)

    assert len(contracts) == 1

    contract = contracts[0]

    assert getattr(contract, "salary_min_offer", None) == 60
    assert getattr(contract, "salary_max_offer", None) == 90
    assert getattr(contract, "salary_currency", None) == "PLN"
    assert getattr(contract, "salary_period", None) == "hourly"

    assert getattr(contract, "contract_type", None) is None
    assert getattr(contract, "offer_id", None) is None
