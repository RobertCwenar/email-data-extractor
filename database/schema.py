from database.database import Database


class DBSchema:
    def __init__(self, db: Database):
        self.db = db

    def create_offers_table(self):
        with self.db._connect() as conn:
            cursor = conn.cursor()

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
    def create_job_details_table(self):
        with self.db._connect() as conn:
            cursor = conn.cursor()

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS JobDetails (
                id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                offer_id INTEGER NOT NULL,
                clean_title TEXT,
                level TEXT,
                category TEXT
            )
            """)

    def create_job_contracts_table(self):
        with self.db._connect() as conn:
            cursor = conn.cursor()

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
                FOREIGN KEY (offer_id) REFERENCES Offers(id)
            )
            """)

    # Create the Companies table
    def create_companies_table(self):
        with self.db._connect() as conn:
            cursor = conn.cursor()

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS Companies(
            id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY, 
            company TEXT UNIQUE NOT NULL)
            """)

    def create_tables(self):
        self.create_offers_table()
        self.create_companies_table()
        self.create_job_details_table()
        self.create_job_contracts_table()
