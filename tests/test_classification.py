from typing import Any, cast

import pytest

from modules.job_classifier import JobClassifier


class MockAIService:
    async def validate_category_api(self, clean_title, categories):
        raise AssertionError("AI should not be called in this test")


def test_classify_level():
    classifier = JobClassifier(cast(Any, MockAIService()))

    result = classifier.classify_level("Senior Data Engineer")

    assert result == "senior"


@pytest.mark.asyncio
async def test_classify_category():
    classifier = JobClassifier(cast(Any, MockAIService()))

    result = await classifier.classify_category("Starszy specjalista ds. logistyki")

    assert result == "logistics_supply_chain"


def test_unknown_level():
    classifier = JobClassifier(cast(Any, MockAIService()))

    result = classifier.classify_level("Something Random")

    assert result == "unknown"
