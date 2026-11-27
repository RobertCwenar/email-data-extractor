import logging
import time
from typing import Any

from offer import JobClassification, JobContract

logger = logging.getLogger(__name__)


class JobClassificationService:
    # Initialize the JobClassificationServce with database and classifier instances
    def __init__(
        self, queries: Any, updates: Any, inserts: Any, classifier: Any, salary_estimator: Any, salary_processor: Any
    ) -> None:
        self.db_query = queries
        self.db_update = updates
        self.db_insert = inserts
        self.classifier = classifier
        self.salary_estimator = salary_estimator
        self.salary_processor = salary_processor

    # Process jobs for classification and save the results to the database
    async def process_jobs(self) -> None:

        jobs = self.db_query.get_jobs_for_classification()
        total = len(jobs)
        logger.info("Loaded %s jobs for classification", total)

        for index, (offer_id, title, company, date) in enumerate(jobs, start=1):
            if not title:
                logger.debug("Skipping classification %s/%s: offer_id=%s has no title", index, total, offer_id)
                continue

            started_at = time.monotonic()
            logger.debug("Classifying job %s/%s: offer_id=%s title=%r", index, total, offer_id, title)

            cached = self.db_query.get_classification_by_title(title)

            if cached and cached[1]:
                logger.debug(f"Classification cache: {title}")
                level, category = cached

            else:
                logger.debug(f"New Classification: {title}")
                level = self.classifier.classify_level(title)
                category = await self.classifier.classify_category(title)

            if self.db_query.job_details_exists(offer_id):
                self.db_update.update_job_category(offer_id, category)
            else:
                self.db_insert.save_job_details(
                    offer_id,
                    title,
                    level,
                    category,
                )
            logger.debug(
                "Classified job %s/%s: offer_id=%s category=%s (%.2fs)",
                index,
                total,
                offer_id,
                category,
                time.monotonic() - started_at,
            )

    async def process_salary_estimations(self, offer_ids: set[int]) -> None:
        contracts = self.db_query.get_job_contracts_for_salary_estimator()
        contracts = [contract for contract in contracts if contract[1] in offer_ids]

        logger.info("Loaded %s new-offer contracts for salary estimation", len(contracts))
        with self.db_query.db._connect() as conn:
            for index, (contract_id, offer_id, title, company, date, level, category) in enumerate(contracts, start=1):
                logger.debug(
                    "Estimating salary %s/%s: contract_id=%s offer_id=%s", index, len(contracts), contract_id, offer_id
                )
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
                    conn=conn,
                )

                self.db_update.update_job_contract_salary(
                    contract_id,
                    "UoP",
                    "PLN",
                    "monthly",
                    salary_min,
                    salary_max,
                    conn,
                )
                logger.debug(
                    "Salary estimated %s/%s: contract_id=%s range=%s-%s",
                    index,
                    len(contracts),
                    contract_id,
                    salary_min,
                    salary_max,
                )

    async def process_salary_selection(self, offer_ids: set[int]) -> None:
        logger.debug("Opening database connection for salary selection (%s offers)", len(offer_ids))
        with self.db_query.db._connect() as conn:
            for index, offer_id in enumerate(offer_ids, start=1):
                logger.debug("Selecting salary %s/%s: offer_id=%s", index, len(offer_ids), offer_id)
                rows = self.db_query.get_job_contracts(offer_id, conn)

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
                            conn,
                        )

                    contracts.append(contract)

                selected_contract = self.salary_processor.select_contract(contracts)
                logger.debug(
                    "Salary selection: offer_id=%s, selected=%s",
                    offer_id,
                    selected_contract,
                )
                if selected_contract:
                    self.db_update.update_offer_salary(
                        offer_id=offer_id,
                        salary_min=selected_contract.salary_min_monthly,
                        salary_max=selected_contract.salary_max_monthly,
                        salary_status=self.salary_processor.get_salary_status(selected_contract),
                        conn=conn,
                    )
                if selected_contract:
                    logger.debug(
                        "Salary selected %s/%s: offer_id=%s status=%s monthly_range=%s-%s",
                        index,
                        len(offer_ids),
                        offer_id,
                        self.salary_processor.get_salary_status(selected_contract),
                        selected_contract.salary_min_monthly,
                        selected_contract.salary_max_monthly,
                    )
                else:
                    logger.debug("No salary contract selected %s/%s: offer_id=%s", index, len(offer_ids), offer_id)
