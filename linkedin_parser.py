# Library

import imaplib
from bs4 import BeautifulSoup
from email import message_from_bytes
import email 
import pandas as pd
import os
from dotenv import load_dotenv
import re
import email.utils


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
status, messages = mail.search(None, "ALL")
mail_ids = messages[0].split()

print("Number of mails:", len(mail_ids))

# Create empty list to store data

data = []

def get_html(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                return part.get_payload(decode=True).decode(errors="ignore")
    else:
        if msg.get_content_type() == "text/html":
            return msg.get_payload(decode=True).decode(errors="ignore")
    return None

def clean_text(block):
    cleaned= []

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

def looks_like_job_offer(title):
    title = title.lower()

    words = [
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
        "manager", 
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

    if any (w in title for w in words):
        if not any (e in title for e in exclude):
                return True
    return False

def job_trigger (line):
    words = [
    "analityk",
    "analyst",
    "specjalista",
    "specjalistka",
    "developer",
    "engineer",
    "konsultant",
    "staż",
    "intern",
    "kontroler",
    "finansowy",
    "it",
    "data",
    "business"
    ]
    return any(k in line.lower() for k in words)

def Companies(company):
    known_companies = [
        "recruitment",
        "allegro",
        "ing",
        "pkobp",
        "mbank",
        "orange",
        "play",
        "deloitte",
        "ey",
        "pwc",
        "qiagen wrocław",
        "capgemini",
        "ppg",
        "euvic it",
        "wrocławski park technologiczny",
        "kaufland",
        "adsystem",
        "ppg global business services", 
        "wyższa szkoła kształcenia zawodowego", 
        "kpmg", 
        "aurora logistics spółka z ograniczoną odpowiedzialnością", 
        "qiagen",
        "ey (dawniej ernst & young)", 
        "upvanta spółka z ograniczoną odpowiedzialnością"
    ]

    company = company.lower().strip()

    company = (
        company.replace(" sp. z o.o.", "")
        .replace(" sp. z o.o", "")
        .replace(".", "")
        .replace(",", "")
        .replace("sa ", "sa")
    )

    company = re.sub(r'\s+', ' ', company)
    company = re.sub(r'\s*-\s*', ' ', company)

    return any( k_c in company for k_c in known_companies)


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

clean_jobs = []
status, response = mail.search(None, 'ALL')
mail_ids = response[0].split()

if not mail_ids:
        print("Brak nowych ofert w mailu.")
else:
        print(f"Znaleziono {len(mail_ids)} nowych maili.")

# Main processing loop
for i in mail_ids:
    print("Przetwarzam mail: ", i)
    status, msg_data = mail.fetch(i, "(RFC822)")
    raw_email = msg_data[0][1]
    msg = email.message_from_bytes(raw_email)
    # Take date from email header and convert it to datetime object, then format it as "dd.mm.yyyy"
    date_str = msg.get("Date")
    if date_str:
        parsed_date = email.utils.parsedate_to_datetime(date_str)
        current_date = parsed_date.strftime("%d.%m.%Y")
   
    print(f"Data maila: {current_date}")

    html = get_html(msg)
    if not html:
        continue

    text = BeautifulSoup(html, "html.parser").get_text("\n")
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    current_job = None


    for line in lines:
        line = line.strip()
        if not line:
            continue

        l = line.lower()
        if any(s in l for s in skip):
            continue

        if "nowe oferty" in l or "właścicielem marki" in l:
            continue
        
    

        # If the line looks like a job title, we start a new job entry
        if looks_like_job_offer(line):
            if current_job and current_job["title"]:
                clean_jobs.append(current_job)

            current_job = {
                "title": line,
                "company": None,
                "location": None,
                "salary": None,
                "date": current_date
            }
            continue

        if not current_job:
            continue

        # Filling in data for the currently found job
        if "zł" in l or "mies. " in l:
            current_job["salary"] = line
            continue
        found_city = None
        for city in ["Wrocław", "Warszawa", "Kraków", "Pietrzykowice", "Wróblowice", "Kobierzyce", "Łódź", "Poznań", "Gdańsk", "Jelcz-Laskowice", "Oleśnica", "Magnice",
                     "Krzyżanowice", "Trzebnica", "Oława", "Szczecin", "Bielany Wrocławskie", "Święte", "Długołęka", "Siechnice", "Opole", "Katowice", "Gliwice", "Rzeszów", "Brzeg Dolny"]:
            if city in line:
                found_city = city
                break
        
        if found_city:
            if any(corp in l for corp in ["sp. z o.o", " s.a", "sa ", "hays", "recruitment"]):
                    parts = line.split(found_city)
                    current_job["company"] = parts[0].strip(", ").strip()
                    current_job["location"] = found_city + parts[1]
            else:
                    current_job["location"]= line
            continue
        
        if current_job and current_job["company"] is None:
            is_probably_company = any(e in l for e in ["s.a.", "sa.", "S.A.", "SA", "s a", "s-a", "sp. z o.o.", "sp z o.o", "sp z oo", "sp zoo", "sp. z oo", "sp z o. o.", 
                                    "sp. z o. o", "sp. zoo", "sp zoo.", "spółka z o.o.", "spolka z o.o.", "sp. z o o", "bank", "Bank", "BANK", "bank.", "spółka akcyjna", "spółka z ograniczoną odpowiedzialnością"])
            is_definitely_company = is_probably_company or Companies(line)
            if is_definitely_company:
                current_job["company"] = line
            elif not found_city and "zł" not in l:
                if len(current_job["title"]) < 20:
                    current_job["title"] += " " + line
                else:
                    current_job["company"] = line
            else:
                pass

    # Add the last job offer from the current email (if it existed)
    if current_job:
        clean_jobs.append(current_job)
  


clean_jobs_filtered = []

for job in clean_jobs:
    if is_valid_job(job):
        clean_jobs_filtered.append(job)

# Add new jobs offerts to excel file
new_df = pd.DataFrame(clean_jobs_filtered)

path = "new_offerts.xlsx"

sheet_name = "LinkeIn"

if not new_df.empty:
    # Date as string to avoid any weird issues with Excel and sorting
    new_df['date'] = new_df['date'].astype(str)
    
if os.path.exists(path):
        try:
            old_df = pd.read_excel(path, sheet_name=sheet_name)
            old_df['date'] = old_df['date'].astype(str)
        except ValueError:
            df_final = new_df
        else:
            df_final = new_df
  

print("\nZakończono pomyślnie!")
print("MAILS processed:", len(mail_ids))
print("TOTAL JOBS found:", len(clean_jobs))
print("FILTERED JOBS:", len(clean_jobs_filtered))