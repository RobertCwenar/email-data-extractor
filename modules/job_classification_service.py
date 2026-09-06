import logging

from offer import JobClassification, JobContract

logger = logging.getLogger(__name__)


class JobClassificationService:
    # Initialize the JobClassificationServce with database and classifier instances
    def __init__(self, db, classifier, salary_estimator, salary_processor):
        self.db = db
        self.classifier = classifier
        self.salary_estimator = salary_estimator
        self.salary_processor = salary_processor

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
        contracts = self.db.get_job_contracts_for_salary_estimator()

        logger.info(f"Contracts for salary estimation: {len(contracts)}")

        for contract_id, offer_id, title, company, date, level, category in contracts:
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

            self.db.update_job_contract_salary(
                contract_id,
                "UoP",
                "PLN",
                "monthly",
                salary_min,
                salary_max,
            )

    async def process_salary_selection(self, offer_ids: set[int]):
        for offer_id in offer_ids:
            rows = self.db.get_job_contracts(offer_id)

            contracts = [
                JobContract(
                    offer_id=offer_id,
                    contract_type=row[0],
                    salary_currency=row[1],
                    salary_period=row[2],
                    salary_min_offer=row[3],
                    salary_max_offer=row[4],
                    salary_min_monthly=row[5],
                    salary_max_monthly=row[6],
                )
                for row in rows
            ]

            selected_contract = self.salary_processor.select_contract(contracts)

            if selected_contract:
                self.db.update_offer_salary(
                    offer_id=offer_id,
                    salary_min=selected_contract.salary_min_monthly,
                    salary_max=selected_contract.salary_max_monthly,
                    salary_status=self.salary_processor.get_salary_status(selected_contract),
                )
