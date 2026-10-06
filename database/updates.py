from database.database import Database


class UpdateDB:
    def __init__(self, db: Database):
        self.db = db

    def update_job_contract_salary(
        self,
        contract_id: int,
        contract_type: str,
        salary_currency: str,
        salary_period: str,
        salary_min_monthly: float | None,
        salary_max_monthly: float | None,
        conn,
    ):
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE JobContracts
            SET contract_type = %s,
            salary_currency = %s,
            salary_period = %s,
            salary_min_monthly = %s,
            salary_max_monthly = %s
        WHERE id = %s
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

    def update_offer_salary(
        self,
        offer_id: int,
        salary_min: float | None,
        salary_max: float | None,
        salary_status: str,
        conn,
    ):
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE Offers
            SET salary_min = %s,
                salary_max = %s,
                salary_status = %s
            WHERE id = %s
            """,
            (
                salary_min,
                salary_max,
                salary_status,
                offer_id,
            ),
        )

    def update_job_classification(
        self,
        offer_id: int,
        level: str,
        category: str,
    ):
        with self.db._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE JobDetails
                SET level = %s,
                    category = %s
                WHERE offer_id = %s
                """,
                (level, category, offer_id),
            )

    def update_job_contract_monthly(
        self,
        contract_id: int,
        salary_min_monthly: float | None,
        salary_max_monthly: float | None,
        conn,
    ):
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE JobContracts
            SET salary_min_monthly = %s,
                salary_max_monthly = %s
            WHERE id = %s
            """,
            (
                salary_min_monthly,
                salary_max_monthly,
                contract_id,
            ),
        )

    def update_offer_status(self, rowids: list[int], status: str) -> None:
        with self.db._connect() as conn:
            cursor = conn.cursor()

            cursor.executemany(
                """
                UPDATE Offers
                SET offer_status = %s
                WHERE id = %s
                """,
                [(status, id) for id in rowids],
            )

    def update_job_category(self, offer_id: int, category: str):
        with self.db._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE JobDetails
                SET category = %s
                WHERE offer_id = %s
                """,
                (category, offer_id),
            )
