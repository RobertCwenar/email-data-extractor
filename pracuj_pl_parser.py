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

# load data

Cache_file = "processed_mails.txt"
jobs = []

status, response = mail.search(None, 'ALL')
mail_ids = response[0].split()

clean_jobs= []
def get_html(msg):
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

def is_valid_offer(offer):
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

async def parser_offers_API(text):
    model = genai.GenerativeModel('models/gemini-3.5-flash')
    
    # A very simple prompt to exclude interpretation errors
    prompt = (
         "Jesteś ekstraktorem ofert pracy. Z poniższego tekstu wyciągnij wszystkie oferty.\n"
            "Zwróć wynik TYLKO jako czystą tablicę JSON: "
            "[{\"position\": \"nazwa stanowiska\", \"company\": \"nazwa firmy\", \"location\": \"miasto\", \"salary\": \"kwota wynagrodzenia jeżeli nie ma to nie wpisuj niczego'\"}]\n\n"
            "Jeśli nie ma żadnej oferty, zwróć: []\n"
            "Nie dodawaj żadnych wyjaśnień, wstępów, ani znaków Markdown typu ```json.\n"
            f"TEKST MAIL:\n{text}"
        )
    
    try:
        response = await model.generate_content_async(prompt)
        
        raw_output = response.text
        print(f"DEBUG: Raw AI response: {raw_output[:500]}") 
        
        # Próba parsowania
        clean_json = raw_output.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
        
    except Exception as e:
        print(f"Parser Error: {e}")
        return []
    
def clean_block(block):
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

async def process_pracuj_block(text, current_date, data):
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
bad_titles = ["Zobacz oferty", 
              "absolwentów uczelni",
                "absolwent uczelni",
                "aktywnie rekrutuje",
                "zobacz oferty",
                "zobacz więcej",
                "zobacz wszystkie"]

skip = ["zobacz oferty",
        "absolwentów uczelni",
        "absolwent uczelni",
        "aktywnie rekrutuje",
        "zobacz więcej",
        "zobacz wszystkie",
        "właścicielem marki"]


def looks_like_job(title):
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
        "supply"
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

def is_job_trigger(line):
    keywords = [
    "analityk", "analyst", "specjalista", "specjalistka", "developer", "engineer",
    "konsultant", "staż", "intern", "kontroler", "finansowy", "it", "data", "business"
    ]

    return any(k in line.lower() for k in keywords)

def known_companies(filename="known_companies.txt"):
    if not os.path.exists(filename):
        return []
    with open(filename, "r", encoding="utf-8") as f:
        # Wczytujemy linie, czyścimy z białych znaków i zamieniamy na małe litery
        return [line.strip().lower() for line in f if line.strip()]

# Wczytujemy firmy raz na początku
KNOWN_COMPANIES_LIST = known_companies()

def Knows_Companies(company):
    if not company:
        return False
        
    company = company.lower().strip()
    
    # 
    clean_name = (
        company.replace(" sp. z o.o.", "")
        .replace(" sp. z o.o", "")
        .replace(".", "")
        .replace(",", "")
        .replace("sa ", "sa")
    )
    clean_name = re.sub(r'\s+', ' ', clean_name)
    clean_name = re.sub(r'\s*-\s*', ' ', clean_name)
    
    # Sprawdzamy czy któraś firma z pliku jest w nazwie
    return any(kc in clean_name for kc in KNOWN_COMPANIES_LIST)


def is_valid_job(job):
    title = job["title"].lower()

    if any(b in title for b in bad_titles):
        return False

    # It should be like a job title, not just a single word
    if len(title.split()) < 2:
        return False

    # company not offering jobs
    if "sp. z o.o" in title.lower():
        return False

    return True

if not mail_ids:
        print("No new job offers found.")
else:
        print(f"Found {len(mail_ids)} new emails.")

if os .path.exists(Cache_file):
    with open(Cache_file, "r") as f:
        processed_ids = set(line.strip() for line in f)
else:
    processed_ids = set()

# Main loop
async def main(mail, mail_ids, clean_jobs):
    if os.path.exists(Cache_file):
        with open(Cache_file, "r") as f:
            processed_ids.update(line.strip() for line in f)

    for i in mail_ids:
        mail_id_str = i.decode() if isinstance(i, bytes) else str(i)
        if mail_id_str in processed_ids:
            continue

        status, msg_data = mail.fetch(i, "(RFC822)")
        if status != 'OK': continue
        
        msg = email.message_from_bytes(msg_data[0][1])
        current_date = email.utils.parsedate_to_datetime(msg.get("Date")).strftime("%d.%m.%Y") if msg.get("Date") else "N/A"
        
        html = get_html(msg)
        if not html: continue

        text = BeautifulSoup(html, "html.parser").get_text("\n")
        
        await process_pracuj_block(text, current_date, clean_jobs)

    for job in clean_jobs:
        print(f"Debug: Test save offers: {job.get('title')}")
        save_offers(
                title=job.get('title', 'N/A'),
                company=job.get('company', 'N/A'),
                location=job.get('location', 'N/A'),
                salary=job.get('salary', 'N/A'),
                date=job.get('date', 'N/A'),
                source='pracuj.pl'
        )
    
    clean_jobs.clear()
    print(f"Processed mail: {mail_id_str}, wait 25 seconds...")
    
    with open(Cache_file, "a") as f:
        f.write(mail_id_str + "\n")
    await asyncio.sleep(25)
    processed_ids.add(mail_id_str)

# Create new dataframe with new offers
def init_db():
    conn = sqlite3.connect('new_offers.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Offers(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            company TEXT,
            location TEXT,
            salary TEXT,
            date TEXT,
            source TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_offers(title, company, location, salary, date, source):
    conn = sqlite3.connect('new_offers.db')
    cursor =conn.cursor()
    cursor.execute('''
            INSERT INTO Offers (title, company, location, salary, date, source)
                   VALUES (?, ?, ?, ?, ?, ?)
        ''', (title, company, location, salary, date, source))

    conn.commit()
    conn.close()

# Entry point: Initialize the asyncio event loop and execute the main processing function
if __name__ == "__main__":
    init_db()
    clean_jobs = []
    asyncio.run(main(mail, mail_ids, clean_jobs))
  
print("\nFinished!")
print("MAILS processed:", len(mail_ids))
print("TOTAL JOBS found:", len(clean_jobs))