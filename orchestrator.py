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
from parsers.email_parser import EmailParser

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

    sources = [
        EmailParser(
            ai,
            db,
            filter_service,
            email_config,
            "RocketJobs",
            source="RocketJobs",
            cache=FileCache("mail_records/processed_rocketjobs_mails.txt"),
        ),
        EmailParser(
            ai,
            db,
            filter_service,
            email_config,
            "PRACA",
            source="Pracuj.pl",
            cache=FileCache("mail_records/processed_praca_mails.txt"),
        ),
        EmailParser(
            ai,
            db,
            filter_service,
            email_config,
            "Link",
            source="Linkedin",
            cache=FileCache("mail_records/processed_linkedin_mails.txt"),
        ),
    ]

    salary_history = SalaryHistory(db)
    salary_history.process_history()

    salary_estimator = SalaryEstimator(salary_history)

    classifier = JobClassifier(ai)

    classification_service = JobClassificationService(db, classifier, salary_estimator)

    for parser in sources:
        logger.info("Processing source: %s", parser.source)

        offers = await parser.fetch_offers()

        for offer in offers:
            result = filter_service.should_save(offer)

            if result:
                offer.salary_status = salary_estimator.salary_status(offer)
                db.save_offers(offer, source=parser.source)

    # Process job classifications and salary estimation
    await classification_service.process_jobs()

    await classification_service.process_salary_estimations()


if __name__ == "__main__":
    asyncio.run(main())
