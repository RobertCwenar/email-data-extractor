import logging

from offer import JobClassification

logger = logging.getLogger(__name__)


class JobClassificationService:
    # Initialize the JobClassificationServce with database and classifier instances
    def __init__(self, db, classifier, salary_estimator):
        self.db = db
        self.classifier = classifier
        self.salary_estimator = salary_estimator

    # Process jobs for classification and save the results to the database
    async def process_jobs(self):

        jobs = self.db.get_jobs_for_classification()

        for offer_id, title, company, date in jobs:
            if not title:
                continue

            cached = self.db.get_classification_by_title(title)

            if cached and cached[1]:
                logger.info(f"Classification cache: {title}")
                level, category = cached

            else:
                logger.info(f"New Classification: {title}")
                level = self.classifier.classify_level(title)
                category = await self.classifier.classify_category(title)

            salary_status = self.db.get_salary_status(offer_id)

            logger.info(f"Salary status for: {offer_id}, {salary_status}")

            if self.db.job_details_exists(offer_id):
                self.db.update_job_category(offer_id, category)
            else:
                self.db.save_job_details(
                    offer_id,
                    title,
                    level,
                    category,
                )

    async def process_salary_estimations(self):

        jobs = self.db.get_jobs_for_salary_estimator()

        logger.info(f"Jobs for salary re-estimation: {len(jobs)}")

        for offer_id, title, company, date, level, category in jobs:
            classification = JobClassification(
                offer_id=offer_id,
                clean_title=title,
                level=level,
                category=category,
            )

            salary_min, salary_max = self.salary_estimator.salary_logic(
                classification,
                company,
                title,
                date,
            )

            logger.info(f"Salary re-estimation for: {offer_id} {salary_min} {salary_max}")

            self.db.update_offer_salary(
                offer_id,
                salary_min,
                salary_max,
                salary_status="estimated",
            )
