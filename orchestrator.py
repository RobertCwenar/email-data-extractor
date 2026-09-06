import asyncio
import logging
import os

from dotenv import load_dotenv

from config import config
from modules.ai_service import AIService
from modules.db_save import Database
from modules.filter_service import FilterService
from modules.job_classification_service import JobClassificationService
from modules.job_classifier import JobClassifier
from modules.processed_cache import FileCache
from modules.salary_estimator import SalaryEstimator
from modules.salary_history import SalaryHistory
from modules.salary_processor import SalaryProcessor
from offer import JobContract
from parsers.email_parser import EmailParser
from parsers.salary_parsers import SalaryParser

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    api_key = os.getenv("KEY_API", "").strip()
    ai = AIService(api_key)
    db = Database("new_offers.db")
    db.create_tables()
    filter_service = FilterService(config)
    email_config = {
        "host": os.getenv("EMAIL_HOST"),
        "port": int(os.getenv("EMAIL_PORT", 993)),
        "user": os.getenv("EMAIL"),
        "password": os.getenv("PASSWORD"),
    }

    salary_history = SalaryHistory(db)
    salary_history.process_history()

    salary_estimator = SalaryEstimator(salary_history)
    salary_processor = SalaryProcessor()
    salary_parser = SalaryParser()
    classifier = JobClassifier(ai)

    sources = [
        EmailParser(
            ai,
            db,
            filter_service,
            email_config,
            "RocketJobs",
            cache=FileCache("mail_records/processed_rocketjobs_mails.txt"),
            source="RocketJobs",
            salary_parser=salary_parser,
        ),
        EmailParser(
            ai,
            db,
            filter_service,
            email_config,
            "PRACA",
            cache=FileCache("mail_records/processed_praca_mails.txt"),
            source="Pracuj.pl",
            salary_parser=salary_parser,
        ),
        EmailParser(
            ai,
            db,
            filter_service,
            email_config,
            "Link",
            cache=FileCache("mail_records/processed_linkedin_mails.txt"),
            source="Linkedin",
            salary_parser=salary_parser,
        ),
    ]

    classification_service = JobClassificationService(db, classifier, salary_estimator, salary_processor)

    offer_ids = set()

    for parser in sources:
        logger.info(f"Processing source: {parser.source}")

        offers = await parser.fetch_offers()

        for offer, offer_text, cache_id in offers:
            if filter_service.should_save(offer):
                offer_id = db.save_offers(
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
                    db.save_job_contract(contract)

    # Process job classifications and salary estimation
    await classification_service.process_jobs()

    await classification_service.process_salary_estimations()
    offer_ids.update(db.get_job_contract_offer_ids())

    await classification_service.process_salary_selection(offer_ids)


if __name__ == "__main__":
    asyncio.run(main())
