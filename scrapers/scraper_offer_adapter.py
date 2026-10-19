import re
from datetime import date
from typing import Any
from urllib.parse import urljoin

from playwright.sync_api import Locator

from offer import JobContract, JobOffer

ROCKETJOBS_CARD_SELECTOR = "a.offer-card"
ROCKETJOBS_TITLE_SELECTOR = "a.offer_list_offer_title_link"
ROCKETJOBS_LOCATION_SELECTOR = "button:has(svg.lucide-map-pin)"
ROCKETJOBS_LEVEL_PATTERN = re.compile(
    r"(?:junior|m\N{LATIN SMALL LETTER L WITH STROKE}odszy specjalista\s*/\s*junior|mid|specjalista\s*/\s*mid|"
    r"senior|starszy specjalista\s*/\s*senior|expert|ekspert\s*/\s*expert|manager)",
    re.IGNORECASE,
)
ROCKETJOBS_SALARY_RANGE_PATTERN = r"\d[\d\s\u00a0.,]*\s*(?:-|\u2013|\u2014)"
ROCKETJOBS_SALARY_VALUE_PATTERN = r"\d[\d\s\u00a0.,]*\s*(?:PLN|z\u0142|EUR|USD)\b"
ROCKETJOBS_WORK_MODES = {"zdalnie", "hybrydowo", "stacjonarnie", "mobilnie"}
ROCKETJOBS_CONTRACTS = {
    "b2b",
    "uop",
    "uz",
    "umowa o prac\u0119",
    "umowa zlecenie",
    "umowa o sta\u017c",
}
LINKEDIN_CARD_SELECTOR = '[componentkey^="job-card-component-ref-"]'
PRACUJ_CARD_SELECTOR = "div[data-test='default-offer']"

PRACUJ_SELECTORS = {
    "title": "[data-test='offer-title']",
    "company": "[data-test='link-company-profile']",
    "location": "[data-test='text-region']",
    "level": "[data-test='offer-additional-info-0']",
    "contract": "[data-test='offer-additional-info-2']",
    "work_mode": "[data-test='offer-additional-info-3']",
    "salary": "[data-test='offer-salary']",
    "url": "a[href*='/praca/']",
}


def _text(card: Locator, selector: str) -> str | None:
    element = card.locator(selector).first
    if not element.count():
        return None
    return element.inner_text(timeout=3000).strip() or None


def _location(card: Locator) -> str | None:
    for raw_text in card.locator(ROCKETJOBS_LOCATION_SELECTOR).all_inner_texts():
        text = raw_text.strip()
        if text.casefold() in {"poka\u017c profil firmy", "zobacz profil firmy"}:
            continue
        match = re.match(r"(.+?)(?:,\s*\+\d+)?(?:\s+Lokalizacje)?$", text)
        location = match.group(1).strip() if match else text
        if location:
            return location
    return None


def _level(spans: list[str]) -> str | None:
    return next(
        (text.strip() for text in spans if ROCKETJOBS_LEVEL_PATTERN.fullmatch(text.strip())),
        None,
    )


def _contract(spans: list[str]) -> str | None:
    for text in spans:
        parts = [part.strip().casefold() for part in text.split(",")]
        if parts and all(part in ROCKETJOBS_CONTRACTS for part in parts):
            return text.strip()
    return None


def _salary(card: Locator) -> str | None:
    spans = card.locator("span").all_inner_texts()
    for index, raw_text in enumerate(spans):
        text = raw_text.strip()
        if re.search(r"\d", text) and re.search(ROCKETJOBS_SALARY_RANGE_PATTERN, text):
            if index + 1 < len(spans):
                unit = spans[index + 1].strip()
                if re.search(r"PLN|z\u0142|EUR|USD", unit, re.IGNORECASE):
                    return f"{text} {unit}"
        if re.search(ROCKETJOBS_SALARY_VALUE_PATTERN, text, re.IGNORECASE):
            return text
    return None


# Source-specific card parsers return plain records validated by BaseScraper.
def rocketjobs_card_to_record(link: Locator, page_url: str) -> dict[str, Any] | None:
    card = link.locator("xpath=..")
    title = _text(card, ROCKETJOBS_TITLE_SELECTOR)
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
        "level": _level(spans),
        "contract": _contract(spans),
        "work_mode": next((text for text in paragraphs if text.strip().casefold() in ROCKETJOBS_WORK_MODES), None),
        "salary": _salary(card),
        "url": urljoin(page_url, offer_url),
    }


def pracuj_card_to_record(card: Locator) -> dict[str, Any]:
    offer_link = card.locator(PRACUJ_SELECTORS["url"]).first
    return {
        "title": _text(card, PRACUJ_SELECTORS["title"]),
        "company": _text(card, PRACUJ_SELECTORS["company"]),
        "location": _text(card, PRACUJ_SELECTORS["location"]),
        "level": _text(card, PRACUJ_SELECTORS["level"]),
        "contract": _text(card, PRACUJ_SELECTORS["contract"]),
        "work_mode": _text(card, PRACUJ_SELECTORS["work_mode"]),
        "salary": _text(card, PRACUJ_SELECTORS["salary"]),
        "url": offer_link.get_attribute("href", timeout=3000) if offer_link.count() else None,
    }


def linkedin_card_to_record(card: Locator) -> dict[str, Any]:
    component_key = card.get_attribute("componentkey")
    offer_id = component_key.removeprefix("job-card-component-ref-") if component_key else None
    paragraphs = card.locator("p")
    paragraph_count = paragraphs.count()
    company = paragraphs.nth(1).inner_text().strip() if paragraph_count > 1 else None
    location_text = paragraphs.nth(2).inner_text().strip() if paragraph_count > 2 else None

    work_mode = None
    location = location_text
    if location_text:
        for mode in ("Praca stacjonarna", "Praca hybrydowa", "Praca zdalna"):
            if mode in location_text:
                work_mode = mode
                location = location_text.replace(f" ({mode})", "").strip()
                break

    return {
        "title": _text(card, "p span[aria-hidden='true']"),
        "company": company,
        "location": location,
        "work_mode": work_mode,
        "url": f"https://www.linkedin.com/jobs/view/{offer_id}" if offer_id else None,
        "offer_id": offer_id,
    }


def pracuj_offer_id_from_url(url: str | None) -> str | None:
    if not url:
        return None
    match = re.search(r",oferta,(\d+)", url)
    return match.group(1) if match else None


# Shared conversions used after source-specific scraping.
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
    elif contract_text.strip() == "b2b" or "kontrakt b2b" in contract_text:
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
