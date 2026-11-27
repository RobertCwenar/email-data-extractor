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
    logger.info("Initializing AI and database services")

    api_key = os.getenv("KEY_API", "").strip()
    ai = AIService(api_key)
    db = Database()

    db_insert = InsertDB(db)
    db_query = QueryDB(db)
    deduplication = Deduplication(db)
    db_update = UpdateDB(db)

    offer_status = OfferStatus(db_query, db_update)
    logger.info("Updating ended offer statuses")
    offer_status.update_ended_offers()
    logger.info("Ended offer statuses updated")
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
    logger.info(
        "Salary history processed: %s records, %s groups", len(salary_history.history), len(salary_history.statistics)
    )

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
    new_offer_ids = source_workflow.new_offer_ids
    logger.info(
        "Offer source workflow finished: %s seen offer IDs, %s newly inserted offers",
        len(offer_ids),
        len(new_offer_ids),
    )
    logger.info("Normalizing offer locations")
    db_update.normalize_offer_locations()
    logger.info("Offer locations normalized")

    logger.info("Starting job classification")
    await classification_service.process_jobs()
    logger.info("Job classification finished")
    logger.info("Starting salary estimations")
    await classification_service.process_salary_estimations(new_offer_ids)
    logger.info("Salary estimations finished")

    logger.info("Starting salary selection for %s newly added offers", len(new_offer_ids))
    await classification_service.process_salary_selection(new_offer_ids)

    logger.info("ETL finished successfully")


async def main() -> None:
    skip_scrapers = False
    while True:
        try:
            await _run_pipeline(skip_scrapers=skip_scrapers)
            return
        except Exception:
            logger.exception("ETL failed. Retrying in 90 seconds without scrapers.")
            skip_scrapers = True
            await asyncio.sleep(90)


if __name__ == "__main__":
    asyncio.run(main())
