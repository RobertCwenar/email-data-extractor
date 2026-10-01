from database.database import Database


class DatabaseUpdate:
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
    ):
        with self.db._connect() as conn:
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

            conn.commit()

    def update_offer_salary(
        self,
        offer_id: int,
        salary_min: float | None,
        salary_max: float | None,
        salary_status: str,
    ):
        with self.db._connect() as conn:
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
        with self.db._connect() as conn:
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

    def update_job_contract_monthly(
        self,
        contract_id: int,
        salary_min_monthly: float | None,
        salary_max_monthly: float | None,
    ):
        with self.db._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE JobContracts
                SET salary_min_monthly = ?,
                    salary_max_monthly = ?
                WHERE id = ?
                """,
                (
                    salary_min_monthly,
                    salary_max_monthly,
                    contract_id,
                ),
            )

            conn.commit()

    def update_offer_status(self, rowids: list[int], status: str) -> None:
        with self.db._connect() as conn:
            cursor = conn.cursor()

            cursor.executemany(
                """
                UPDATE Offers
                SET offer_status = ?
                WHERE id = ?
                """,
                [(status, id) for id in rowids],
            )

            conn.commit()

    def update_job_category(self, offer_id: int, category: str):
        with self.db._connect() as conn:
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
