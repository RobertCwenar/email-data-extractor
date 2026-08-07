import re

from config import config


class JobClassifier:
    def __init__(self):
        self.levels = config.get_dict(["job_classification", "level"])
        self.categories = config.get_dict(["job_classification", "category"])

    def classify_level(self, clean_title: str):
        title = clean_title.lower()

        priority = [
            "manager",
            "senior",
            "junior",
            "intern",
            "mid",
        ]

        for level in priority:
            for keyword in self.levels[level]:
                pattern = rf"\b{re.escape(keyword.lower())}\b"

                if re.search(pattern, title):
                    return level

        return "mid"

    def classify_category(self, clean_title: str):
        title = clean_title.lower()

        for category, keywords in self.categories.items():
            for keyword in keywords:
                if keyword.lower() in title:
                    return category

        return "unknown"
