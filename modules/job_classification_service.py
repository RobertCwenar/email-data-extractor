import logging
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
        classifications_by_title: dict[str, tuple[Any, ...] | None] = {}

        for index, (offer_id, title, company, date, has_details) in enumerate(jobs, start=1):
            if not title:
                continue

            if title not in classifications_by_title:
                classifications_by_title[title] = self.db_query.get_classification_by_title(title)
            cached = classifications_by_title[title]

            if cached and cached[1]:
                logger.debug(f"Classification cache: {title}")
                level, category = cached

            else:
                logger.debug(f"New Classification: {title}")
                level = self.classifier.classify_level(title)
                category = await self.classifier.classify_category(title)
                classifications_by_title[title] = (level, category)

            if has_details:
                self.db_update.update_job_category(offer_id, category)
            else:
                self.db_insert.save_job_details(
                    offer_id,
                    title,
                    level,
                    category,
                )

    async def process_salary_estimations(self) -> set[int]:
        contracts = self.db_query.get_job_contracts_for_salary_estimator()

        logger.debug("Contracts for salary estimation: %s", len(contracts))
        estimated_offers: dict[int, tuple[float | None, float | None, str, int]] = {}
        contract_updates: list[tuple[str, str, str, float | None, float | None, int]] = []

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

            logger.debug("Salary re-estimation for: %s %s %s", offer_id, salary_min, salary_max)
            estimated_offers[offer_id] = (salary_min, salary_max, "estimated", offer_id)
            contract_updates.append(("UoP", "PLN", "monthly", salary_min, salary_max, contract_id))

        with self.db_query.db._connect() as conn:
            self.db_update.update_offer_salaries(list(estimated_offers.values()), conn)
            self.db_update.update_job_contract_salaries(contract_updates, conn)

        return set(estimated_offers)

    async def process_salary_selection(self, offer_ids: set[int]) -> None:
        if not offer_ids:
            return

        rows = self.db_query.get_job_contracts_for_offers(offer_ids)
        contracts_by_offer: dict[int, list[tuple[Any, ...]]] = {}
        for row in rows:
            contracts_by_offer.setdefault(row[1], []).append(row)

        contract_updates: list[tuple[float | None, float | None, int]] = []
        offer_updates: dict[int, tuple[float | None, float | None, str, int]] = {}

        for offer_id in sorted(offer_ids):
            contracts = []
            for row in contracts_by_offer.get(offer_id, []):
                contract_id = row[0]
                contract = JobContract(
                    offer_id=offer_id,
                    contract_type=row[2],
                    salary_currency=row[3],
                    salary_period=row[4],
                    salary_min_offer=row[5],
                    salary_max_offer=row[6],
                    salary_min_monthly=row[7],
                    salary_max_monthly=row[8],
                )
                old_monthly = (contract.salary_min_monthly, contract.salary_max_monthly)
                contract = self.salary_processor.normalize_salary(contract)
                new_monthly = (contract.salary_min_monthly, contract.salary_max_monthly)
                if new_monthly != old_monthly:
                    contract_updates.append((*new_monthly, contract_id))
                contracts.append(contract)

            selected_contract = self.salary_processor.select_contract(contracts)
            logger.debug("Salary selection: offer_id=%s, selected=%s", offer_id, selected_contract)
            if selected_contract:
                offer_updates[offer_id] = (
                    selected_contract.salary_min_monthly,
                    selected_contract.salary_max_monthly,
                    self.salary_processor.get_salary_status(selected_contract),
                    offer_id,
                )

        with self.db_query.db._connect() as conn:
            if contract_updates:
                self.db_update.update_job_contract_monthlies(contract_updates, conn)
            if offer_updates:
                self.db_update.update_offer_salaries(list(offer_updates.values()), conn)
