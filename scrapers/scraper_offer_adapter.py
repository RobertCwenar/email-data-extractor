import re
from datetime import date
from typing import Any
from urllib.parse import urljoin

from playwright.sync_api import Locator

from offer import JobContract, JobOffer

CARD_SELECTOR = "a.offer-card"
TITLE_SELECTOR = "a.offer_list_offer_title_link"
LOCATION_SELECTOR = "button:has(svg.lucide-map-pin)"
LEVEL_PATTERN = r"\b(?:Junior|Mid|Senior|Expert|Manager)\b"
CONTRACT_PATTERN = r"\b(?:UoP|B2B|UZ)\b|umowa o prac\u0119|umowa zlecenie"
SALARY_RANGE_PATTERN = r"\d[\d\s\u00a0.,]*\s*(?:-|\u2013|\u2014)"
SALARY_VALUE_PATTERN = r"\d[\d\s\u00a0.,]*\s*(?:PLN|z\u0142|EUR|USD)\b"
WORK_MODES = {"zdalnie", "hybrydowo", "stacjonarnie", "mobilnie"}


def _text(card: Locator, selector: str) -> str | None:
    element = card.locator(selector).first
    if not element.count():
        return None
    return element.inner_text(timeout=3000).strip() or None


def _location(card: Locator) -> str | None:
    element = card.locator(LOCATION_SELECTOR).first
    if not element.count():
        return None
    text = element.inner_text().strip()
    match = re.match(r"(.+?)(?:,\s*\+\d+)?(?:\s+Lokalizacje)?$", text)
    return match.group(1).strip() if match else text


def _salary(card: Locator) -> str | None:
    spans = card.locator("span").all_inner_texts()
    for index, raw_text in enumerate(spans):
        text = raw_text.strip()
        if re.search(r"\d", text) and re.search(SALARY_RANGE_PATTERN, text):
            if index + 1 < len(spans):
                unit = spans[index + 1].strip()
                if re.search(r"PLN|z\u0142|EUR|USD", unit, re.IGNORECASE):
                    return f"{text} {unit}"
        if re.search(SALARY_VALUE_PATTERN, text, re.IGNORECASE):
            return text
    return None


def rocketjobs_card_to_offer(link: Locator, page_url: str) -> dict[str, Any] | None:
    card = link.locator("xpath=..")
    title = _text(card, TITLE_SELECTOR)
    if not title:
        title = re.sub(r"^Zobacz ofert\u0119\s*", "", link.get_attribute("title") or "", flags=re.IGNORECASE).strip()

    image = card.locator("img[alt]").first
    company = image.get_attribute("alt") if image.count() else None
    company = re.sub(r"^Image:\s*", "", company or "", flags=re.IGNORECASE).strip()
    offer_url = link.get_attribute("href")
    if not title or not company or not offer_url or re.search(r"logo|rocketjobs", company, re.IGNORECASE):
        return None

    spans = card.locator("span").all_inner_texts()
    paragraphs = card.locator("p").all_inner_texts()
    return {
        "title": title,
        "company": company,
        "location": _location(card) or "Nie podano",
        "level": next((text for text in spans if re.search(LEVEL_PATTERN, text.strip(), re.IGNORECASE)), None),
        "contract": next((text for text in spans if re.search(CONTRACT_PATTERN, text, re.IGNORECASE)), None),
        "work_mode": next((text for text in paragraphs if text.strip().casefold() in WORK_MODES), None),
        "salary": _salary(card),
        "url": urljoin(page_url, offer_url),
    }


def scraper_record_to_offer(record: dict[str, Any]) -> JobOffer:
    scraped_at = record.get("scraped_at")
    try:
        offer_date = date.fromisoformat(scraped_at) if isinstance(scraped_at, str) else date.today()
    except ValueError:
        offer_date = date.today()

    return JobOffer(
        title=str(record.get("title") or "").strip(),
        company=str(record.get("company") or "").strip(),
        location=str(record.get("location") or "Nie podano").strip(),
        date=offer_date.isoformat(),
    )


def scraper_record_to_contract(record: dict[str, Any]) -> JobContract:
    salary_text = str(record.get("salary") or "").replace("\u00a0", " ").strip()
    salary_text = salary_text.replace("\u00e2\u20ac\u201c", "\u2013").replace("z\u0139\u201a", "z\u0142")
    contract_text = str(record.get("contract") or "").casefold().replace("prac\u00c4\u2122", "prac\u0119")

    contract_type = None
    if "umowa o prac\u0119" in contract_text or "permanent" in contract_text:
        contract_type = "UoP"
    elif "kontrakt b2b" in contract_text:
        contract_type = "B2B"
    elif "umowa zlecenie" in contract_text:
        contract_type = "UZ"

    contract = JobContract(contract_type=contract_type)
    if not salary_text:
        return contract

    normalized = salary_text.casefold().replace("zale\u0139\u013dnie", "zale\u017cnie")
    normalized = normalized.replace("miesi\u00c4\u2026c", "miesi\u0105c")
    if "zale\u017cnie od umowy" in normalized or "zal. od umowy" in normalized:
        return contract

    if "netto" in normalized and "vat" in normalized:
        contract.contract_type = "B2B"
    elif "brutto" in normalized and contract.contract_type is None:
        contract.contract_type = "UoP"

    if "/ godz." in normalized or "/ godzin" in normalized or "/ hour" in normalized:
        contract.salary_period = "hourly"
    elif "/ mies." in normalized or "/ miesi\u0105c" in normalized:
        contract.salary_period = "monthly"
    else:
        return contract

    match = re.search(
        r"(\d[\d \u00a0]*)\s*[-\u2013\u2014]\s*(\d[\d \u00a0]*)\s*(?:z\u0142|PLN)",
        salary_text,
    )
    if not match:
        return contract

    salary_min = float(match.group(1).replace(" ", "").replace("\u00a0", ""))
    salary_max = float(match.group(2).replace(" ", "").replace("\u00a0", ""))
    if salary_min > salary_max:
        return contract

    contract.salary_currency = "PLN"
    contract.salary_min_offer = salary_min
    contract.salary_max_offer = salary_max
    return contract
