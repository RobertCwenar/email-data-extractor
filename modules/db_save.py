import logging
import sqlite3
from datetime import datetime

from offer import JobOffer


def normalize_date(value):
    if not value:
        return None

    value = str(value).strip()

    formats = [
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S%z",
    ]

    for format in formats:
        try:
            return datetime.strptime(value, format).strftime("%Y-%m-%d")
        except ValueError:
            pass

    return None


class Database:
    def __init__(self, db_name: str = "new_offers.db"):
        self.db_name = db_name
        self.logger = logging.getLogger(__name__)

    def save_offers(self, job: JobOffer, source: str):
        self.logger.debug(
            "SAVING TO DB: %s (%s)",
            job.title,
            source,
        )

        job.date = normalize_date(job.date)
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                    INSERT INTO Offers (title, company, location, salary_min, salary_max, date, source)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (job.title, job.company, job.location, job.salary_min, job.salary_max, job.date, source),
            )
