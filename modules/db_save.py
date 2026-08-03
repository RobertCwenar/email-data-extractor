import logging
import sqlite3
from datetime import datetime

from offer import JobOffer

logger = logging.getLogger(__name__)


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

    def save_offers(self, job: JobOffer, source: str):
        self.save_company(job.company)
        logger.debug(
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

            return cursor.lastrowid

    def create_companies_table(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS Companies(
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            company TEXT UNIQUE NOT NULL)
            """)

    def save_company(self, company_name: str):
        if not company_name:
            return None

        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                    INSERT OR IGNORE INTO Companies (company)
                        VALUES (?)
                """,
                (company_name,),
            )
            cursor.execute(
                """
                    SELECT id FROM Companies WHERE company = ? 
                    """,
                (company_name,),
            )
            return cursor.fetchone()[0]

    def create_modes_table(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Modes(
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                mode TEXT UNIQUE NOT NULL
                    )
                """)

    def create_job_links_table(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS JobLinks(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                offer_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                source TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """)

    def save_job_link(self, offer_id: int, url: str, source: str):

        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
            INSERT INTO JobLinks
            (   offer_id,
                url,
                source
            )
            VALUES (?, ?, ?)
            """,
                (offer_id, url, source),
            )
