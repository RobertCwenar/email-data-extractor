from config import config
from offer import JobClassification, JobOffer


class SalaryEstimator:
    def __init__(self, salary_history):
        self.salary_rules = config.get_dict(["salary_rules"])
        self.salary_history = salary_history

    def salary_status(self, job: JobOffer):

        if job.salary_min is not None or job.salary_max is not None:
            return "offer"

        elif job.salary_min is None and job.salary_max is None:
            return "estimated"

    def salary_logic(self, job: JobClassification):

        history = self.salary_history.get_salary(
            job.category,
            job.level,
        )

        if history and history[0] is not None and history[1] is not None:
            return history

        for category, levels in self.salary_rules.items():
            if job.category == category:
                for level, salary in levels.items():
                    if job.level == level:
                        base_salary = salary["base"]
                        salary_range = salary["range"]

                        salary_min = base_salary

                        salary_max = base_salary + salary_range

                        return salary_min, salary_max

        return None, None
