import asyncio
import logging
import os

from dotenv import load_dotenv

from config import config
from modules.ai_service import AIService
from modules.db_save import Database
from modules.filter_service import FilterService
from modules.processed_cache import FileCache
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

    for parser in sources:
        logger.info("Processing source: %s", parser.source)

        offers = await parser.fetch_offers()
        logger.info("%s found  %s offers", parser.source, len(offers))

        for offer in offers:
            result = filter_service.should_save(offer)

            if result:
                db.save_offers(offer, source=parser.source)


if __name__ == "__main__":
    asyncio.run(main())
