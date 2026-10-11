import re
from datetime import date
from typing import Any

from offer import JobContract, JobOffer


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


def scraper_record_to_contract(record: dict[str, Any]) -> JobContract:
    salary_text = str(record.get("salary") or "").replace("\u00a0", " ").strip()
    contract_text = str(record.get("contract") or "").casefold()

    contract_type = None

    if "umowa o pracę" in contract_text or "permanent" in contract_text:
        contract_type = "UoP"
    elif "kontrakt b2b" in contract_text:
        contract_type = "B2B"
    elif "umowa zlecenie" in contract_text:
        contract_type = "UZ"

    contract = JobContract(contract_type=contract_type)

    if not salary_text:
        return contract

    normalized = salary_text.casefold()

    if "zależnie od umowy" in normalized or "zal. od umowy" in normalized:
        return contract

    if "netto" in normalized and "vat" in normalized:
        contract.contract_type = "B2B"
    elif "brutto" in normalized and contract.contract_type is None:
        contract.contract_type = "UoP"

    if "/ godz." in normalized or "/ godzin" in normalized:
        contract.salary_period = "hourly"
    elif "/ mies." in normalized or "/ miesiąc" in normalized:
        contract.salary_period = "monthly"
    else:
        return contract

    match = re.search(
        r"(\d[\d ]*)\s*[–-]\s*(\d[\d ]*)\s*zł",
        salary_text,
    )

    if not match:
        return contract

    salary_min = float(match.group(1).replace(" ", ""))
    salary_max = float(match.group(2).replace(" ", ""))

    if salary_min > salary_max:
        return contract

    contract.salary_currency = "PLN"
    contract.salary_min_offer = salary_min
    contract.salary_max_offer = salary_max

    return contract
