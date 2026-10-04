import asyncio
import os
import sys

from dotenv import load_dotenv

from database.database import Database
from database.inserts import InsertDB
from database.queries import QueryDB
from database.updates import UpdateDB
from modules.ai_service import AIService
from modules.salary_processor import SalaryProcessor
from modules.salary_recovery import SalaryRecovery


async def main():
    load_dotenv()

    if len(sys.argv) != 2:
        print("Usage: uv run python salary_recovery.py <offer_id>")
        return

    offer_id = int(sys.argv[1])

    db = Database()
    db_query = QueryDB(db)
    db_insert = InsertDB(db)
    db_update = UpdateDB(db)

    api_key = os.getenv("KEY_API", "").strip()
    ai = AIService(api_key)

    salary_processor = SalaryProcessor()

    email_config = {
        "host": os.getenv("EMAIL_HOST"),
        "port": int(os.getenv("EMAIL_PORT", 993)),
        "user": os.getenv("EMAIL"),
        "password": os.getenv("PASSWORD"),
    }

    recovery = SalaryRecovery(
        ai=ai,
        email_config=email_config,
        salary_processor=salary_processor,
        db_query=db_query,
        db_insert=db_insert,
        db_update=db_update,
    )

    result = await recovery.recover(offer_id)

    print(f"Salary recovery: {result}")


if __name__ == "__main__":
    asyncio.run(main())
