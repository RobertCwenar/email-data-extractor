from typing import Any

from offer import JobOffer


class Deduplication:
    def __init__(self, db: Any) -> None:
        self.db = db

    def find_same_source_duplicate_id(self, offer: JobOffer, source: str) -> int | None:
        if not offer.date:
            return None

        with self.db._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id
                FROM Offers
                WHERE date = %s
                    AND title = %s
                    AND company = %s
                    AND source = %s
                ORDER BY id
                LIMIT 1
                """,
                (offer.date, offer.title, offer.company, source),
            )
            row = cursor.fetchone()
            return row[0] if row else None

    def has_job_contract(self, offer_id: int) -> bool:
        with self.db._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM JobContracts WHERE offer_id = %s LIMIT 1",
                (offer_id,),
            )
            return cursor.fetchone() is not None
