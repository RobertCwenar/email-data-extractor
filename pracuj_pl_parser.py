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
from google import genai
from google.genai import types
import json
import time

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
    client = genai.Client(api_key=key_api)
else:
    print("None")

async def parser_offers_API(text, retries=3):
    for attempt in range(retries):    
        # Very simple prompt to extract json
        models=["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-2.5-flash"]
        
        model_name = models[attempt] if attempt < len (models) else models[-1]
        prompt = (
            "Jesteś ekstraktorem ofert pracy. Z poniższego tekstu wyciągnij wszystkie oferty.\n"
            "Zwróć wynik TYLKO jako czystą tablicę JSON: "
            "[{\"position\": \"nazwa stanowiska\", \"company\": \"nazwa firmy\", \"location\": \"miasto\", \"salary\": \"kwota wynagrodzenia jeżeli nie ma to nie wpisuj niczego'\"}]\n\n"
            "Jeśli nie ma żadnej oferty, zwróć: []\n"
            "Nie dodawaj żadnych wyjaśnień, wstępów, ani znaków Markdown typu ```json.\n"
            f"TEKST MAIL:\n{text}"
        )
    
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                )
            )
            raw_output=response.text
            print(f"DEBUG: Answer AI: {raw_output[:500]}") 
            clean_json = raw_output.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json)
            
        except Exception as e:
            if "503" in str(e):
                print(f"PARSER ERROR: {e}")
                time.sleep(3)
            else:
                print(f"Error: {e}")
                break
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
    
    print(f" [SUKCES] Wyciągnięto {count} poprawnych ofert.")
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
        "SPOLKA Z OGRANICZONA ODPOWIEDZIALNOSCIA"
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
    
    # Używamy pre-procesingu jak w Twoim kodzie
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
        
        # Procesowanie (używamy tej samej struktury co w Twoim przykładzie)
        await process_pracuj_block(text, current_date, clean_jobs)
        
        print(f"Przetworzono mail: {mail_id_str}, czekam 15 sekund...")
        await asyncio.sleep(25)

        with open(Cache_file, "a") as f:
            f.write(mail_id_str + "\n")
        processed_ids.add(mail_id_str)

for job in clean_jobs:
    if is_valid_job(job):
        clean_jobs.append(job)

# Entry point: Initialize the asyncio event loop and execute the main processing function
if __name__ == "__main__":
    clean_jobs = []
    asyncio.run(main(mail, mail_ids, clean_jobs))
    clean_jobs_filtered = [job for job in clean_jobs if is_valid_job(job)]
    
# Create new dataframe with new offers
new_df = pd.DataFrame(clean_jobs_filtered)

path = "new_offers.xlsx"
sheet_name = "Pracuj.pl"

jobs_saved = 0

if not new_df.empty:
    # Date as string to avoid any weird issues with Excel and sorting
    new_df['date'] = new_df['date'].astype(str)
    
    if os.path.exists(path):
        try:
            with pd.ExcelWriter(path, mode='a', engine='openpyxl', if_sheet_exists='replace') as writer:
                try:
                    old_df = pd.read_excel(path, sheet_name=sheet_name)
                    old_df['date'] = old_df['date'].astype(str)
                    
                    df_final = pd.concat([old_df, new_df], ignore_index=True)
                except ValueError:
                    
                    df_final = new_df
                jobs_added = len(new_df)
                
                df_final['temp_date'] = pd.to_datetime(df_final['date'], format='%d.%m.%Y', errors='coerce')
                df_final = df_final.sort_values(by='temp_date', ascending=False).drop(columns=['temp_date'])
         
                df_final.to_excel(writer, sheet_name=sheet_name, index=False)
                print(f"Merged new job offers with existing data in sheet: {sheet_name}")
                
        except Exception as e:
            print("Error occurred while processing Excel file:", e)
    else:
        df_final = new_df.copy()
  
        df_final['temp_date'] = pd.to_datetime(df_final['date'], format='%d.%m.%Y', errors='coerce')
        df_final = df_final.sort_values(by='temp_date', ascending=False).drop(columns=['temp_date'])
        
        df_final.to_excel(path, sheet_name=sheet_name, index=False)
        jobs_added = len(df_final)
        print(f"Created new Excel file with sheet: {sheet_name}")
else:
    print("Empty list of new job offers.")

print(f"\nSaved! New unique jobs added to {sheet_name}: {jobs_added}")
print("\nFinished!")
print("MAILS processed:", len(mail_ids))
print("TOTAL JOBS found:", len(clean_jobs))
print("FILTERED JOBS:", len(clean_jobs_filtered))