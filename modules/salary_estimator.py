import logging

from config import config
from offer import JobClassification, JobOffer

logger = logging.getLogger(__name__)


class SalaryEstimator:
    def __init__(self, salary_history):
        self.salary_rules = config.get_dict(["salary_rules"])
        self.salary_history = salary_history

    def salary_status(self, job: JobOffer):

        if job.salary_min is not None or job.salary_max is not None:
            return "offer"

        return "estimated"

    def salary_logic(self, job: JobClassification, company, title, date):
        logger.info(f"Salary estimation started: {job.category}, {job.level}")

        history = self.salary_history.find_real_salary(
            company=company,
            title=title,
            date=date,
        )

        logger.info(f"Real salary history result: {history}")

        if history:
            logger.info(f"Using real salary from history: {history}")
            return history

        history = self.salary_history.get_salary(job.category, job.level)

        logger.info(f"Statistical salary history result: {history}")

        if history and history[0] is not None and history[1] is not None:
            logger.info(f"Using statistical salary history: {history}")
            return history

        for category, levels in self.salary_rules.items():
            if job.category == category:
                for level, salary in levels.items():
                    if job.level == level:
                        base_salary = salary["base"]
                        salary_range = salary["range"]

                        salary_min = base_salary
                        salary_max = base_salary + salary_range

                        logger.info(f"Using salary rules for {job.category}, {job.level}: {salary_min}, {salary_max}")

                        return salary_min, salary_max

        logger.info(f"No salary rules found for {job.category}, {job.level}")

        return None, None

    def recalculate_empty_salaries(self, db):
        jobs = db.get_jobs_for_salary_estimator()

        for job in jobs:
            offer_id, title, company, date, level, category = job

            classification = JobClassification(
                offer_id=offer_id,
                category=category,
                level=level,
            )

            salary_min, salary_max = self.salary_logic(
                classification,
                company,
                title,
                date,
            )

            if salary_min is not None and salary_max is not None:
                db.update_offer_salary(
                    offer_id,
                    salary_min,
                    salary_max,
                )
