from typing import Any, Literal

from offer import JobOffer


class Deduplication:
    def __init__(self, db: Any) -> None:
        self.db = db

    def find_cross_source_duplicate_id(
        self,
        offer: JobOffer,
        source_kind: Literal["email", "scraper"],
    ) -> int | None:
        if not offer.date:
            return None

        with self.db._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, source
                FROM Offers
                WHERE date = %s
                AND title = %s
                AND company = %s
                """,
                (offer.date, offer.title, offer.company),
            )

            row = cursor.fetchone()
            if not row:
                return None

            offer_id, existing_source = row

            if source_kind == "scraper" and existing_source != "scraper":
                return offer_id

            if source_kind == "email" and existing_source == "scraper":
                return offer_id

            return None
