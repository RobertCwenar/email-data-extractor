# Library
import asyncio
import imaplib
from bs4 import BeautifulSoup
from email import message_from_bytes
import email
import pandas as pd
import os
from dotenv import load_dotenv
import re
import email.utils
import google.generativeai as genai
import json
import sqlite3
from datetime import datetime 

# Load environment variables
load_dotenv()

# Login to wp.pl
mail = imaplib.IMAP4_SSL("imap.wp.pl", 993)
login_email = os.getenv("EMAIL").strip().replace(",", "")
my_password = os.getenv("PASSWORD").strip().replace(",", "")
print("Logging in:", bool(login_email))
print("Password loaded:", bool(my_password))

mail.login(login_email, my_password)
mail.select("PRACA") 
status, messages = mail.search(None, "UNSEEN")
mail_ids = messages[0].split()
print("Number of emails:", len(mail_ids))

# Load data
cache_file = "processed_mails.txt"
jobs = []

status, response = mail.search(None, 'ALL')
mail_ids = response[0].split()

clean_jobs= []
def get_html(msg: str) -> str:
    if msg is None:
        return None
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                return part.get_payload(decode=True).decode(errors="ignore")
    else:
        if msg.get_content_type() == "text/html":
            return msg.get_payload(decode=True).decode(errors="ignore")
    return None

def is_valid_offer(offer: str) -> str:
    pos = offer.get('position', '').strip()
    comp = offer.get('company', '').strip()

    if len(pos) < 3 or len(comp) < 2 or pos.lower() == "null" or comp.lower() == "null":
        return False
    
    # Rubbish
    bad_markers = ["zobacz", "rekrutuje", "więcej", "wszystkie", "ofert"]
    if any(marker in pos.lower() for marker in bad_markers):
        return False
    return True

#Load APi
api_key = os.getenv("KEY_API")
if api_key:
    key_api = api_key.strip().replace(",", "")
    genai.configure(api_key=key_api)
else:
    print("None")

async def parser_offers_API(text: str) -> list:
    model = genai.GenerativeModel('models/gemini-3.5-flash')
    
    # A very simple prompt to exclude interpretation errors
    prompt = (
        "Jesteś precyzyjnym ekstraktorem ofert pracy. Twoim JEDYNYM zadaniem jest wyciągnięcie ofert z tekstu.\n"
        "Zasady:\n"
        "1. Zwróć wyłącznie poprawny format JSON (tablica obiektów).\n"
        "2. Jeśli w tekście nie ma ofert, zwróć dokładnie tylko: []\n"
        "3. ABSOLUTNIE NIE pisz żadnych wstępów, zakończeń, wyjaśnień ani znaków formatowania Markdown (takich jak ```json).\n"
        "4. Format wyjściowy:\n"
        "[{\"position\": \"nazwa\", \"company\": \"nazwa\", \"location\": \"miasto\", \"salary\": \"kwota\"}]\n\n"
        f"TEKST DO ANALIZY:\n{text}"
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
    
def clean_block(block: str) -> str:
    cleaned = []

    for line in block:
        l = line.lower()

        if l in ["!", "nowość!", "nowość", "hit!", "śpiesz się!"]:
            continue

        if "z " in l and "." in l:
            continue

        cleaned.append(line)

    return cleaned

skip = skip = [
    "logo", "więcej", "ciepłe", "najlepiej dopasowana", 
    "nowość", "hit", "śpiesz się",
    "krajowego rejestru", "krs", "nip", "regon", 
    "kapitału zakładowego", "wpłacony w całości", "ul. prosta", 
    "wyprzedź innych kandydatów", "Zobacz oferty, które mogły Ci umknąć", "bądź na bieżąco z nowymi ofertami pracy", 
    "zobacz wszystkie oferty pracy", 
    "zobacz wszystkie oferty", "zobacz więcej ofert", "zobacz więcej", "zobacz inne oferty", "zobacz inne", 
    "zobacz podobne oferty", "zobacz podobne", "sprawdź inne oferty", 
    "sprawdź inne", 
    "sprawdź podobne oferty", 
    "sprawdź podobne",
]

bad_titles = [
    "najlepiej dopasowana",
    "nowość",
    "hit",
]

async def process_pracuj_block(text: str, current_date: datetime, data: dict):
    # text is already plain text (we cleaned it in main)
    offers = await parser_offers_API(text)
    
    count = 0
    # Iterate once over each offer
    for offer in offers:
        is_valid = is_valid_offer(offer)
        is_job = looks_like_job(offer.get('position', ''))
        
        if is_valid and is_job:
            # Add the offer
            data.append({
                "date": current_date,
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


def looks_like_job(title: str) -> bool:
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
        'business', 
        'controlling', 
        'finanse', 
        'finance', 
        'planowania', 
        'planowanie', 
        'kontroler',
        'kontroler finansowy',
        'raportowanie',
        'raporty',
        'raportowania', 
        "archiwum", 
        "biurowy", 
        "fakturowania", 
        "spedytor", 
        "menedżer",  
        "logist", 
        "supply", 
        "analityk", "analyst", "specjalista", "specjalistka", "developer", "konsultant", 
        "księgowy", "staż", "młodszy", "data", "it", "danych", "business", "controlling", 
        "finanse", "finance", "planowania", "planowanie", "kontroler", "raportowanie", 
        "raporty", "raportowania", "biurowy", "fakturowania", "spedytor", "menedżer", 
        "logist", "supply", "koordynator", "asystent", "asystentka", "project manager", "financial", "junior"
    ]
    exclude = [
        "sp. z o.o", 
        "s.a.", 
        "sa ", 
        " sp. z", 
        "bank", 
        "polska"
    ]

    if any (k in title for k in keywords):
        if not any(e in title for e in exclude):
            return True
    return False

def is_job_trigger(line: str) -> dict:
    keywords = [
    "analityk", "analyst", "specjalista", "specjalistka", "developer", "engineer",
    "konsultant", "staż", "intern", "kontroler", "finansowy", "it", "data", "business"
    ]

    return any(k in line.lower() for k in keywords)

def known_companies(filename="known_companies.txt"):
    if not os.path.exists(filename):
        return []
    with open(filename, "r", encoding="utf-8") as f:
        # 
        return [line.strip().lower() for line in f if line.strip()]

# Load known companies
KNOWN_COMPANIES_LIST = known_companies()

def Knows_Companies(company):
    if not company:
        return False
        
    company = company.lower().strip()
    
    # Normalization for company names in search script
    clean_name = (
        company.replace(" sp. z o.o.", "")
        .replace(" sp. z o.o", "")
        .replace(".", "")
        .replace(",", "")
        .replace("sa ", "sa")
    )
    clean_name = re.sub(r'\s+', ' ', clean_name)
    clean_name = re.sub(r'\s*-\s*', ' ', clean_name)
    
    # Check company from file
    return any(kc in clean_name for kc in KNOWN_COMPANIES_LIST)


def is_valid_job(job: str) -> str:
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

if not mail_ids:
        print("No new job offers found.")
else:
        print(f"Found {len(mail_ids)} new emails.")

if os .path.exists(cache_file):
    with open(cache_file, "r") as f:
        processed_ids = set(line.strip() for line in f)
else:
    processed_ids = set()

# Main loop
async def main(mail, mail_ids, clean_jobs):
    # Load cache only once at startup
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            processed_ids.update(line.strip() for line in f)

    for i in mail_ids:
        mail_id_str = i.decode() if isinstance(i, bytes) else str(i)
        print(f"DEBUG: Checking mail ID: {mail_id_str}")
        # Skip if mail was already processed
        if mail_id_str in processed_ids:
            print(f"DEBUG: Mail {mail_id_str} is already processed. Skipping.")
            continue

        status, msg_data = mail.fetch(i, "(RFC822)")
        if status != 'OK': continue
        
        msg = email.message_from_bytes(msg_data[0][1])
        current_date = email.utils.parsedate_to_datetime(msg.get("Date")).strftime("%d.%m.%Y") if msg.get("Date") else "N/A"
        print(f"DEBUG: Attempting to fetch mail {mail_id_str}")
        html = get_html(msg)
        if not html: 
            print(f"DEBUG: Mail {mail_id_str} has no content (html is None). Skipping.")
            # Mark as processed even if empty to avoid re-checking
            with open(cache_file, "a") as f:
                f.write(mail_id_str + "\n")
            processed_ids.add(mail_id_str)
            continue

        text = BeautifulSoup(html, "html.parser").get_text("\n")
        print(f"DEBUG: Calling process_pracuj_block for mail ID: {mail_id_str}")
        # AI processes the mail
        await process_pracuj_block(text, current_date, clean_jobs)
        await asyncio.sleep(45)
        # Save offers
        for job in clean_jobs:
            print(f"Debug: Saving: {job.get('title')}")
            save_offers(
                title=job.get('title', 'N/A'),
                company=job.get('company', 'N/A'),
                location=job.get('location', 'N/A'),
                salary=job.get('salary', 'N/A'),
                date=job.get('date', 'N/A'),
                source='Pracuj.pl'
            )
        
        # Clear the list after saving to avoid duplicates for the next mail
        clean_jobs.clear()
        
        # SAVE ID TO CACHE after finishing the mail
        with open(cache_file, "a") as f:
            f.write(mail_id_str + "\n")
        processed_ids.add(mail_id_str)

        print(f"Processed mail: {mail_id_str}, wait 25 seconds...")
        await asyncio.sleep(25)


def save_offers(title: str, company: str, location: str, salary: str , date: str, source: str, db_name = 'new_offers.db'):
    conn = sqlite3.connect(db_name)
    cursor =conn.cursor()
    cursor.execute('''
            INSERT INTO Offers (title, company, location, salary, date, source)
                   VALUES (?, ?, ?, ?, ?, ?)
        ''', (title, company, location, salary, date, source))

    conn.commit()
    conn.close()

# Entry point: Initialize the asyncio event loop and execute the main processing function
if __name__ == "__main__":
    clean_jobs = []
    asyncio.run(main(mail, mail_ids, clean_jobs))
  
print("\nFinished!")
print("MAILS processed:", len(mail_ids))
print("TOTAL JOBS found:", len(clean_jobs))