import logging

from offer import JobClassification, JobContract

logger = logging.getLogger(__name__)


class JobClassificationService:
    # Initialize the JobClassificationServce with database and classifier instances
    def __init__(self, queries, updates, inserts, classifier, salary_estimator, salary_processor) -> None:
        self.db_query = queries
        self.db_update = updates
        self.db_insert = inserts
        self.classifier = classifier
        self.salary_estimator = salary_estimator
        self.salary_processor = salary_processor

    # Process jobs for classification and save the results to the database
    async def process_jobs(self) -> None:

        jobs = self.db_query.get_jobs_for_classification()

        for offer_id, title, company, date in jobs:
            if not title:
                continue

            cached = self.db_query.get_classification_by_title(title)

            if cached and cached[1]:
                logger.debug(f"Classification cache: {title}")
                level, category = cached

            else:
                logger.debug(f"New Classification: {title}")
                level = self.classifier.classify_level(title)
                category = await self.classifier.classify_category(title)

            salary_status = self.db_query.get_salary_status(offer_id)

            logger.debug(f"Salary status for: {offer_id}, {salary_status}")

            if self.db_query.job_details_exists(offer_id):
                self.db_update.update_job_category(offer_id, category)
            else:
                self.db_insert.save_job_details(
                    offer_id,
                    title,
                    level,
                    category,
                )

    async def process_salary_estimations(self) -> None:
        contracts = self.db_query.get_job_contracts_for_salary_estimator()

        logger.debug(f"Contracts for salary estimation: {len(contracts)}")

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

            logger.debug(f"Salary re-estimation for: {offer_id} {salary_min} {salary_max}")

            self.db_update.update_offer_salary(
                offer_id,
                salary_min,
                salary_max,
                salary_status="estimated",
            )

            self.db_update.update_job_contract_salary(
                contract_id,
                "UoP",
                "PLN",
                "monthly",
                salary_min,
                salary_max,
            )

    async def process_salary_selection(self, offer_ids: set[int]) -> None:
        for offer_id in offer_ids:
            rows = self.db_query.get_job_contracts(offer_id)

            contracts = []

            for row in rows:
                contract_id = row[0]
                contract = JobContract(
                    offer_id=offer_id,
                    contract_type=row[1],
                    salary_currency=row[2],
                    salary_period=row[3],
                    salary_min_offer=row[4],
                    salary_max_offer=row[5],
                    salary_min_monthly=row[6],
                    salary_max_monthly=row[7],
                )
                old_min_monthly = contract.salary_min_monthly
                old_max_monthly = contract.salary_max_monthly

                contract = self.salary_processor.normalize_salary(contract)

                if contract.salary_min_monthly != old_min_monthly or contract.salary_max_monthly != old_max_monthly:
                    self.db_update.update_job_contract_monthly(
                        contract_id,
                        contract.salary_min_monthly,
                        contract.salary_max_monthly,
                    )

                contracts.append(contract)

            selected_contract = self.salary_processor.select_contract(contracts)

            if selected_contract:
                self.db_update.update_offer_salary(
                    offer_id=offer_id,
                    salary_min=selected_contract.salary_min_monthly,
                    salary_max=selected_contract.salary_max_monthly,
                    salary_status=self.salary_processor.get_salary_status(selected_contract),
                )
