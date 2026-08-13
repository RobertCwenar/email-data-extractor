import logging
import sqlite3

DB = "new_offers.db"

logger = logging.getLogger(__name__)


def migrate_job_details():
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title
        FROM Offers
    """)

    offers = cursor.fetchall()

    logger.info(f"Found {len(offers)} offers")

    for offer in offers:
        try:
            cursor.execute(
                """
                INSERT INTO JobDetails
                (offer_id, clean_title, level, category)
                VALUES (?, ?, ?, ?)
                """,
                (
                    offer[0],
                    offer[1],
                    None,
                    None,
                ),
            )
        except sqlite3.Error as e:
            logger.warning(f"Could not save JobDetails for offer {offer[0]} {offer[1]}: {e}")

    cursor.execute("""
        SELECT COUNT(*)
        FROM JobDetails
    """)

    logger.info(f"JobDetails after: {cursor.fetchone()[0]}")


if __name__ == "__main__":
    migrate_job_details()
