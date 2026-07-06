# Library
import asyncio
import email
import email.utils
import imaplib
import json
import os
import sqlite3
from datetime import datetime
from email.message import Message
from imaplib import IMAP4_SSL
from pathlib import Path
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# Login to wp.pl and fetch unseen messages
def login() -> tuple[imaplib.IMAP4_SSL, list[bytes]]:
    mail = imaplib.IMAP4_SSL("imap.wp.pl", 993)
    login_email = os.getenv("EMAIL", "").strip().replace(",", "")
    my_password = os.getenv("PASSWORD", "").strip().replace(",", "")
    print("Logging in:", bool(login_email))
    print("Password loaded:", bool(my_password))

    mail.login(login_email, my_password)
    mail.select("RocketJobs")  # Select the mailbox
    status, response = mail.search(None, "UNSEEN")
    mail_ids = response[0].split()
    return mail, mail_ids


# Cache file to store processed mail IDs
cache_file = Path("mail_records/processed_rocketjobs_mails.txt")


# Define a function to extract HTML content from an email message
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


def is_valid_offer(offer: Dict[str, Any]) -> bool:
    pos = offer.get("position", "").strip()
    comp = offer.get("company", "").strip()

    if len(pos) < 3 or len(comp) < 2 or pos.lower() == "null" or comp.lower() == "null":
        return False

    # Rubbish
    bad_markers = ["zobacz", "rekrutuje", "więcej", "wszystkie", "ofert"]
    if any(marker in pos.lower() for marker in bad_markers):
        return False
    return True


# Load API
api_key = os.getenv("KEY_API")
if api_key:
    key_api = api_key.strip().replace(",", "")
    genai.configure(api_key=key_api)
else:
    print("None")


async def parser_offers_API(text: str) -> List[Dict[str, Any]]:
    model = genai.GenerativeModel("models/gemini-3.5-flash")

    # A very simple prompt to exclude interpretation errors
    prompt = (
        "Jesteś ekstraktorem ofert pracy. Z poniższego tekstu wyciągnij wszystkie oferty.\n"
        "Zwróć wynik TYLKO jako czystą tablicę JSON: "
        '[{"position": "nazwa stanowiska", '
        '"company": "nazwa firmy", '
        '"location": "miasto", '
        '"salary": "kwota wynagrodzenia jeżeli nie ma to nie wpisuj niczego"}]\n'
        "Jeśli nie ma żadnej oferty, zwróć: []\n"
        "Nie dodawaj żadnych wyjaśnień, wstępów, ani znaków Markdown typu ```json.\n"
        f"TEKST MAIL:\n{text}"
    )
    try:
        response = await model.generate_content_async(prompt)

        raw_output = response.text
        print(f"DEBUG: Raw AI response: {raw_output[:500]}")

        # Parser
        clean_json = raw_output.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)

    except Exception as e:
        print(f"Parser Error: {e}")
        return []


def clean_block(block: Optional[str]) -> List[str]:
    if block is None:
        return []

    lines = block.splitlines()
    cleaned: List[str] = []

    for line in lines:
        lower_line = line.lower()

        if lower_line in ["!", "nowość!", "nowość", "hit!", "śpiesz się!"]:
            continue

        if "z " in lower_line and "." in lower_line:
            continue

        cleaned.append(line)

    return cleaned


skip = skip = [
    "logo",
    "więcej",
    "ciepłe",
    "najlepiej dopasowana",
    "nowość",
    "hit",
    "śpiesz się",
    "krajowego rejestru",
    "krs",
    "nip",
    "regon",
    "kapitału zakładowego",
    "wpłacony w całości",
    "ul. prosta",
    "wyprzedź innych kandydatów",
    "Zobacz oferty, które mogły Ci umknąć",
    "bądź na bieżąco z nowymi ofertami pracy",
    "zobacz wszystkie oferty pracy",
    "zobacz wszystkie oferty",
    "zobacz więcej ofert",
    "zobacz więcej",
    "zobacz inne oferty",
    "zobacz inne",
    "zobacz podobne oferty",
    "zobacz podobne",
    "sprawdź inne oferty",
    "sprawdź inne",
    "sprawdź podobne oferty",
    "sprawdź podobne",
    "mamy dla ciebie nowe oferty pracy",
    "mamy dla ciebie nowe oferty",
    "twoje preferencje",
    "Mamy dla Ciebie nowe oferty. "
    "Twoje preferencje: Logistyka, Wrocław, 30 km, "
    "Specjalista / Mid, Młodszy specjalista / Junior",
]

bad_titles = [
    "najlepiej dopasowana",
    "nowość",
    "hit",
]


async def process_rocket_block(text: str, current_date: datetime, data: List[dict[str, Any]]) -> None:
    # text is already plain text (we cleaned it in main)
    offers: List[Dict[str, Any]] = await parser_offers_API(text)

    count = 0
    # Iterate once over each offer
    for offer in offers:
        is_valid = is_valid_offer(offer)
        position_title = str(offer.get("position", ""))
        is_job = looks_like_job(position_title)

        if is_valid and is_job:
            # Add the offer
            data.append(
                {
                    "date": current_date.strftime("%Y-%m-%d"),
                    "title": offer.get("position", "N/A"),
                    "company": str(offer.get("company", "N/A")),
                    "location": str(offer.get("location", "N/A")),
                    "salary": str(offer.get("salary", "N/A")),
                }
            )
            count += 1
        else:
            print(f" [Reject] {offer.get('position')} | Valid: {is_valid} | Job: {is_job}")

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


def looks_like_job(title: Optional[str]) -> bool:
    if not title or not isinstance(title, str):
        return False

    title = title.lower()

    keywords = [
        "analityk",
        "analyst",
        "specjalista",
        "developer",
        "konsultant",
        "księgowy",
        "staż",
        "młodszy",
        "data",
        "it",
        "danych",
        "business",
        "controlling",
        "finanse",
        "finance",
        "planowania",
        "planowanie",
        "kontroler",
        "kontroler finansowy",
        "raportowanie",
        "raporty",
        "raportowania",
        "archiwum",
        "biurowy",
        "fakturowania",
        "spedytor",
        "menedżer",
        "logist",
        "supply",
        "analityk",
        "analyst",
        "specjalista",
        "specjalistka",
        "developer",
        "konsultant",
        "księgowy",
        "staż",
        "młodszy",
        "data",
        "it",
        "danych",
        "business",
        "controlling",
        "finanse",
        "finance",
        "planowania",
        "planowanie",
        "kontroler",
        "raportowanie",
        "raporty",
        "raportowania",
        "biurowy",
        "fakturowania",
        "spedytor",
        "menedżer",
        "logist",
        "supply",
        "koordynator",
        "asystent",
        "asystentka",
        "project manager",
        "financial",
        "junior",
    ]
    exclude = ["sp. z o.o", "s.a.", "sa ", " sp. z", "bank", "polska"]

    if any(k in title for k in keywords):
        if not any(e in title for e in exclude):
            return True
    return False


def is_job_trigger(line: Optional[str]) -> bool:
    lowercased_line = (line or "").lower()
    keywords = [
        "analyst",
        "analityk",
        "asystent",
        "asystentka",
        "biurowy",
        "business",
        "controlling",
        "coordinator",
        "data",
        "danych",
        "developer",
        "engineer",
        "fakturowania",
        "finance",
        "finanse",
        "finansowy",
        "intern",
        "it",
        "junior",
        "konsultant",
        "kontroler",
        "księgowy",
        "logist",
        "menedżer",
        "młodszy",
        "planowanie",
        "planowania",
        "project manager",
        "raportowanie",
        "raportowania",
        "raporty",
        "specjalista",
        "specjalistka",
        "spedytor",
        "staż",
        "supply",
        "analizy",
        "analytics",
        "engineer",
        "SAP",
    ]

    return any(k in lowercased_line.lower() for k in keywords)


def is_valid_job(job: Dict[str, Any]) -> bool:
    title = job["title"].lower()

    if any(b in title for b in bad_titles):
        return False

    # It should be like a job title, not just a single word
    if len(title.split()) < 2:
        return False

    # Company not offering jobs
    if "sp. z o.o" in title.lower():
        return False

    return True


# Entry point: Initialize the asyncio event loop and execute the main processing function
async def run_parser(mail: Any, mail_ids: list[str]) -> int:
    cache_file = Path("mail_records/processed_rocketjobs_mails.txt")
    if not mail_ids:
        print("None new offers found.")
    else:
        print(f"Found {len(mail_ids)} new emails.")

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

        await process_rocket_block(text, current_date, clean_jobs)
        await asyncio.sleep(55)
        for job in clean_jobs:
            save_offers(
                title=job.get("title", "N/A"),
                company=job.get("company", "N/A"),
                location=job.get("location", "N/A"),
                salary=job.get("salary", "N/A"),
                date=job.get("date", "N/A"),
                source="RocketJobs",
            )
            total_added += 1

        clean_jobs.clear()

        with open(cache_file, "a") as f:
            f.write(mail_id_str + "\n")
        processed_ids.add(mail_id_str)
        await asyncio.sleep(35)
        print(f"Processed mail: {mail_id_str}, wait 35 seconds...")

    return total_added


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

    print("\nFinished!")
    print("MAILS processed:", len(mail_ids_str))
    print("TOTAL JOBS found:", total_found)
