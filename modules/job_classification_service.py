from offer import JobClassification


class JobClassificationService:

    def __init__(self, db, classifier):
        self.db = db
        self.classifier = classifier


    def process_jobs(self):

        jobs = self.db.get_jobs_classification()

        for offer_id, clean_title in jobs:

            if not clean_title:
                continue

            classification = JobClassification(
                offer_id=offer_id,
                clean_title=clean_title,
                level=self.classifier.classify_level(clean_title),
                category=self.classifier.classify_category(clean_title),
            )

            self.db.save_job_details(
                classification.offer_id,
                classification.clean_title,
                classification.level,
                classification.category,
            )