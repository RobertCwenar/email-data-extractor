import logging
import re

from config import config
from modules.ai_service import AIService
from typing import get_args, Literal

logger = logging.getLogger(__name__)


class JobClassifier:
    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service
        self.levels = config.get_dict(["job_classification", "level"])
        self.categories = config.get_dict(["job_classification", "category"])

    def classify_level(self, clean_title: str):
        title = clean_title.lower()

        Priority = Literal[
            "senior",
            "junior",
            "intern",
            "mid",
            "manager", 
        ]

        for level in get_args(Priority):
            for keyword in self.levels[level]:
                pattern = rf"\b{re.escape(keyword.lower())}\b"

                if re.search(pattern, title):
                    return level

        return "unknown"

    async def classify_category(self, clean_title: str):
        title = clean_title.lower()

        for category, keywords in self.categories.items():
            for keyword in keywords:
                if keyword.lower() in title:
                    return category

        logger.info("AI Category: %s", clean_title)

        result = await self.ai_service.validate_category_api(
            clean_title,
            list(self.categories.keys()),
        )

        return result.category
