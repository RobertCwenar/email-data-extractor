import logging

from dotenv import load_dotenv

from database.connection import Database

logger = logging.getLogger(__name__)
load_dotenv()


def migrate_job_details() -> None:
    db = Database()

    with db._connect() as conn:
        with conn.cursor() as cursor:
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
            result = cursor.fetchone()
            if result is not None:
                count = result[0]
                logger.info(f"JobDetails contains {count} records")


if __name__ == "__main__":
    migrate_job_details()
