import logging

from dotenv import load_dotenv

from database.database import Database

logger = logging.getLogger(__name__)
load_dotenv()


def migrate_job_details():
    db = Database()

    with db._connect() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, title
            FROM Offers
        """)

        offers = cursor.fetchall()

        logger.info(f"Found {len(offers)} offers")

        for offer_id, title in offers:
            cursor.execute(
                """
                INSERT INTO JobDetails
                (offer_id, clean_title, level, category)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    offer_id,
                    title,
                    None,
                    None,
                ),
            )

        cursor.execute("""
            SELECT COUNT(*)
            FROM JobDetails
        """)
        logger.info(f"JobDetails contains {cursor.fetchone()[0]} records")


if __name__ == "__main__":
    migrate_job_details()
