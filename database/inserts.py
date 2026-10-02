import logging
from datetime import datetime

from database.database import Database
from offer import JobContract, JobOffer

logger = logging.getLogger(__name__)


class InsertDB:
    def __init__(self, db: Database):
        self.db = db

    # Save job offer to the database
    def save_offers(self, job: JobOffer, source: str, contract: JobContract | None = None):
        self.save_company(job.company)
        logger.debug(f"SAVING TO DB: {job.title} {source}")

        job.date = normalize_date(job.date)
        with self.db._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                    INSERT INTO Offers (
                        title, company, location, salary_min, salary_max,
                        date, source, salary_status, offer_status
                    )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    job.offer_status,
                ),
            )

            return cursor.lastrowid

    # Save company to the Companies table and return its ID
    def save_company(self, company_name: str):
        if not company_name:
            return None

        with self.db._connect() as conn:
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

    def save_job_contract(self, contract: JobContract):
        with self.db._connect() as conn:
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
        with self.db._connect() as conn:
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
