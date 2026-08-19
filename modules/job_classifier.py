import asyncio
import logging
import re
from typing import Literal, get_args

from config import config
from modules.ai_service import AIService

logger = logging.getLogger(__name__)


class JobClassifier:
    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service
        self.levels = config.get_dict(["job_classification", "level"])
        self.categories = config.get_dict(["job_classification", "category"])
        self.category_cache: dict[str, str] = {}

    def _normalize_title(self, title: str) -> str:
        return " ".join(title.lower().strip().split())

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
        cache_key = self._normalize_title(clean_title)

        if cache_key in self.category_cache:
            category = self.category_cache[cache_key]

            logger.info(f"Category cache HIT: '{clean_title}' -> '{category}'")

            return category

        title = clean_title.lower()

        logger.info(f"Classify category input: {clean_title}")

        scores: dict[str, int] = {}
        matches_by_category: dict[str, list[tuple[str, int]]] = {}

        for category, keywords in self.categories.items():
            if category == "Category_Literal":
                continue

            score = 0
            matches = []

            for keyword in keywords:
                keyword = keyword.lower().strip()

                if keyword in title:
                    if len(keyword.split()) >= 3:
                        points = 10
                    elif len(keyword.split()) == 2:
                        points = 5
                    else:
                        points = 1

                    score += points
                    matches.append((keyword, points))

            if score > 0:
                scores[category] = score
                matches_by_category[category] = matches

        if scores:
            best_category = max(
                scores,
                key=lambda category: scores[category],
            )

            logger.info(f"Category scores for {clean_title}: {scores}")

            logger.info(
                f"Category match: '{clean_title}' -> '{best_category}' "
                f"[score={scores[best_category]}, matches={matches_by_category[best_category]}]"
            )

            best_score = scores[best_category]

            if best_score >= 1:
                self.category_cache[cache_key] = best_category

                logger.info(f"Category cache SAVE: {clean_title} -> {best_category}")

                return best_category

        logger.info(f"AI Category: {clean_title}")

        await asyncio.sleep(2)

        result = await self.ai_service.validate_category_api(
            clean_title,
            self.categories["Category_Literal"],
        )

        logger.info(f"AI Category result: {clean_title} -> {result.category}")

        self.category_cache[cache_key] = result.category

        logger.info(f"Category cache SAVE: {clean_title} -> {result.category}")

        return result.category
