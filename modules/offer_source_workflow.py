import asyncio
import logging
from datetime import datetime
from typing import Any, Literal, TypeAlias
from zoneinfo import ZoneInfo

from database.inserts import InsertDB
from modules.ai_service import AIService
from modules.filter_service import FilterService
from modules.offer_status import OfferStatus
from modules.salary_processor import SalaryProcessor
from offer import JobContract, JobOffer
from scrapers.scraper_offer_adapter import scraper_record_to_contract, scraper_record_to_offer

logger = logging.getLogger(__name__)
WARSAW_TIMEZONE = ZoneInfo("Europe/Warsaw")

SourceKind = Literal["email", "scraper"]
EmailOfferRecord: TypeAlias = tuple[JobOffer, str, str | None]
ScraperRecord: TypeAlias = dict[str, Any]
OfferRecord: TypeAlias = EmailOfferRecord | ScraperRecord
OfferBatch: TypeAlias = tuple[SourceKind, str, list[OfferRecord]]


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
        batches: list[OfferBatch] = []
        for parser in self.email_parsers:
            logger.info("Processing source: %s", parser.source)
            offers = await parser.fetch_offers()
            batches.append(("email", parser.source, offers))
        for scraper in self.scrapers:
            try:
                source_name = getattr(scraper, "source", "scraper")
                saved_records = await asyncio.to_thread(scraper.load_saved_offers)
                if self.offline_scrapers:
                    records = saved_records
                elif isinstance(saved_records, list) and saved_records:
                    records = saved_records
                    logger.info(
                        "Using %s saved offers from today for %s; skipping live scrape",
                        len(records),
                        scraper.__class__.__name__,
                    )
                elif self.db_query.has_source_offers_for_date(
                    source_name,
                    datetime.now(WARSAW_TIMEZONE).date(),
                ):
                    records = []
                    logger.info(
                        "Database already has %s offers for today; skipping live scrape",
                        source_name,
                    )
                else:
                    newly_scraped = await asyncio.to_thread(scraper.run_scraper)
                    saved_after_scrape = await asyncio.to_thread(scraper.load_saved_offers)
                    records = (
                        saved_after_scrape
                        if isinstance(saved_after_scrape, list) and saved_after_scrape
                        else newly_scraped
                    )
                logger.info("Loaded %s offers from %s", len(records), scraper.__class__.__name__)
                batches.append(("scraper", source_name, records))
            except Exception:
                logger.exception("Scraper failed: %s; loading its saved output", scraper.__class__.__name__)
                try:
                    records = await asyncio.to_thread(scraper.load_saved_offers)
                    batches.append(("scraper", getattr(scraper, "source", "scraper"), records))
                except Exception:
                    logger.exception("Could not load saved output for %s", scraper.__class__.__name__)

        offer_ids: set[int] = set()
        seen_offers: dict[tuple[str | None, str | None, str | None, str], int] = {}

        for source_kind, source_name, offers in batches:
            logger.info("Processing %s records from %s", len(offers), source_name)
            for index, item in enumerate(offers, start=1):
                if index == 1 or index % 50 == 0 or index == len(offers):
                    logger.info("%s progress: %s/%s", source_name, index, len(offers))

                if isinstance(item, dict):
                    record: ScraperRecord = item
                    offer = scraper_record_to_offer(record)
                    offer_text = ""
                else:
                    offer, offer_text, _cache_id = item

                if not self.filter_service.should_save(offer):
                    continue

                offer_key = (offer.date, offer.title, offer.company, source_name)
                duplicate = seen_offers.get(offer_key)
                if duplicate is None:
                    duplicate = self.db_query.find_same_source_duplicate_id(offer, source_name)

                if duplicate is not None:
                    seen_offers[offer_key] = duplicate
                    logger.debug("Skipping already persisted offer: %s | %s", offer.title, offer.company)
                    continue

                offer.offer_status = self.offer_status.get_offer_status(offer)
                if isinstance(item, dict):
                    contracts = [scraper_record_to_contract(item)]
                else:
                    contracts = await self.ai.validate_salary_api(offer_text) if offer_text else []

                if not contracts:
                    contracts = [JobContract(contract_type="UoP")]

                for contract in contracts:
                    if source_kind == "email":
                        contract = self.salary_processor.resolve_contract_type(
                            contract,
                            offer_text,
                        )

                    self.salary_processor.normalize_salary(contract)

                offer_id = self.db_insert.save_offer_with_contracts(
                    offer,
                    source=source_name,
                    contracts=contracts,
                )
                if offer_id is None:
                    continue
                offer_ids.add(offer_id)

                seen_offers[offer_key] = offer_id

        for parser in self.email_parsers:
            commit_processed_messages = getattr(parser, "commit_processed_messages", None)
            if callable(commit_processed_messages):
                commit_processed_messages()

        return offer_ids
