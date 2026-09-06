import logging
import sqlite3
from datetime import datetime

from offer import JobContract, JobOffer

logger = logging.getLogger(__name__)


# Database class for saving job offers and related data to SQLite database
class Database:
    def __init__(self, db_name: str = "new_offers.db"):
        self.db_name = db_name

    # Save job offer to the database
    def save_offers(self, job: JobOffer, source: str, contract: JobContract | None = None):
        self.save_company(job.company)
        logger.debug(f"SAVING TO DB: {job.title} {source}")

        job.date = normalize_date(job.date)
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                    INSERT INTO Offers (title, company, location, salary_min, salary_max, date, source, salary_status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.title,
                    job.company,
                    job.location,
                    job.salary_min,
                    job.salary_max,
                    job.date,
                    source,
                    job.salary_status,
                ),
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

    # Create the JobLinks table
    def create_job_links_table(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS JobLinks(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                offer_id INTEGER NOT NULL,
                title TEXT,
                url TEXT NOT NULL,
                source TEXT,
                filter_keywords TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """)

    # Save job link to the JobLinks table
    def save_job_link(self, offer_id: int, title: str, url: str, source: str, filter_keywords: str):

        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
            INSERT INTO JobLinks
            (   offer_id,
                title,
                url,
                source,
                filter_keywords
            )
            VALUES (?, ?, ?, ?, ?)
            """,
                (offer_id, title, url, source, filter_keywords),
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

    def create_job_contracts_table(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS JobContracts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                offer_id INTEGER NOT NULL,
                contract_type TEXT,
                salary_currency TEXT,
                salary_period TEXT,
                salary_min_offer REAL, 
                salary_max_offer REAL,
                salary_min_monthly REAL, 
                salary_max_monthly REAL,
                FOREIGN KEY (offer_id) REFERENCES Offers(id)
                )
                """)
            conn.commit()

    def save_job_contract(self, contract: JobContract):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO JobContracts (
                    offer_id,
                    contract_type,
                    salary_currency,
                    salary_period,
                    salary_min_offer,
                    salary_max_offer, 
                    salary_min_monthly, 
                    salary_max_monthly
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    contract.offer_id,
                    contract.contract_type,
                    contract.salary_currency,
                    contract.salary_period,
                    contract.salary_min_offer,
                    contract.salary_max_offer,
                    contract.salary_min_monthly,
                    contract.salary_max_monthly,
                ),
            )

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

    def get_job_contract(self, offer_id: int):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT contract_type, salary_period
                FROM JobContracts
                WHERE offer_id = ?
            """,
                (offer_id,),
            )

            return cursor.fetchone()

    def get_job_contracts(self, offer_id: int):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    contract_type,
                    salary_currency,
                    salary_period,
                    salary_min_offer,
                    salary_max_offer,
                    salary_min_monthly,
                    salary_max_monthly
                FROM JobContracts
                WHERE offer_id = ?
                """,
                (offer_id,),
            )

            return cursor.fetchall()

    def get_job_contract_offer_ids(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT DISTINCT offer_id
                FROM JobContracts
                WHERE offer_id IS NOT NULL
                """
            )

            return [row[0] for row in cursor.fetchall()]

    def update_job_contract_salary(
        self,
        contract_id: int,
        contract_type: str,
        salary_currency: str,
        salary_period: str,
        salary_min_monthly: float,
        salary_max_monthly: float,
    ):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE JobContracts
                SET contract_type = ?,
                salary_currency = ?,
                salary_period = ?,
                salary_min_monthly = ?,
                salary_max_monthly = ?
            WHERE id = ?
                """,
                (
                    contract_type,
                    salary_currency,
                    salary_period,
                    salary_min_monthly,
                    salary_max_monthly,
                    contract_id,
                ),
            )

    # Get jobs for classification from the Offers table
    def get_jobs_for_classification(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT o.id, o.title, o.company, o.date
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

    def job_details_exists(self, offer_id: int) -> bool:
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT 1
                FROM JobDetails
                WHERE offer_id = ?
                LIMIT 1
                """,
                (offer_id,),
            )

            return cursor.fetchone() is not None

    def get_salary_status(self, offer_id: int) -> str:
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT salary_status
                FROM Offers
                WHERE id = ?
                """,
                (offer_id,),
            )

            return cursor.fetchone()[0]

    def update_offer_salary(
        self,
        offer_id: int,
        salary_min: float | None,
        salary_max: float | None,
        salary_status: str,
    ):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE Offers
                SET salary_min = ?,
                    salary_max = ?,
                    salary_status = ?
                WHERE id = ?
                """,
                (
                    salary_min,
                    salary_max,
                    salary_status,
                    offer_id,
                ),
            )

            conn.commit()

    def update_job_classification(
        self,
        offer_id: int,
        level: str,
        category: str,
    ):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE JobDetails
                SET level = ?,
                    category = ?
                WHERE offer_id = ?
                """,
                (level, category, offer_id),
            )

            conn.commit()

    def get_salary_history(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT o.id, o.title, o.company, o.salary_min, o.salary_max, o.date, jd.category, jd.level
                FROM Offers o
                LEFT JOIN JobDetails jd 
                    ON jd.offer_id = o.id
                WHERE o.salary_status IN ("offer", "offer_calculate")
            """)
            return cursor.fetchall()

    def create_tables(self):
        self.create_companies_table()
        self.create_job_links_table()
        self.create_job_details_table()
        self.create_job_contracts_table()

    def get_job_contracts_for_salary_estimator(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute("""
            SELECT
                jc.id,
                jc.offer_id,
                o.title,
                o.company,
                o.date,
                jd.level,
                jd.category
            FROM JobContracts jc
            JOIN Offers o
                ON o.id = jc.offer_id
            JOIN JobDetails jd
                ON jd.offer_id = o.id
            WHERE jc.salary_min_offer IS NULL
                AND jc.salary_max_offer IS NULL
                AND jd.level IS NOT NULL
                AND jd.category IS NOT NULL
            """)

        return cursor.fetchall()

    def get_all_job_details_for_migration(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
        SELECT offer_id, clean_title, level, category
        FROM JobDetails
        ORDER BY offer_id """
            )

            return cursor.fetchall()


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
