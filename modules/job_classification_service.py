import logging

logger = logging.getLogger(__name__)


class JobClassificationService:
    # Initialize the JobClassificationServce with database and classifier instances
    def __init__(self, db, classifier):
        self.db = db
        self.classifier = classifier

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
                if self.db.job_details_exists(offer_id):
                    self.db.update_job_category(offer_id, category)
                else:
                    self.db.save_job_details(offer_id, clean_title, level, category)
                continue

            logger.info("New Classification: %s", clean_title)
            level = self.classifier.classify_level(clean_title)
            category = await self.classifier.classify_category(clean_title)

            if cached:
                self.db.update_job_category(offer_id, category)
            else:
                self.db.save_job_details(
                    offer_id,
                    clean_title,
                    level,
                    category,
                )
