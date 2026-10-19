from unittest.mock import AsyncMock, MagicMock, call

import pytest
from google.genai.errors import ClientError

from modules.ai_service import AIService


class RateLimitError(ClientError):
    def __init__(self):
        Exception.__init__(self, "429 quota exceeded")
        self.code = 429


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


@pytest.mark.asyncio
async def test_generate_response_falls_back_and_skips_rate_limited_model(monkeypatch):
    ai_service = AIService(api_key="fake_key")
    ai_service.client = MagicMock()
    ai_service._models = ["model-a", "model-b"]
    monkeypatch.setattr(ai_service, "_wait_before_api_call", AsyncMock())

    fallback_response = MagicMock()
    ai_service.client.models.generate_content.side_effect = [RateLimitError(), fallback_response, fallback_response]

    first_result = await ai_service._generate_response("prompt", {})
    second_result = await ai_service._generate_response("prompt", {})

    assert first_result is fallback_response
    assert second_result is fallback_response
    assert ai_service._unavailable_models == {"model-a"}
    assert ai_service.client.models.generate_content.call_args_list == [
        call(
            model="model-a",
            contents="prompt",
            config={"response_mime_type": "application/json", "response_schema": {}, "temperature": 0.0},
        ),
        call(
            model="model-b",
            contents="prompt",
            config={"response_mime_type": "application/json", "response_schema": {}, "temperature": 0.0},
        ),
        call(
            model="model-b",
            contents="prompt",
            config={"response_mime_type": "application/json", "response_schema": {}, "temperature": 0.0},
        ),
    ]


@pytest.mark.asyncio
async def test_generate_response_reports_when_all_models_are_unavailable():
    ai_service = AIService(api_key="fake_key")
    ai_service.client = MagicMock()
    ai_service._models = ["model-a"]
    ai_service._unavailable_models.add("model-a")

    with pytest.raises(RuntimeError, match="All AI models are currently unavailable"):
        await ai_service._generate_response("prompt", {})

    ai_service.client.models.generate_content.assert_not_called()
