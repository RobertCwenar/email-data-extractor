import logging

from dotenv import load_dotenv

from database.database import Database

logger = logging.getLogger(__name__)

load_dotenv()


def migrate_salary_status():
    db = Database()

    with db._connect() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE Offers
            Set salary_status = CASE
                WHEN salary_min IS NOT NULL
                    OR salary_max is not null
                    THEN 'offer'
                ELSE 'estimated'
            END
            WHERE salary_status IS NULL
            """
        )
        logger.info(f"Update rows: {cursor.rowcount}")


if __name__ == "__main__":
    migrate_salary_status()
