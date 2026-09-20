from datetime import datetime, timedelta

from modules.db_save import Database
from offer import JobOffer


class OfferStatus:
    def __init__(self, db: Database) -> None:
        self.db = db

    def get_offer_status(self, job: JobOffer) -> str:
        offers = self.db.get_offer_history(job.title, job.company)

        if not offers:
            return "new"

        last_date = max(datetime.strptime(date, "%Y-%m-%d") for date in offers)

        if job.date is None:
            return "process"

        job_date = datetime.strptime(job.date, "%Y-%m-%d")

        if (job_date - last_date).days >= 30:
            return "new"

        return "process"

    def update_ended_offers(self) -> None:
        # ``Database`` exposes all offers; only active offers can become ended.
        offers = [offer for offer in self.db.get_offers_for_status() if offer[4] != "ended"]

        grouped_offers: dict[tuple[str, str], list[tuple[int, datetime, str]]] = {}

        for offer in offers:
            id, title, company, date, status = offer

            key = (title, company)
            grouped_offers.setdefault(key, []).append((id, datetime.strptime(date, "%Y-%m-%d"), status))

        today = datetime.today()

        for offers in grouped_offers.values():
            cycles = []
            current_cycle: list[tuple[int, datetime, str]] = []

            for offer in offers:
                if not current_cycle:
                    current_cycle.append(offer)
                    continue

                days = (offer[1] - current_cycle[-1][1]).days

                if days >= 30:
                    cycles.append(current_cycle)
                    current_cycle = [offer]
                else:
                    current_cycle.append(offer)

            if current_cycle:
                cycles.append(current_cycle)

            for cycle in cycles:
                if today - cycle[-1][1] >= timedelta(days=30):
                    self.db.update_offer_status(
                        [offer[0] for offer in cycle],
                        "ended",
                    )
