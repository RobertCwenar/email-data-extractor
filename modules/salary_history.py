import logging
from modules.statistics_salary import SalaryStatistics 
from datetime import datetime
logger = logging.getLogger(__name__)


class SalaryHistory:
    def __init__(self, db):
        self.db = db
        self.statistics = {}
        self.salary_statistics = SalaryStatistics()
        self.history =[]

    def process_history(self):
        history_data = self.db.get_salary_history()

        logger.info(f"Salary history records: {len(history_data)}")

        self.history = self.get_history(history_data)

        logger.info(f"Processed salary history: {len(self.history)}")

        groups = self.group_history(self.history)

        logger.info(f"History groups: {len(groups)}")

        self.statistics = {}

        for key, data in groups.items():
            statistics = self.calculate_statistics(data)
            self.statistics[key] = statistics

            logger.info(f"Salary history: {key}, {statistics}")

    def _to_float(self, value):
        try:
            return float(value) if value not in (None, "") else None
        except (ValueError, TypeError):
            return None

    def get_history(self, history_data):
        history = []

        for offer in history_data:
            salary_min = self._to_float(offer[3])
            salary_max = self._to_float(offer[4])

            history.append({
                "id": offer[0],
                "title": offer[1],
                "company": offer[2],
                "salary_min": salary_min,
                "salary_max": salary_max,
                "date": offer[5],
                "category": offer[6],
                "level": offer[7],
            })

        return history

    def calculate_statistics(self, history):
        if not history:
            return None

        salary_min = [minimum for minimum, maximum in history if minimum is not None]

        salary_max = [maximum for minimum, maximum in history if maximum is not None]

        average_min = self.salary_statistics.average_salary(salary_min)
        average_max = self.salary_statistics.average_salary(salary_max)
        median_min = self.salary_statistics.median_salary(salary_min)
        median_max = self.salary_statistics.median_salary(salary_max)
        standard_deviation_min = self.salary_statistics.standard_deviation(salary_min)
        standard_deviation_max = self.salary_statistics.standard_deviation(salary_max)

        return {
            "count_min": len(salary_min),
            "count_max": len(salary_max),
            "avg_min": average_min,
            "avg_max": average_max,
            "median_min": median_min,
            "median_max": median_max,
            "standard_deviation_minimum": standard_deviation_min,
            "standard_deviation_maximum": standard_deviation_max,
        }

    def group_history(self, history):
        groups: dict[tuple[str, str], list[tuple]] = {}

        for offer in history:
            key = (offer["category"], offer["level"])

            if key not in groups:
                groups[key] = []

            groups[key].append(
                (offer["salary_min"], offer["salary_max"]))

        return groups

    def get_salary(self, category, level):
        key = (category, level)

        logger.info(f"Looking for salary history:, {key}")

        statistics = self.statistics.get((category, level))

        logger.info(f"Salary lookup: {key}, {statistics}")

        if not statistics:
            return None

        return (
            statistics["avg_min"],
            statistics["avg_max"],
        )
    def find_real_salary(self, company, title, date, months=2):
        if not company or not title or not date:
            return None

        target_date = datetime.fromisoformat(date)

        matches = []

        for offer in self.history:
            if offer["company"] != company:
                continue

            if offer["title"] != title:
                continue

            if offer["date"] == date:
                continue

            if offer["salary_min"] is None and offer["salary_max"] is None:
                continue

            if not offer["date"]:
                continue

            offer_date = datetime.fromisoformat(offer["date"])

            difference = abs((target_date - offer_date).days)

            if difference <= months * 30:
                matches.append((difference, offer))

        if not matches:
            return None

        closest_offer = min(matches, key=lambda item: item[0])[1]

        return (
            closest_offer["salary_min"],
            closest_offer["salary_max"],
        )