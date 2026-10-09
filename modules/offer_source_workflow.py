import logging
from typing import Literal

from database.inserts import InsertDB
from modules.ai_service import AIService
from modules.filter_service import FilterService
from modules.offer_status import OfferStatus
from modules.salary_processor import SalaryProcessor
from offer import JobContract, JobOffer
from parsers.scraper_offer_adapter import scraper_record_to_offer

logger = logging.getLogger(__name__)

SourceKind = Literal["email", "scraper"]


class OfferSourceWorkflow:
    def __init__(
        self,
        *,
        email_parsers,
        scraper,
        db_query,
        db_insert: InsertDB,
        filter_service: FilterService,
        offer_status: OfferStatus,
        ai: AIService,
        salary_processor: SalaryProcessor,
    ) -> None:
        self.email_parsers = email_parsers
        self.scraper = scraper
        self.db_query = db_query
        self.db_insert = db_insert
        self.filter_service = filter_service
        self.offer_status = offer_status
        self.ai = ai
        self.salary_processor = salary_processor

    async def run(self) -> set[int]:
        batches: list[tuple[SourceKind, str, list[tuple[JobOffer, str, str | None]]]] = []
        for parser in self.email_parsers:
            logger.info("Processing source: %s", parser.source)
            batches.append(("email", parser.source, await parser.fetch_offers()))
        records = self.scraper.load_todays_offers()
        batches.append(("scraper", "scraper", [scraper_record_to_offer(record) for record in records]))

        offer_ids: set[int] = set()

        for source_kind, source_name, offers in batches:
            for offer, offer_text, _cache_id in offers:
                if not self.filter_service.should_save(offer):
                    continue

                duplicate_id = self.db_query.find_cross_source_duplicate_id(
                    offer,
                    source_kind,
                )
                if duplicate_id is not None:
                    logger.info(
                        "Skipping cross-source duplicate: %s | %s",
                        offer.title,
                        offer.company,
                    )
                    continue

                offer.offer_status = self.offer_status.get_offer_status(offer)
                offer_id = self.db_insert.save_offers(offer, source=source_name)
                offer_ids.add(offer_id)

                contracts = await self.ai.validate_salary_api(offer_text) if offer_text else []
                if not contracts:
                    contracts = [JobContract(contract_type="UoP")]

                for contract in contracts:
                    contract.offer_id = offer_id
                    contract = self.salary_processor.resolve_contract_type(
                        contract,
                        offer_text,
                    )
                    self.salary_processor.normalize_salary(contract)
                    self.db_insert.save_job_contract(contract)

        return offer_ids
