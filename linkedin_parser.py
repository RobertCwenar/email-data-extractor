# Library

import imaplib
from bs4 import BeautifulSoup
from email import message_from_bytes
import pandas as pd
import os
from dotenv import load_dotenv
import re
import email.utils
from openpyxl import load_workbook

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

def process_linkedin_block(block, current_date):
    full_text = " ".join([line.strip() for line in block.split("\n") if line.strip()])

    split_pattern = r'(\d+\s+absolwentów\s+uczelni|\d+\s+absolwent\s+uczelni|Aktywnie\s+rekrutuje)'
    pieces = re.split(split_pattern, full_text)

    current_offer = ""

    for piece in pieces:
        piece = piece.strip()
        if not piece:
            continue

        # Check if the piece matches the split pattern, which indicates the end of a job offer block
        if re.match(split_pattern, piece):
            if "·" in current_offer:
                parts = current_offer.split("·")
                location = parts[-1].strip() if len(parts) > 1 else ""
                pos_and_company = parts[0].strip()
                # Clean up the position and company string
                pos_and_company = pos_and_company.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
                pos_and_company = re.sub(r'[\u200b\u200c\u200d\u2060\ufeff\xa0\u034f]+', ' ', pos_and_company)
                pos_and_company = re.sub(r'\s*Lokalizacja:\s*[^A-Z]*', ' ', pos_and_company).strip()
                
                pos_and_company = re.sub(r'\s*Najlepsze oferty pracy dla Ciebie\s*', ' ', pos_and_company).strip()
                pos_and_company = re.sub(r'\s*Aplikuj\s+', ' ', pos_and_company, flags=re.IGNORECASE).strip()
                pos_and_company = re.sub(r'([a-z])([A-Z])', r'\1 \2', pos_and_company)
                pos_and_company = re.sub(r'\s+', ' ', pos_and_company).strip()

                pos_lower = pos_and_company.lower()

                keywords = ["młodszy",
                            "młodsza",
                            "junior",
                            "intern",
                            "stażysta",
                            "analityk",
                            "analityczka",
                            "analyst",
                            "data",
                            "specjalista",
                            "specjalistka",
                            "developer",
                            "engineer"]
                
 
                first_match_idx = -1
                for kw in keywords:
                    idx = pos_lower.find(kw)
                    if idx != -1:
                        if first_match_idx == -1 or idx < first_match_idx:
                            first_match_idx = idx

                if first_match_idx != -1:
                    pos_and_company = pos_and_company[first_match_idx:].strip()

                # Extract title and company from the position and company string
                if any(s in pos_and_company.lower() for s in skip):
                    current_offer = ""
                    continue 
                title = pos_and_company
                company = "None"
                found_companies = False

                known_companies = [
                    "Santander Consumer Bank", "NG Engineering Group", "NG Engineering", "KPMG", "Deloitte", "EY Polska", "EY", "PwC Polska", "PwC",
                    "Poczta Polska", "Alior Leasing", "Erste Bank Polska", "Erste Bank", "Elenger", "In Post", "In Post", "Inpost", "LPP", "Grupa LPP", "Grupa Żywiec", "Żywiec Group", "Żywiec",
                    "SGS GBS Europe", "TIAS Accounting and Legal", "Wrocławski Park Technologiczny", "Polkomtel", "Polkomtel Sp. z o.o.", "Polkomtel S.A.", "Polkomtel Group", "Polkomtel IT", "Polkomtel Sp. z o.o.", "Polkomtel S.A.", "Polkomtel Group", "Polkomtel IT",
                    "Wyższa Szkoła Kształcenia Zawodowego", "Olympus Corporation", "Olympus Polska", "Olympus", "Grupa Żywiec", "Żywiec Group", "Żywiec", "ZF Group", "ZF", "Grupa Żywiec", "Żywiec Group", "Żywiec", "Grupa Żywiec", "Żywiec Group", "Żywiec", "Hineken"
                ]

                found_companies = False
                for kc in known_companies:
                    if kc.lower() in pos_and_company.lower():
                        start_idx = pos_and_company.lower().find(kc.lower())
                        title = pos_and_company[:start_idx].strip()
                        company = kc
                        found_companies = True
                        break
                
                if not found_companies:
                    legal_match = re.search(r'\b([^,.]+?)\s*(?:Sp\s*z\s*o\s*\.\s*o\s*|S\s*\.?\s*A\s*\.?|Group|Group\s+IT)\b', pos_and_company, flags=re.IGNORECASE)
                    if legal_match:
                        full_company_match = legal_match.group(0)
                        start_idx = pos_and_company.find(full_company_match)
                        if start_idx != -1:
                            title = pos_and_company[:start_idx].strip()
                        company = full_company_match
                        found_companies = True

                if not found_companies and " " in pos_and_company:
                    title = pos_and_company.rsplit(" ", 1)[0].strip()
                    company = pos_and_company.rsplit(" ", 1)[1].strip()

                data.append({
                    "date": current_date,
                    "title": title,
                    "company": company,
                    "location": location,
                    "salary": None,
                })
                    
            current_offer = ""
            
        else:
            current_offer = piece

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
    ]

    if any (w in title for w in words):
        if not any (e in title for e in exclude):
                return True
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

# Main processing loop

for i in mail_ids:
    mail_id_str = i.decode() if isinstance(i, bytes) else str(i)

    if mail_id_str in processed_mail_ids:
        continue
    print(f"Processing mail ID: {mail_id_str}")
    status, msg_data = mail.fetch(i, "(RFC822)")
    if status == 'OK' and msg_data and isinstance(msg_data[0], tuple) and len(msg_data[0]) > 1:
        raw_email = msg_data[0][1]
        if not isinstance(raw_email, bytes):
            print(f"Cannot process mail {mail_id_str}: not bytes.")
            continue
        msg = email.message_from_bytes(raw_email)

    current_date = "None date"
    date_str = msg.get("Date")
    if date_str:
        try:
            parsed_date = email.utils.parsedate_to_datetime(date_str)
            current_date = parsed_date.strftime("%d.%m.%Y")
        except Exception as e:
            print(f"Error parsing date for mail {mail_id_str}: {e}")
            current_date = date_str

    print(f"Mail date: {current_date}")



    html = get_html(msg)
    if not html:
        continue

    text = BeautifulSoup(html, "html.parser").get_text(separator="\n")

    process_linkedin_block(text, current_date)
    with open(Cache_file_path, "a") as f:
        f.write(mail_id_str + "\n")
        processed_mail_ids.add(mail_id_str)

# Add new jobs offers to excel file

file_path = "new_offers.xlsx"
sheet_name = "LinkedIn"

new_df = pd.DataFrame(data)

if not new_df.empty:
    # Convert date to string
    new_df['date'] = new_df['date'].astype(str)
    
    # If file exists, try to merge it
    if os.path.exists(file_path):
        try:
            # Use ExcelWriter to avoid erasing other sheets in the file
            with pd.ExcelWriter(file_path, mode='a', engine='openpyxl', if_sheet_exists='replace') as writer:
                try:
                    old_df = pd.read_excel(file_path, sheet_name=sheet_name)
                    old_df['date'] = old_df['date'].astype(str)
                    df_final = pd.concat([old_df, new_df], ignore_index=True)
                except ValueError:    
                    # Sheet didn't exist inside the file, so final data is just the new data
                    df_final = new_df
                
                # Save the merged data back to the sheet
                df_final.to_excel(writer, sheet_name=sheet_name, index=False)
                print("Merged new job offers with existing data.")
        except Exception as e:
            print("Error occurred while processing Excel file:", e)
    else:
        # 3. If file doesn't exist at all, create it fresh
        new_df.to_excel(file_path, sheet_name=sheet_name, index=False)
        print("Created new Excel file and saved jobs.")
        
else:
    print("No new job offers found in the emails.")

print("\nFinished!")
print("MAILS processed:", len(mail_ids))
print("TOTAL JOBS found:", len(data))