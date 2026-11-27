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

    def find_same_source_duplicates_batch(
        self,
        offers: list[JobOffer],
        source: str,
    ) -> dict[tuple[Any, str, str, str], tuple[int, bool]]:
        valid_offers = [offer for offer in offers if offer.date]

        if not valid_offers:
            return {}

        values = list(dict.fromkeys((offer.date, offer.title, offer.company) for offer in valid_offers))

        with self.db._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
            WITH input_offers(date, title, company) AS (
                SELECT *
                FROM UNNEST(%s::text[], %s::text[], %s::text[])
            )
            SELECT DISTINCT ON (o.date, o.title, o.company)
                o.date,
                o.title,
                o.company,
                o.id,
                EXISTS (
                    SELECT 1
                    FROM JobContracts jc
                    WHERE jc.offer_id = o.id
                ) AS has_contract
            FROM input_offers i
            JOIN Offers o
                ON o.date = i.date
                AND o.title = i.title
                AND o.company = i.company
                AND o.source = %s
            ORDER BY o.date, o.title, o.company, o.id
            """,
                (
                    [item[0] for item in values],
                    [item[1] for item in values],
                    [item[2] for item in values],
                    source,
                ),
            )

            rows = cursor.fetchall()

        return {
            (date, title, company, source): (offer_id, has_contract)
            for date, title, company, offer_id, has_contract in rows
        }
