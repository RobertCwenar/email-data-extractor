# Library
import asyncio
import imaplib
import json
from bs4 import BeautifulSoup
from email import message_from_bytes
import pandas as pd
import os
from dotenv import load_dotenv
import re
import email.utils
from openpyxl import load_workbook
import google.generativeai as genai
import time

#Load environment variables from .env file
load_dotenv()

#Login to wp.pl
mail = imaplib.IMAP4_SSL("imap.wp.pl", 993)
login_email = os.getenv("EMAIL").strip().replace(",", "")
my_password = os.getenv("PASSWORD").strip().replace(",", "")
print("Logging in: ", bool (login_email))
print("Password loaded:", bool(my_password))

mail.login(login_email, my_password)
mail.select("Link") # Change to the desired mailbox (e.g., "inbox")!!!!
status, messages = mail.search(None, "UNSEEN")
mail_ids = messages[0].split()

print("Number of mails:", len(mail_ids))

# Create empty list to store data
Cache_file_path = "processed_linkedin_mails.txt"
processed_mail_ids = set()
data = [] 

def get_html(msg): 
    if msg.is_multipart():
        for part in msg.walk():
            # Looking for a part of email with html
            if part.get_content_type() == "text/html":
                charset = part.get_content_charset() or 'utf-8'
                return part.get_payload(decode=True).decode(charset, errors='ignore')
    elif msg.get_content_type() == "text/html":
        charset = msg.get_content_charset() or 'utf-8'
        return msg.get_payload(decode=True).decode(charset, errors='ignore')
    return ""

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

# Load API
api_key = os.getenv("KEY_API")
if api_key:
    key_api= api_key.strip().replace(",", "")
    genai.configure(api_key=key_api)
else:
    print("None")

async def parse_all_offers_from_mail(text):
    model = genai.GenerativeModel('models/gemini-3.5-flash')
    
    prompt = (
    "Jesteś precyzyjnym systemem ekstrakcji danych. Przeanalizuj poniższy tekst i wyciągnij WSZYSTKIE oferty pracy.\n"
        "Zwróć wynik jako czysty JSON w formacie listy obiektów: [{'position': '...', 'company': '...', 'location': '...'}, ...].\n"
        "Jeśli w tekście jest 12 ofert, lista musi mieć 12 elementów. NIE dodawaj żadnego tekstu przed ani po JSON-ie.\n"
        f"TEKST DO ANALIZY:\n{text}"
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

async def process_linkedin_block(text, current_date, data):
    # text is already plain text (we cleaned it in main)
    offers = await parse_all_offers_from_mail(text)
    
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
                "location": offer.get('location', 'N/A')
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

# Define functions to analyze job offers and companies
def looks_like_job(title):
    clean_title = title.lower()

    junk_phrases = [
        "aktywnie rekrutuje", "bądź pierwszym", "spośród", "kandydatów", 
        "1 kontakt", "absolwentów uczelni", "absolwent uczelni", "zobacz oferty"
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

Cache_file_path = "processed_linkedin_mails.txt"
if os.path.exists(Cache_file_path):
    with open(Cache_file_path, "r") as f:
        processed_mail_ids = set(line.strip() for line in f)
else:
    processed_mail_ids = set()

# Main Loop
async def main(mail, mail_ids):
    if os.path.exists(Cache_file_path):
        with open(Cache_file_path, "r") as f:
            processed_mail_ids.update(line.strip() for line in f)

    for i in mail_ids:
        mail_id_str = i.decode() if isinstance(i, bytes) else str(i)
        if mail_id_str in processed_mail_ids:
            continue

        status, msg_data = mail.fetch(i, "(RFC822)")
        if status != 'OK': continue
        
        msg = email.message_from_bytes(msg_data[0][1])
        current_date = email.utils.parsedate_to_datetime(msg.get("Date")).strftime("%d.%m.%Y") if msg.get("Date") else "N/A"
        
        html = get_html(msg)
        if not html: continue

        soup = BeautifulSoup(html, "html.parser")
        text_block = soup.get_text(separator=" ", strip=True)[:2000]
        
        if len(text_block) > 50:
            await process_linkedin_block(text_block, current_date, data)
            print("Czekam 15 sekund")
            await asyncio.sleep(15)

            with open(Cache_file_path, "a") as f:
                f.write(mail_id_str + "\n")
            processed_mail_ids.add(mail_id_str)

# Entry point: Initialize the asyncio event loop and execute the main processing function
if __name__ == "__main__":
    asyncio.run(main(mail, mail_ids))

# Add new jobs offers to excel file

file_path = "new_offers.xlsx"
sheet_name = "LinkedIn"

def append_to_excel(data, file_path="new_offers.xlsx"):
    if not data: return
    df = pd.DataFrame(data)
    
    if not os.path.exists(file_path):
        df.to_excel(file_path, index=False, sheet_name="LinkedIn")
    else:
        with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
            try:
                # Wczytaj by znaleźć ostatni wiersz
                old_df = pd.read_excel(file_path, sheet_name="LinkedIn")
                start_row = len(old_df) + 1
                df.to_excel(writer, index=False, header=False, startrow=start_row, sheet_name="LinkedIn")
            except Exception:
                df.to_excel(writer, index=False, sheet_name="LinkedIn")
    
    
    print(f"Zapisano {len(data)} ofert do pliku {file_path}.")
print("\nFinished!")
print("MAILS processed:", len(mail_ids))
print("TOTAL JOBS found:", len(data))

if data:
    append_to_excel(data, file_path="new_offers.xlsx")
else:
    print("Brak danych do zapisania w Excelu.")