# Library
import asyncio
import email
import email.utils
import imaplib
import logging
import os
import sqlite3
from datetime import datetime
from email.message import Message
from imaplib import IMAP4_SSL
from pathlib import Path
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel

# Load environment variables
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("parser")


class JobOffer(BaseModel):
    date: datetime
    title: str
    company: str
    location: str
    salary: Optional[float] = None


class OffersResponse(BaseModel):
    offers: List[JobOffer]


# Login to wp.pl and fetch unseen messages
def login() -> tuple[imaplib.IMAP4_SSL, list[bytes]]:
    mail = imaplib.IMAP4_SSL("imap.wp.pl", 993)
    login_email = os.getenv("EMAIL", "").strip().replace(",", "")
    my_password = os.getenv("PASSWORD", "").strip().replace(",", "")
    logger.info(f"Logging in: {bool(login_email)}")
    logger.info(f"Password loaded: {bool(my_password)}")

    mail.login(login_email, my_password)
    mail.select("Link")
    status, response = mail.search(None, "UNSEEN")
    mail_ids = response[0].split()
    return mail, mail_ids


# Cache file to store processed mail IDs
cache_file = Path("mail_records/processed_linkedin_mails.txt")


# Function to extract HTML content from an email message
def get_html(msg: Message) -> Optional[str]:
    if msg is None:
        return None

    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True)
                if isinstance(payload, bytes):
                    return payload.decode("utf-8", errors="ignore")
    elif msg.get_content_type() == "text/html":
        payload = msg.get_payload(decode=True)
        if isinstance(payload, bytes):
            return payload.decode("utf-8", errors="ignore")
    return None


def is_valid_offer(offer: JobOffer) -> bool:
    pos = offer.title.strip()
    comp = offer.company.strip()

    if len(pos) < 3 or len(comp) < 2 or pos.lower() == "null" or comp.lower() == "null":
        return False

    # Rubbish
    bad_markers = ["zobacz", "rekrutuje", "więcej", "wszystkie", "ofert"]
    if any(marker in pos.lower() for marker in bad_markers):
        return False
    return True


# Load API
client = genai.Client(api_key=os.getenv("KEY_API", "").strip().replace(",", ""))


# Function to parse job offers from text using the API
async def parser_offers_API(text: str) -> List[JobOffer]:
    prompt = f'Extract all job offers from this text mail:\n"{text}"'

    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="models/gemini-3.1-flash-lite",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": OffersResponse.model_json_schema(),
                "temperature": 0.0,
            },
        )
        if not response.parsed:
            return []
        try:
            parsed_response = OffersResponse.model_validate(response.parsed)
            return parsed_response.offers
        except Exception as parse_error:
            logger.error("Failed to validate parsed API response: %s", parse_error, exc_info=True)
            return []
    except Exception as e:
        logger.error(f"Error occurred while parsing offers: {e}", exc_info=True)
        return []


# Process each block of text to extract job offers and validate them
async def process_linkedin_block(text: str, current_date: datetime, data: List[dict[str, Any]]) -> None:
    # text is already plain text (we cleaned it in main)
    offers: List[JobOffer] = await parser_offers_API(text)

    count = 0
    # Iterate once over each offer
    for offer in offers:
        is_valid = is_valid_offer(offer)
        # JobOffer is a Pydantic model, access attributes directly. Use title for job detection.
        is_job = looks_like_job(getattr(offer, "title", ""))

        if is_valid and is_job:
            # Add the offer
            data.append(
                {
                    "date": current_date.strftime("%Y-%m-%d"),
                    "title": offer.title,
                    "company": offer.company,
                    "location": offer.location,
                    "salary": offer.salary,
                }
            )
            count += 1

        else:
            print(f" [Reject] {offer.title} | Valid: {is_valid} | Job: {is_job}")
    # Print the number of valid offers retrieved
    print(f" [SUCCESS] {count} valid offers retrieved.")


# Define functions to analyze job offers and companies
bad_titles = [
    "Zobacz oferty",
    "absolwentów uczelni",
    "absolwent uczelni",
    "aktywnie rekrutuje",
    "zobacz oferty",
    "zobacz więcej",
    "zobacz wszystkie",
]

skip = [
    "zobacz oferty",
    "absolwentów uczelni",
    "absolwent uczelni",
    "aktywnie rekrutuje",
    "zobacz więcej",
    "zobacz wszystkie",
    "właścicielem marki",
]


# Define functions to analyze job offers and companies
def looks_like_job(title: Optional[str]) -> bool:
    if not title or not isinstance(title, str):
        return False

    clean_title = title.lower()

    junk_phrases: list[str] = [
        "aktywnie rekrutuje",
        "bądź pierwszym",
        "spośród",
        "kandydatów",
        "1 kontakt",
        "absolwentów uczelni",
        "absolwent uczelni",
        "zobacz oferty",
    ]

    for junk in junk_phrases:
        clean_title = clean_title.replace(junk.lower(), "")

    words = {
        "analityk",
        "analityczka",
        "analiz",
        "data",
        "bi",
        "business intelligence",
        "raport",
        "raportowanie",
        "danych",
        "science",
        "sql",
        "dwh",
        "etl",
        "power bi",
        "dashboard",
        "wizualizacja",
        "biznesowy",
        "business",
        "finans",
        "finance",
        "controlling",
        "kontroler",
        "ksiegow",
        "accounting",
        "audyt",
        "audit",
        "compliance",
        "ryzyko",
        "kredyt",
        "planowanie",
        "planowania",
        "zakup",
        "sourcing",
        "procurement",
        "it",
        "developer",
        "administrator",
        "support",
        "helpdesk",
        "systemow",
        "siec",
        "cyber",
        "security",
        "crm",
        "sap",
        "erp",
        "webcon",
        "logist",
        "spedyt",
        "transport",
        "magazyn",
        "supply",
        "chain",
        "operac",
        "dystrybucja",
        "produkcja",
        "realizacji",
        "zamówień",
        "konsultant",
        "rpa",
        "automatyz",
        "specjalista",
        "rozliczeń",
        "staż",
        "praktyk",
        "controller",
        "asystent",
        "biurow",
        "administrac",
        "hr",
        "kadr",
        "plac",
        "office",
        "rekrut",
    }
    is_match = any(w in clean_title for w in words)

    exclude = [
        "sp. z o.o",
        "s.a.",
        "sa ",
        " sp. z",
    ]

    is_excluded = any(e in clean_title for e in exclude)

    # Logic: must match words AND must not match exclusions
    if is_match and not is_excluded:
        return True
    print(f" [DEBUG] Rejected: '{title}' | Match: {is_match} | Excluded: {is_excluded}")
    return False


# Entry point: Initialize the asyncio event loop and execute the main processing function
async def run_parser(mail: Any, mail_ids: list[str]) -> int:
    cache_file = Path("mail_records/processed_linkedin_mails.txt")
    if not mail_ids:
        logger.info("None new offers found.")
    else:
        logger.info(f"Found {len(mail_ids)} new emails.")

    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            processed_ids = {line.strip() for line in f}
    else:
        processed_ids = set()

    clean_jobs: List[Dict[str, Any]] = []
    result = await main(mail, mail_ids, clean_jobs, processed_ids)
    return result


# Main Loop
async def main(mail: IMAP4_SSL, mail_ids: List[Any], clean_jobs: List[Dict[str, Any]], processed_ids: set[str]) -> int:
    total_added = 0

    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            processed_ids.update(line.strip() for line in f)
    for i in mail_ids:
        mail_id_str = i.decode() if isinstance(i, bytes) else str(i)
        if mail_id_str in processed_ids:
            continue

        status, msg_data = mail.fetch(i, "(RFC822)")
        if status != "OK":
            continue

        if msg_data and isinstance(msg_data[0], tuple):
            raw_email = msg_data[0][1]
            if isinstance(raw_email, bytes):
                msg = email.message_from_bytes(raw_email)
            else:
                continue
        else:
            continue

        date_header = msg.get("Date")
        current_date = email.utils.parsedate_to_datetime(date_header) if date_header else datetime.now()

        html = get_html(msg)
        if not html:
            with open(cache_file, "a") as f:
                f.write(mail_id_str + "\n")
            processed_ids.add(mail_id_str)
            continue

        text = BeautifulSoup(html, "html.parser").get_text("\n")

        await process_linkedin_block(text, current_date, clean_jobs)
        await asyncio.sleep(55)
        for job in clean_jobs:
            save_offers(
                title=job.get("title", "N/A"),
                company=job.get("company", "N/A"),
                location=job.get("location", "N/A"),
                salary=job.get("salary", "N/A"),
                date=job.get("date", "N/A"),
                source="Linkedin",
            )
            total_added += 1

        clean_jobs.clear()

        with open(cache_file, "a") as f:
            f.write(mail_id_str + "\n")
        processed_ids.add(mail_id_str)
        await asyncio.sleep(35)
        print(f"Processed mail: {mail_id_str}, wait 35 seconds...")

    return total_added


# Add new jobs offers to database file
def save_offers(title: str, company: str, location: str, salary: str, date: str, source: str, db_name="new_offers.db"):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute(
        """
            INSERT INTO Offers (title, company, location, salary, date, source)
                   VALUES (?, ?, ?, ?, ?, ?)
        """,
        (title, company, location, salary, date, source),
    )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    mail, mail_ids = login()
    mail_ids_str: List[str] = [m.decode("utf-8") if isinstance(m, bytes) else str(m) for m in mail_ids]
    total_found = asyncio.run(run_parser(mail, mail_ids_str))

    logger.info("\nFinished!")
    logger.info(f"MAILS processed: {len(mail_ids_str)}")
    logger.info(f"TOTAL JOBS found: {total_found}")
