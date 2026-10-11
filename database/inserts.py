import logging
from datetime import datetime
from typing import Any

from database.connection import Database
from offer import JobContract, JobOffer

logger = logging.getLogger(__name__)


class InsertDB:
    def __init__(self, db: Database) -> None:
        self.db = db

    # Save job offer to the database
    def save_offers(self, job: JobOffer, source: str, contract: JobContract | None = None) -> Any | None:
        self.save_company(job.company)
        logger.debug(f"SAVING TO DB: {job.title} {source}")

        job.date = normalize_date(job.date)
        with self.db._connect() as conn, conn.cursor() as cursor:
            cursor.execute(
                """
                    INSERT INTO Offers (
                        title, company, location, salary_min, salary_max,
                        date, source, salary_status, offer_status
                    )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
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

            result = cursor.fetchone()
            if result is None:
                return None
            return result[0]

    # Save company to the Companies table and return its ID
    def save_company(self, company_name: str) -> Any | None:
        if not company_name:
            return None

        with self.db._connect() as conn, conn.cursor() as cursor:
            cursor.execute(
                """
                    INSERT INTO Companies (company)
                    VALUES (%s)
                    ON CONFLICT (company) DO NOTHING
                """,
                (company_name,),
            )
            cursor.execute(
                """
                    SELECT id FROM Companies WHERE company = %s
                    """,
                (company_name,),
            )
            result = cursor.fetchone()
            if result is None:
                return None
            return result[0]

    def save_job_contract(self, contract: JobContract) -> None:
        with self.db._connect() as conn:
            with conn.cursor() as cursor:
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
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
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
    ) -> None:
        with self.db._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO JobDetails (
                        offer_id,
                        clean_title,
                        level,
                        category
                    )
                    VALUES (%s, %s, %s, %s)
                    """,
                    (offer_id, clean_title, level, category),
                )


# Normalize date to a standard format
def normalize_date(value: Any) -> str | None:
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
