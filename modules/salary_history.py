import logging

logger = logging.getLogger(__name__)


class SalaryHistory:
    def __init__(self, db):
        self.db = db
        self.statistics = {}

    def process_history(self):
        history_data = self.db.get_salary_history()

        history = self.get_history(history_data)

        groups = self.group_history(history)

        self.statistics = {}

        for key, data in groups.items():
            statistics = self.calculate_statistics(data)
            self.statistics[key] = statistics

            logger.info(f"Salary history: {key}, {statistics}")

    def get_history(self, history_data):
        history = []

        for offer in history_data:
            salary_min = offer[2]
            salary_max = offer[3]

            try:
                salary_min = float(salary_min) if salary_min not in (None, "") else None
            except ValueError, TypeError:
                salary_min = None

            try:
                salary_max = float(salary_max) if salary_max not in (None, "") else None
            except ValueError, TypeError:
                salary_max = None

            history.append((salary_min, salary_max, offer[4], offer[5]))

        return history

    def calculate_statistics(self, history):
        if not history:
            return None

        salary_min = [minimum for minimum, maximum in history if minimum is not None]

        salary_max = [maximum for minimum, maximum in history if maximum is not None]

        return {
            "count_min": len(salary_min),
            "count_max": len(salary_max),
            "avg_min": sum(salary_min) / len(salary_min) if salary_min else None,
            "avg_max": sum(salary_max) / len(salary_max) if salary_max else None,
        }

    def group_history(self, history):
        groups: dict[tuple[str, str], list[tuple]] = {}

        for salary_min, salary_max, category, level in history:
            key = (category, level)

            if key not in groups:
                groups[key] = []

            groups[key].append((salary_min, salary_max))

        return groups

    def get_salary(self, category, level):
        statistics = self.statistics.get((category, level))
        logger.info(f"Salary lookup: {category}, {level}, {statistics}")
        if not statistics:
            return None

        return (
            statistics["avg_min"],
            statistics["avg_max"],
        )
