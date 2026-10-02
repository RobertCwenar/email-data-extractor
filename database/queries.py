from database.database import Database


class QueryDB:
    def __init__(self, db: Database):
        self.db = db

    def get_job_contract(self, offer_id: int):
        with self.db._connect() as conn:
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
        with self.db._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    id,
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
        with self.db._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT DISTINCT offer_id
                FROM JobContracts
                WHERE offer_id IS NOT NULL
                """
            )

            return [row[0] for row in cursor.fetchall()]

    # Get jobs for classification from the Offers table
    def get_jobs_for_classification(self):
        with self.db._connect() as conn:
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
        with self.db._connect() as conn:
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

    def job_details_exists(self, offer_id: int) -> bool:
        with self.db._connect() as conn:
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
        with self.db._connect() as conn:
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

    def get_salary_history(self):
        with self.db._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT o.id, o.title, o.company, o.salary_min, o.salary_max, o.date, jd.category, jd.level
                FROM Offers o
                LEFT JOIN JobDetails jd 
                    ON jd.offer_id = o.id
                WHERE o.salary_status IN ("offer", "offer_calculate")
            """)
            return cursor.fetchall()

    def get_job_contracts_for_salary_estimator(self):
        with self.db._connect() as conn:
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
        with self.db._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
        SELECT offer_id, clean_title, level, category
        FROM JobDetails
        ORDER BY offer_id """
            )

            return cursor.fetchall()

    def get_offer_history(self, title: str, company: str):
        with self.db._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT date
                FROM Offers
                WHERE title = ? AND company = ?
                """,
                (title, company),
            )

            return [row[0] for row in cursor.fetchall()]

    def get_offers_for_status(self):
        with self.db._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, title, company, date, offer_status
                FROM Offers
                WHERE date IS NOT NULL
                ORDER BY company, title, date
                """
            )

            return cursor.fetchall()

    def get_previous_offer(self, offer_id: int, title: str, company: str):
        with self.db._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
            SELECT id
            FROM Offers
            WHERE title = ?
                AND company = ?
                AND id < ?
            ORDER BY id DESC
            LIMIT 1
            """,
                (title, company, offer_id),
            )

        row = cursor.fetchone()
        return row[0] if row else None

    def get_offers(self):
        with self.db._connect() as conn:
            cursor = conn.cursor()

            cursor.execute("""
            SELECT
                id,
                title,
                company,
                location,
                salary_min,
                salary_max,
                date,
                source,
                salary_status,
                offer_status
            FROM Offers
            ORDER BY date DESC
            """)

        return cursor.fetchall()

    def get_offer(self, offer_id: int):
        with self.db._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    id,
                    title,
                    company,
                    location,
                    salary_min,
                    salary_max,
                    date,
                    source,
                    salary_status,
                    offer_status
                FROM Offers
                WHERE id = ?
                """,
                (offer_id,),
            )

            return cursor.fetchone()

    def get_previous_offer_with_salary(
        self,
        offer_id: int,
        title: str,
        company: str,
    ):
        with self.db._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    o.id,
                    o.salary_min,
                    o.salary_max,
                    o.salary_status,
                    jc.contract_type,
                    jc.salary_currency,
                    jc.salary_period,
                    jc.salary_min_offer,
                    jc.salary_max_offer,
                    jc.salary_min_monthly,
                    jc.salary_max_monthly
                FROM Offers o
                JOIN JobContracts jc
                    ON jc.offer_id = o.id
                WHERE o.title = ?
                AND o.company = ?
                AND o.id != ?
                AND o.salary_min IS NOT NULL
                AND o.salary_max IS NOT NULL
                AND o.salary_status IS NOT NULL
                ORDER BY o.id DESC
                LIMIT 1
                """,
                (title, company, offer_id),
            )

            return cursor.fetchone()
