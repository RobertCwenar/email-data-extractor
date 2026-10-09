from datetime import date
from typing import Any

from offer import JobOffer


def scraper_record_to_offer(record: dict[str, Any]) -> tuple[JobOffer, str, None]:
    offer = JobOffer(
        title=str(record.get("title") or "").strip(),
        company=str(record.get("company") or "").strip(),
        location=str(record.get("location") or "Nie podano").strip(),
        date=date.today().isoformat(),
    )
    offer_text = "\n".join(
        str(record[field]).strip()
        for field in ("title", "company", "salary", "contract", "level", "work_mode")
        if record.get(field)
    )
    return offer, offer_text, None
