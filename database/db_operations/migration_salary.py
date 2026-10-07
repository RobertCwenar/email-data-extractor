import logging

from dotenv import load_dotenv

from database.database import Database

logger = logging.getLogger(__name__)

load_dotenv()


def migrate_job_salary():
    with Database()._connect() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, salary_min, salary_max
            FROM Offers
        """)

        offers = cursor.fetchall()

        logger.info(f"Found {len(offers)} offers")

        for offer_id, salary_min, salary_max in offers:
            cursor.execute(
                """
                INSERT INTO JobContracts
                (offer_id, salary_min_offer, salary_max_offer)
                VALUES (%s, %s, %s)
                """,
                (offer_id, salary_min, salary_max),
            )

        cursor.execute("""
            SELECT COUNT(*)
            FROM JobContracts
        """)

        count_row = cursor.fetchone()
        if count_row is None:
            logger.warning("Could not determine JobContracts count")
            return

        count = count_row[0]

        logger.info(f"JobContracts contains {count} records")


if __name__ == "__main__":
    migrate_job_salary()
