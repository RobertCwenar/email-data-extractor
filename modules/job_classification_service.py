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

        for offer_id, clean_title in jobs:
            if not clean_title:
                continue

            cached = self.db.get_classification_by_title(clean_title)

            if cached and cached[1]:
                logger.info("Classification cache: %s", clean_title)
                level, category = cached

            else:
                logger.info("New Classification: %s", clean_title)
                level = self.classifier.classify_level(clean_title)
                category = await self.classifier.classify_category(clean_title)

            classification = JobClassification(
                offer_id=offer_id,
                clean_title=clean_title,
                level=level,
                category=category,
            )

            salary_status = self.db.get_salary_status(offer_id)

            if salary_status == "estimated":
                salary_min, salary_max = self.salary_estimator.salary_logic(classification)

                if salary_min is not None and salary_max is not None:
                    self.db.update_offer_salary(offer_id, salary_min, salary_max)

            if self.db.job_details_exists(offer_id):
                self.db.update_job_category(offer_id, category)
            else:
                self.db.save_job_details(
                    offer_id,
                    clean_title,
                    level,
                    category,
                )
