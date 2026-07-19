import asyncio
import logging
import os

from dotenv import load_dotenv

from config import config
from modules.ai_service import AIService
from modules.db_save import Database
from modules.filter_service import FilterService
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
        EmailParser(ai, db, filter_service, email_config, "RocketJobs", source="RocketJobs"),
        EmailParser(ai, db, filter_service, email_config, "PRACA", source="Pracuj.pl"),
        EmailParser(ai, db, filter_service, email_config, "Link", source="Linkedin"),
    ]

    for parser in sources:
        offers = await parser.fetch_offers()

        for offer in offers:
            result = filter_service.should_save(offer)

            if result:
                db.save_offers(offer, source=parser.source)


if __name__ == "__main__":
    asyncio.run(main())
