from database.database import Database


class DBSchema:
    def __init__(self, db: Database):
        self.db = db

    # Create the JobDetails table
    def create_job_details_table(self):
        with self.db._connect() as conn:
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
        with self.db._connect() as conn:
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

    # Create the Companies table
    def create_companies_table(self):
        with self.db._connect() as conn:
            cursor = conn.cursor()

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS Companies(
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            company TEXT UNIQUE NOT NULL)
            """)

    def create_tables(self):
        self.create_companies_table()
        self.create_job_details_table()
        self.create_job_contracts_table()
