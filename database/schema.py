import logging

from database.connection import Database

logger = logging.getLogger(__name__)


class DBSchema:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create_offers_table(self) -> None:
        with self.db._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS Offers (
                        id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                        title TEXT,
                        company TEXT,
                        location TEXT,
                        salary_min DOUBLE PRECISION,
                        salary_max DOUBLE PRECISION,
                        date TEXT,
                        source TEXT,
                        salary_status TEXT,
                        offer_status TEXT
                    )
                """)

    # Create the JobDetails table
    def create_job_details_table(self) -> None:
        with self.db._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS JobDetails (
                    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    offer_id INTEGER NOT NULL,
                    clean_title TEXT,
                    level TEXT,
                    category TEXT
                )
                """)

    def create_job_contracts_table(self) -> None:
        with self.db._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS JobContracts (
                    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    offer_id INTEGER NOT NULL,
                    contract_type TEXT,
                    salary_currency TEXT,
                    salary_period TEXT,
                    salary_min_offer DOUBLE PRECISION,
                    salary_max_offer DOUBLE PRECISION,
                    salary_min_monthly DOUBLE PRECISION,
                    salary_max_monthly DOUBLE PRECISION,
                    salary_estimation_done BOOLEAN NOT NULL DEFAULT FALSE,
                    FOREIGN KEY (offer_id) REFERENCES Offers(id)
                )
                """)
                cursor.execute(
                    """
                    ALTER TABLE JobContracts
                    ADD COLUMN IF NOT EXISTS salary_estimation_done BOOLEAN NOT NULL DEFAULT FALSE
                    """
                )

    # Create the Companies table
    def create_companies_table(self) -> None:
        with self.db._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS Companies(
                id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY, 
                company TEXT UNIQUE NOT NULL)
                """)

    def create_tables(self) -> None:
        self.create_offers_table()
        self.create_companies_table()
        self.create_job_details_table()
        self.create_job_contracts_table()

    def mark_legacy_salary_estimations_complete(self) -> None:
        migration_key = "job_contract_salary_estimation_new_records_only_v1"
        with self.db._connect() as conn, conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS ETLMigrations (
                    migration_key TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cursor.execute(
                """
                INSERT INTO ETLMigrations (migration_key)
                VALUES (%s)
                ON CONFLICT (migration_key) DO NOTHING
                RETURNING migration_key
                """,
                (migration_key,),
            )
            if cursor.fetchone() is not None:
                cursor.execute(
                    """
                    UPDATE JobContracts
                    SET salary_estimation_done = TRUE
                    WHERE salary_estimation_done IS FALSE
                    """
                )
                logger.info(
                    "Marked %s existing contracts as legacy; salary fields were left unchanged",
                    cursor.rowcount,
                )

    def create_performance_indexes(self) -> None:
        with self.db._connect() as conn, conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS offers_source_duplicate_lookup_idx
                ON Offers (date, title, company, source, id)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS job_contracts_pending_salary_estimation_idx
                ON JobContracts (id)
                WHERE salary_min_offer IS NULL
                    AND salary_max_offer IS NULL
                    AND salary_estimation_done IS FALSE
                """
            )
