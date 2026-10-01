import logging
import sqlite3

logger = logging.getLogger(__name__)

db_name = "new_offers.db"


def migrate_salary_status():
    with sqlite3.connect(db_name) as conn:
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
