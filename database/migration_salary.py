import logging
import sqlite3

DB = "new_offers.db"

logger = logging.getLogger(__name__)


def migrate_job_salary():
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, salary_min, salary_max
            FROM Offers
        """)

        offers = cursor.fetchall()

        logger.info(f"Found {len(offers)} offers")

        for offer_id, salary_min, salary_max in offers:
            try:
                cursor.execute(
                    """
                    INSERT INTO JobContracts
                    (offer_id, salary_min_offer, salary_max_offer)
                    VALUES (?, ?, ?)
                    """,
                    (
                        offer_id,
                        salary_min,
                        salary_max,
                    ),
                )

            except sqlite3.Error as e:
                logger.warning(
                    f"Could not save JobContracts for offer {offer_id}: {e}"
                )

        cursor.execute("""
            SELECT COUNT(*)
            FROM JobContracts
        """)

        count = cursor.fetchone()[0]

        logger.info(f"JobContracts contains {count} records")


if __name__ == "__main__":
    migrate_job_salary()