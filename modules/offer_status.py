from datetime import datetime, timedelta

from database.queries import QueryDB
from database.updates import UpdateDB
from offer import JobOffer


class OfferStatus:
    def __init__(self, db_read: QueryDB, db_update: UpdateDB) -> None:
        self.db_read = db_read
        self.db_update = db_update

    def get_offer_status(self, job: JobOffer) -> str:
        if job.date is None:
            return "process"

        offers = self.db_read.get_offer_history(job.title, job.company)

        if not offers:
            return "new"

        last_date = max(datetime.strptime(date, "%Y-%m-%d") for date in offers)
        job_date = datetime.strptime(job.date, "%Y-%m-%d")

        if (job_date - last_date).days >= 30:
            return "new"

        return "process"

    def update_ended_offers(self) -> None:
        offers = [offer for offer in self.db_read.get_offers_for_status() if offer[4] != "ended"]

        grouped_offers: dict[tuple[str, str], list[tuple[int, datetime, str]]] = {}

        for offer in offers:
            offer_id, title, company, date, status = offer

            key = (title, company)
            grouped_offers.setdefault(key, []).append((offer_id, datetime.strptime(date, "%Y-%m-%d"), status))

        today = datetime.today()

        for company_offers in grouped_offers.values():
            cycles = []
            current_cycle: list[tuple[int, datetime, str]] = []

            for offer in company_offers:
                if not current_cycle:
                    current_cycle.append(offer)
                    continue

                offer_date = offer[1]
                previous_offer_date = current_cycle[-1][1]

                days = (offer_date - previous_offer_date).days

                if days >= 30:
                    cycles.append(current_cycle)
                    current_cycle = [offer]
                else:
                    current_cycle.append(offer)

            if current_cycle:
                cycles.append(current_cycle)

            for cycle in cycles:
                last_offer_date = cycle[-1][1]
                if today - last_offer_date >= timedelta(days=30):
                    offer_ids = [offer_id for offer_id, _, _ in cycle]
                    self.db_update.update_offer_status(
                        offer_ids,
                        "ended",
                    )
