import logging
import sqlite3

from offer import JobOffer


class Database:
    def __init__(self, db_name: str = "new_offers.db"):
        self.db_name = db_name
        self.logger = logging.getLogger(__name__)

    def save_offers(self, job: JobOffer, source: str):
        self.logger.debug("SAVING TO DB:", job.title, source)
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(
            """
                    INSERT INTO Offers (title, company, location, salary_min, salary_max, date, source)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
            (job.title, job.company, job.location, job.salary_min, job.salary_max, job.date, source),
        )

        conn.commit()

        conn.close()
