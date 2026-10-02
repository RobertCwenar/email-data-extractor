import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from config import config
from database.database import Database
from database.inserts import InsertDB
from database.queries import QueryDB
from database.schema import DBSchema
from database.updates import UpdateDB
from modules.ai_service import AIService
from modules.email_sources import build_email_parsers
from modules.filter_service import FilterService
from modules.job_classification_service import JobClassificationService
from modules.job_classifier import JobClassifier
from modules.offer_status import OfferStatus
from modules.salary_estimator import SalaryEstimator
from modules.salary_history import SalaryHistory
from modules.salary_processor import SalaryProcessor
from offer import JobContract
from parsers.salary_parsers import SalaryParser

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
async def main() -> None:
    logger.info("ETL started")
    api_key = os.getenv("KEY_API", "").strip()
    ai = AIService(api_key)
    db = Database()

    db_insert = InsertDB(db)
    db_query = QueryDB(db)
    db_update = UpdateDB(db)
    db_schema = DBSchema(db)

    db_schema.create_tables()
    offer_status = OfferStatus(db_query, db_update)
    offer_status.update_ended_offers()
    filter_service = FilterService(config)
    email_config = {
        "host": os.getenv("EMAIL_HOST"),
        "port": int(os.getenv("EMAIL_PORT", 993)),
        "user": os.getenv("EMAIL"),
        "password": os.getenv("PASSWORD"),
    }

    salary_history = SalaryHistory(db_query)
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

    classification_service = JobClassificationService(
        db_query, db_update, db_insert, classifier, salary_estimator, salary_processor
    )

    offer_ids = set()

    for parser in sources:
        logger.info(f"Processing source: {parser.source}")

        offers = await parser.fetch_offers()

        for offer, offer_text, cache_id in offers:
            if filter_service.should_save(offer):
                offer.offer_status = offer_status.get_offer_status(offer)
                offer_id = db_insert.save_offers(
                    offer,
                    source=parser.source,
                )
                offer_ids.add(offer_id)
                contracts = []

                if offer_text:
                    contracts = await ai.validate_salary_api(offer_text)

                if not contracts:
                    contracts = [JobContract(contract_type="UoP")]

                for contract in contracts:
                    contract.offer_id = offer_id
                    contract = salary_processor.resolve_contract_type(contract, offer_text)
                    salary_processor.normalize_salary(contract)
                    db_insert.save_job_contract(contract)

    # Process job classifications and salary estimation
    await classification_service.process_jobs()

    await classification_service.process_salary_estimations()
    offer_ids.update(db_query.get_job_contract_offer_ids())

    await classification_service.process_salary_selection(offer_ids)

    logger.info("ETL finished successfully")


# Run the main function
if __name__ == "__main__":
    asyncio.run(main())
