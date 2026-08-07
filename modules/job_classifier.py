from config import config

class JobClassifier:
    def __init__(self):
        self.levels = config.get_list(['job_classification', 'level'])
        self.categories = config.get_dict(['job_classification','category'])

    def classify_level(self, clean_title: str):
        title = clean_title.lower()

        for level in self.levels:
            if level.lower() in title:
                return level

        return "mid" # Default level if no match is found

    def classify_category(self, clean_title: str):
        title = clean_title.lower()

        for category, keywords in self.categories.items():
            for keyword in keywords:
                if keyword.lower() in title:
                    return category

        return None