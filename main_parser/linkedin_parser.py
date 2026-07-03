# Library
import asyncio
import imaplib
import json
from bs4 import BeautifulSoup
from email import message_from_bytes
from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv
import email.utils
import google.generativeai as genai
import sqlite3
from email.message import Message
from datetime import datetime
from imaplib import IMAP4_SSL
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

# Login to wp.pl and fetch unseen messages
def login() -> tuple[imaplib.IMAP4_SSL, list[bytes]]:
    mail = imaplib.IMAP4_SSL("imap.wp.pl", 993)
    login_email = os.getenv("EMAIL", "").strip().replace(",", "")
    my_password = os.getenv("PASSWORD", "").strip().replace(",", "")
    print("Logging in:", bool(login_email))
    print("Password loaded:", bool(my_password))
    
    mail.login(login_email, my_password)
    mail.select("Link") 
    status, response = mail.search(None, 'UNSEEN')
    mail_ids = response[0].split()
    return mail, mail_ids

mail, mail_ids = login()

# Cache file to store processed mail IDs
cache_file = Path("mail_records/processed_linkedin_mails.txt")
clean_jobs: List[Dict[str, Any]] = []
processed_ids: set[str] = set()

def get_html(msg: Message) -> Optional[str]:
    if msg is None:
        return None
    
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True)
                if isinstance(payload, bytes):
                    return payload.decode('utf-8', errors='ignore')
    elif msg.get_content_type() =="text/html":
        payload = msg.get_payload(decode=True)
        if isinstance(payload, bytes):
            return payload.decode('utf-8', errors='ignore')
    return None

def is_valid_offer(offer: Dict [str, Any]) -> bool:
    pos = offer.get('position', '').strip()
    comp = offer.get('company', '').strip()

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
    key_api= api_key.strip().replace(",", "")
    genai.configure(api_key=key_api)
else:
    print("None")

async def parse_all_offers_from_mail(text):
    model = genai.GenerativeModel('models/gemini-3.1-flash-lite')
    
    prompt = (
            "Jesteś ekstraktorem ofert pracy. Z poniższego tekstu wyciągnij wszystkie oferty.\n"
            "Zwróć wynik TYLKO jako czystą tablicę JSON: "
            "[{\"position\": \"nazwa stanowiska\", \"company\": \"nazwa firmy\", \"location\": \"miasto\", \"salary\": \"kwota wynagrodzenia jeżeli nie ma to nie wpisuj niczego'\"}]\n\n"
            "Jeśli nie ma żadnej oferty, zwróć: []\n"
            "Nie dodawaj żadnych wyjaśnień, wstępów, ani znaków Markdown typu ```json.\n"
            f"TEKST MAIL:\n{text}"
        )
    
    response = model.generate_content(prompt)

    # Clean response
    cleaned = response.text.replace('```json', '').replace('```', '').strip()
    try:
        # Parse the response as a list
        return json.loads(cleaned)
    except Exception as e:
        print(f"JSON parsing error: {e}")
        return []

async def process_linkedin_block(text: str, current_date: datetime, data: List[dict[str, Any]]) -> None:
    # text is already plain text (we cleaned it in main)
    offers: List[Dict[str, Any]] = await parse_all_offers_from_mail(text)
    
    count = 0
    # Iterate once over each offer
    for offer in offers:
        is_valid = is_valid_offer(offer)
        is_job = looks_like_job(offer.get('position', ''))
        
        if is_valid and is_job:
            # Add the offer
            data.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "title": offer.get('position', 'N/A'),
                "company": offer.get('company', 'N/A'),
                "location": offer.get('location', 'N/A'),
                "salary": offer.get('salary', 'N/A')
            })
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
        "zobacz wszystkie"
    ]

skip = [
    "zobacz oferty",
    "absolwentów uczelni",
    "absolwent uczelni",
    "aktywnie rekrutuje",
    "zobacz więcej",
    "zobacz wszystkie",
    "właścicielem marki"
]

# Define functions to analyze job offers and companies
def looks_like_job(title: Optional[str]) -> bool:
    if not title or not isinstance(title, str):
        return False
    
    clean_title = title.lower()

    junk_phrases: list[str] = [
        "aktywnie rekrutuje", "bądź pierwszym", "spośród", "kandydatów", 
        "1 kontakt", "absolwentów uczelni", "absolwent uczelni", "zobacz oferty", 
    ]
    
    for junk in junk_phrases:
        clean_title = clean_title.replace(junk.lower(), "")

    words = {
    "analityk", "analityczka", "analiz", "data", "bi", "business intelligence", 
    "raport", "raportowanie", "danych", "science", "sql", "dwh", "etl", 
    "power bi", "dashboard", "wizualizacja", "biznesowy", "business", 
    "finans", "finance", "controlling", "kontroler", "ksiegow", "accounting", 
    "audyt", "audit", "compliance", "ryzyko", "kredyt", "planowanie", 
    "planowania", "zakup", "sourcing", "procurement", "it", "developer", 
    "administrator", "support", "helpdesk", "systemow", "siec", "cyber", 
    "security", "crm", "sap", "erp", "webcon", "logist", "spedyt", "transport", 
    "magazyn", "supply", "chain", "operac", "dystrybucja", "produkcja", 
    "realizacji", "zamówień", "konsultant", "rpa", "automatyz", "specjalista", 
    "rozliczeń", "staż", "praktyk", "controller", "asystent", "biurow", 
    "administrac", "hr", "kadr", "plac", "office", "rekrut"
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

if not mail_ids:
        print("None new offers found.")
else:
        print(f"Found {len(mail_ids)} new emails.")

if os.path.exists(cache_file):
    with open(cache_file, "r") as f:
        processed_ids = {line.strip() for line in f}
else:
    processed_ids = set()

# Main Loop
async def main(mail: IMAP4_SSL, mail_ids: List[Any], clean_jobs: List[Dict[str, Any]]) -> int:
    total_added = 0
  
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            processed_ids.update(line.strip() for line in f)
    for i in mail_ids:
        mail_id_str = i.decode() if isinstance(i, bytes) else str(i)
        if mail_id_str in processed_ids:
            continue

        status, msg_data = mail.fetch(i, "(RFC822)")
        if status != 'OK': continue
        
        if msg_data and isinstance(msg_data[0], tuple):
            raw_email = msg_data[0][1]
            if isinstance(raw_email, bytes):
                msg = email.message_from_bytes(raw_email)
            else:
                continue 
        else:
            continue

        date_header = msg.get("Date")
        current_date = (email.utils.parsedate_to_datetime(date_header) if date_header else datetime.now())
        
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
                title=job.get('title', 'N/A'),
                company=job.get('company', 'N/A'),
                location=job.get('location', 'N/A'),
                salary=job.get('salary', 'N/A'),
                date=job.get('date', 'N/A'),
                source='Linkedin'
            )
            total_added += 1
      
        clean_jobs.clear()
      
        with open(cache_file, "a") as f:
            f.write(mail_id_str + "\n")
        processed_ids.add(mail_id_str)
        print(f"Processed mail: {mail_id_str}, wait 25 seconds...")
        await asyncio.sleep(45)       
        
    return total_added

# Add new jobs offers to database file
def save_offers(title: str, company: str, location: str, salary: str, date: str, source: str, db_name='new_offers.db'):
    conn = sqlite3.connect(db_name)
    cursor =conn.cursor()
    cursor.execute('''
            INSERT INTO Offers (title, company, location, salary, date, source)
                   VALUES (?, ?, ?, ?, ?, ?)
        ''', (title, company, location, salary, date, source))

    conn.commit()
    conn.close()

# Entry point: Initialize the asyncio event loop and execute the main processing function
async def run_parser(mail: Any, mail_ids: list[str]) -> int:
    clean_jobs: List[Dict[str, Any]] = []
    result = await main(mail, mail_ids, clean_jobs)
    return result

if __name__ == "__main__":
    mail_ids_str: List[str] = [m.decode('utf-8') if isinstance(m, bytes) else str(m) for m in mail_ids]
    total_found = asyncio.run(run_parser(mail, mail_ids_str))

    print("\nFinished!")
    print("MAILS processed:", len(mail_ids_str))
    print("TOTAL JOBS found:", total_found)