from unittest.mock import MagicMock

import pytest

from services.ai_service import AIService


@pytest.mark.asyncio
async def test_extract_offers():
    ai_service = AIService(api_key="fake_key")
    ai_service.client = MagicMock()

    ai_service.client.models.generate_content.return_value.parsed = {
        "offers": [
            {
                "date": "2026-07-16",
                "title": "Specjalista ds. danych",
                "company": "Firma X",
                "location": "Warszawa",
                "salary_min": 6000,
                "salary_max": 7000,
            }
        ]
    }

    offers = await ai_service.parser_offers_api("mail z ofertą pracy")  # type: ignore[attr-defined]

    assert len(offers) == 1
    assert offers[0].title == "Specjalista ds. danych"
    assert offers[0].company == "Firma X"
