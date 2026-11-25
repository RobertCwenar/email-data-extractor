import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from config import config
from database.connection import Database
from database.deduplication import Deduplication
from database.inserts import InsertDB
from database.queries import QueryDB
from database.schema import DBSchema
from database.updates import UpdateDB
from modules.ai_service import AIService
from modules.email_sources import build_email_parsers
from modules.filter_service import FilterService
from modules.job_classification_service import JobClassificationService
from modules.job_classifier import JobClassifier
from modules.offer_source_workflow import OfferSourceWorkflow
from modules.offer_status import OfferStatus
from modules.salary_estimator import SalaryEstimator
from modules.salary_history import SalaryHistory
from modules.salary_processor import SalaryProcessor
from parsers.salary_parser import SalaryParser
from scrapers.justjoin_scraper import JustJoinScraper
from scrapers.linkedin_scraper import LinkedInScraper
from scrapers.pracuj_scraper import Scraper
from scrapers.rocketjobs_scraper import RocketJobsScraper
from scrapers.theprotocol_scraper import TheProtocolScraper

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("etl.log"),
        logging.StreamHandler(),
    ],
    force=True,
)
logger = logging.getLogger(__name__)

print(Path("etl.log").resolve())


# Main function to orchestrate the job offer processing
async def _run_pipeline(*, skip_scrapers: bool = False) -> None:
    logger.info(
        "ETL started (scrapers=%s)",
        "disabled" if skip_scrapers else "enabled",
    )

    db = Database()
    try:
        await _run_pipeline_with_database(db, skip_scrapers=skip_scrapers)
    finally:
        db.close()


async def _run_pipeline_with_database(db: Database, *, skip_scrapers: bool) -> None:
    api_key = os.getenv("KEY_API", "").strip()
    ai = AIService(api_key)

    db_insert = InsertDB(db)
    db_query = QueryDB(db)
    deduplication = Deduplication(db)
    db_update = UpdateDB(db)
    schema = DBSchema(db)
    logger.info("Ensuring database schema and ETL indexes")
    schema.create_tables()
    logger.info("Marking contracts already in Neon as legacy salary records")
    schema.mark_legacy_salary_estimations_complete()
    schema.create_performance_indexes()
    logger.info("Database schema and ETL indexes are ready")

    offer_status = OfferStatus(db_query, db_update)
    logger.info("Updating ended offer statuses")
    offer_status.update_ended_offers()
    filter_service = FilterService(config)

    email_config = {
        "host": os.getenv("EMAIL_HOST"),
        "port": int(os.getenv("EMAIL_PORT", 993)),
        "user": os.getenv("EMAIL"),
        "password": os.getenv("PASSWORD"),
    }

    salary_history = SalaryHistory(db_query)
    logger.info("Processing salary history")
    salary_history.process_history()

    salary_estimator = SalaryEstimator(salary_history)
    salary_processor = SalaryProcessor()
    salary_parser = SalaryParser()
    classifier = JobClassifier(ai)

    sources = build_email_parsers(
        ai=ai,
        db_insert=db_insert,
        filter_service=filter_service,
        email_config=email_config,
        salary_parser=salary_parser,
    )

    scrapers = [Scraper(), LinkedInScraper(), RocketJobsScraper(), JustJoinScraper(), TheProtocolScraper()]

    classification_service = JobClassificationService(
        db_query,
        db_update,
        db_insert,
        classifier,
        salary_estimator,
        salary_processor,
    )

    source_workflow = OfferSourceWorkflow(
        email_parsers=sources,
        scrapers=scrapers,
        db_query=deduplication,
        db_insert=db_insert,
        filter_service=filter_service,
        offer_status=offer_status,
        ai=ai,
        salary_processor=salary_processor,
        offline_scrapers=skip_scrapers,
    )

    offer_ids = await source_workflow.run()
    logger.info("Normalizing offer locations")
    db_update.normalize_offer_locations()

    logger.info("Starting offer classification and salary processing")
    await classification_service.process_jobs()
    estimated_offer_ids = await classification_service.process_salary_estimations()
    offer_ids.update(estimated_offer_ids)
    await classification_service.process_salary_selection(offer_ids)

    logger.info("ETL finished successfully")


async def main() -> None:
    max_attempts = 2
    for attempt in range(max_attempts):
        try:
            await _run_pipeline(skip_scrapers=attempt > 0)
            return
        except Exception:
            if attempt + 1 >= max_attempts:
                logger.exception("ETL failed after %s attempts; stopping.", max_attempts)
                raise
            logger.exception("ETL attempt %s failed. Retrying once in 30 seconds without scrapers.", attempt + 1)
            await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(main())
