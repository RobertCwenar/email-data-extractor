import logging
import sqlite3
from datetime import datetime

from offer import JobOffer

logger = logging.getLogger(__name__)


# Normalize date to a standard format
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
    # Try pasing the value through each format untill one works
    for format in formats:
        try:
            return datetime.strptime(value, format).strftime("%Y-%m-%d")
        except ValueError:
            pass

    return None


# Database class for saving job offers and related data to SQLite database
class Database:
    def __init__(self, db_name: str = "new_offers.db"):
        self.db_name = db_name

    # Save job offer to the database
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

    # Create the Companies table
    def create_companies_table(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS Companies(
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            company TEXT UNIQUE NOT NULL)
            """)

    # Save company to the Companies table and return its ID
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

    # Create the modes table
    def create_modes_table(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Modes(
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                mode TEXT UNIQUE NOT NULL
                    )
                """)

    # Create the JobLinks table
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

    # Save job link to the Joblinks table
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

    # Create the JobDetails table
    def create_job_details_table(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS JobDetails(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                offer_id INTEGER NOT NULL,
                clean_title TEXT,
                level TEXT,
                category TEXT
            )
            """)

            conn.commit()

    # Save job details to the JobDetails table
    def save_job_details(
        self,
        offer_id: int,
        clean_title: str,
        level: str,
        category: str,
    ):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO JobDetails (
                    offer_id,
                    clean_title,
                    level,
                    category
                )
                VALUES (?, ?, ?, ?)
                """,
                (offer_id, clean_title, level, category),
            )

            conn.commit()

    # Get jobs for classification from the Offers table
    def get_jobs_for_classification(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT o.id, o.title
                FROM Offers o
                LEFT JOIN JobDetails jd ON jd.offer_id = o.id
                WHERE jd.offer_id IS NULL
                    or jd.category IS NULL
            """)

            return cursor.fetchall()

    def get_classification_by_title(self, clean_title: str):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT level, category
                FROM JobDetails
                WHERE clean_title = ?
                LIMIT 1
                """,
                (clean_title,),
            )

            return cursor.fetchone()

    def update_job_category(self, offer_id: int, category: str):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE JobDetails
                SET category = ?
                WHERE offer_id = ?
                """,
                (category, offer_id),
            )

            conn.commit()
