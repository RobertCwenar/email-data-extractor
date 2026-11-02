import asyncio
import logging
from typing import Literal

from database.inserts import InsertDB
from modules.ai_service import AIService
from modules.filter_service import FilterService
from modules.offer_status import OfferStatus
from modules.salary_processor import SalaryProcessor
from offer import JobContract, JobOffer
from scrapers.scraper_offer_adapter import scraper_record_to_contract, scraper_record_to_offer

logger = logging.getLogger(__name__)

SourceKind = Literal["email", "scraper"]


class OfferSourceWorkflow:
    def __init__(
        self,
        *,
        email_parsers,
        scrapers,
        db_query,
        db_insert: InsertDB,
        filter_service: FilterService,
        offer_status: OfferStatus,
        ai: AIService,
        salary_processor: SalaryProcessor,
        offline_scrapers: bool = False,
    ) -> None:
        self.email_parsers = email_parsers
        self.scrapers = scrapers
        self.db_query = db_query
        self.db_insert = db_insert
        self.filter_service = filter_service
        self.offer_status = offer_status
        self.ai = ai
        self.salary_processor = salary_processor
        self.offline_scrapers = offline_scrapers

    async def run(self) -> set[int]:
        batches: list[tuple[SourceKind, str, list[tuple[JobOffer, str, str | None]]]] = []
        for parser in self.email_parsers:
            logger.info("Processing source: %s", parser.source)
            offers = await parser.fetch_offers()
            batches.append(("email", parser.source, offers))
        for scraper in self.scrapers:
            try:
                load_offers = scraper.load_saved_offers if self.offline_scrapers else scraper.run_scraper
                records = await asyncio.to_thread(load_offers)
                logger.info("Loaded %s offers from %s", len(records), scraper.__class__.__name__)
                batches.append(("scraper", getattr(scraper, "source", "scraper"), records))
            except Exception:
                logger.exception("Scraper failed: %s; loading its saved output", scraper.__class__.__name__)
                try:
                    records = await asyncio.to_thread(scraper.load_saved_offers)
                    batches.append(("scraper", getattr(scraper, "source", "scraper"), records))
                except Exception:
                    logger.exception("Could not load saved output for %s", scraper.__class__.__name__)

        offer_ids: set[int] = set()

        for source_kind, source_name, offers in batches:
            for item in offers:
                if source_kind == "scraper":
                    record = item
                    offer = scraper_record_to_offer(record)
                    offer_text = ""
                else:
                    offer, offer_text, _cache_id = item

                if not self.filter_service.should_save(offer):
                    continue

                same_source_duplicate_id = self.db_query.find_same_source_duplicate_id(offer, source_name)
                if isinstance(same_source_duplicate_id, int):
                    offer_id = same_source_duplicate_id
                    if self.db_query.has_job_contract(offer_id):
                        offer_ids.add(offer_id)
                        logger.info("Skipping already persisted offer: %s | %s", offer.title, offer.company)
                        continue
                else:
                    offer.offer_status = self.offer_status.get_offer_status(offer)
                    saved_offer_id = self.db_insert.save_offers(offer, source=source_name)
                    if saved_offer_id is None:
                        continue
                    offer_id = saved_offer_id

                offer_ids.add(offer_id)

                if source_kind == "scraper":
                    contracts = [scraper_record_to_contract(record)]
                else:
                    contracts = await self.ai.validate_salary_api(offer_text) if offer_text else []

                if not contracts:
                    contracts = [JobContract(contract_type="UoP")]

                for contract in contracts:
                    contract.offer_id = offer_id

                    if source_kind == "email":
                        contract = self.salary_processor.resolve_contract_type(
                            contract,
                            offer_text,
                        )

                    self.salary_processor.normalize_salary(contract)
                    self.db_insert.save_job_contract(contract)

        for parser in self.email_parsers:
            commit_processed_messages = getattr(parser, "commit_processed_messages", None)
            if callable(commit_processed_messages):
                commit_processed_messages()

        return offer_ids
